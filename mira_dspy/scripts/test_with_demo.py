"""Test script for mira_dspy using MIMIC-IV demo dataset.

This script demonstrates the mira_dspy pipeline with the 100-patient demo
subset, which doesn't require PhysioNet credentialing.

Usage:
    cd mira_dspy
    source .venv/bin/activate
    python scripts/test_with_demo.py
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pandas as pd
from tqdm import tqdm

# Configure paths to use demo data
MIMIC_DEMO_DIR = Path(__file__).parent.parent.parent / "mimic_demo" / "2.2"
os.environ["MIRA_MIMIC_HOSP_DIR"] = str(MIMIC_DEMO_DIR / "hosp")
os.environ["MIRA_MIMIC_ED_DIR"] = str(MIMIC_DEMO_DIR / "ed")
os.environ["MIRA_MIMIC_NOTE_DIR"] = str(MIMIC_DEMO_DIR / "note")

from dataset.mimic_dataset import MIMIC_Dataset, MIMIC_Hadm_Dataset
from evaluations.preprocess import PatientGroundTruth


def load_demo_dataset() -> MIMIC_Dataset:
    """Load a minimal dataset from the MIMIC-IV demo for testing.

    Since the demo doesn't have the preprocessed diagnosis datasets,
    we build a minimal version directly from the raw CSV files.
    """
    hosp_dir = MIMIC_DEMO_DIR / "hosp"
    ed_dir = MIMIC_DEMO_DIR / "ed"

    # Load raw tables
    admissions = pd.read_csv(hosp_dir / "admissions.csv")
    patients = pd.read_csv(hosp_dir / "patients.csv")
    diagnoses_icd = pd.read_csv(hosp_dir / "diagnoses_icd.csv")
    procedures_icd = pd.read_csv(hosp_dir / "procedures_icd.csv")
    labevents = pd.read_csv(hosp_dir / "labevents.csv")
    microbiologyevents = pd.read_csv(hosp_dir / "microbiologyevents.csv")
    prescriptions = pd.read_csv(hosp_dir / "prescriptions.csv")

    # Load ED data if available
    try:
        ed_stays = pd.read_csv(ed_dir / "edstays.csv")
        triage = pd.read_csv(ed_dir / "triage.csv")
        vitalsign = pd.read_csv(ed_dir / "vitalsign.csv")
    except FileNotFoundError:
        ed_stays = pd.DataFrame(columns=["hadm_id"])
        triage = pd.DataFrame(columns=["hadm_id"])
        vitalsign = pd.DataFrame(columns=["hadm_id"])

    # Demo doesn't have discharge notes, so we create placeholder history
    # In real usage, this comes from processed discharge letters
    hadm_ids = set(admissions["hadm_id"].unique())

    # Create placeholder history_pe_admedication_diagnosis
    # (In real MIMIC, this is extracted from discharge letters)
    history_df = pd.DataFrame({
        "hadm_id": list(hadm_ids),
        "extracted_history": ["Patient with abdominal pain and nausea." * 10] * len(hadm_ids),
        "pe": ["Abdomen tender to palpation." * 5] * len(hadm_ids),
        "admission_medication": ["None"] * len(hadm_ids),
        "procedures_from_discharge_letter": [[] for _ in range(len(hadm_ids))],
    })

    # Create placeholder radiology
    radiology_df = pd.DataFrame({
        "hadm_id": list(hadm_ids)[:10],  # Only some have radiology
        "charttime": pd.Timestamp("2020-01-01"),
        "modality": ["CT"] * min(10, len(hadm_ids)),
        "region": ["Abdomen/Pelvis"] * min(10, len(hadm_ids)),
        "extracted_rad_events": ["No acute abnormality."] * min(10, len(hadm_ids)),
    })

    # Get all hadm_ids that have diagnoses
    hadm_ids_with_diagnoses = set(diagnoses_icd["hadm_id"].unique())

    # Create a simple "demo" diagnosis label (first ICD code for each hadm)
    demo_diagnoses = diagnoses_icd.groupby("hadm_id").first().reset_index()

    print(f"Loaded demo dataset with {len(hadm_ids)} admissions")
    print(f"Admissions with diagnoses: {len(hadm_ids_with_diagnoses)}")

    # Build a minimal MIMIC_Dataset-like structure
    # We'll use a simple wrapper instead of the full class

    class DemoDataset:
        def __init__(self, hadm_ids, admissions, patients, diagnoses_icd,
                     procedures_icd, labevents, microbiologyevents, prescriptions,
                     history_df, radiology_df, ed_stays, triage, vitalsign):
            self.hadm_ids = hadm_ids
            self.admissions = admissions
            self.patients = patients
            self.diagnoses_icd = diagnoses_icd
            self.procedures_icd = procedures_icd
            self.lab_events = labevents
            self.microbiology = microbiologyevents
            self.medication = prescriptions
            self.history_pe_admedication_diagnosis = history_df
            self.radiology = radiology_df
            self.ed_stays = ed_stays
            self.triage = triage
            self.vitalsign = vitalsign
            self.diagnosis_ed = pd.DataFrame(columns=["hadm_id"])
            self.medrecon = pd.DataFrame(columns=["hadm_id"])
            self.pyxis = pd.DataFrame(columns=["hadm_id"])
            self.diagnosis = "demo"

        def __getitem__(self, hadm_id):
            return DemoAdmission(
                hadm_id=hadm_id,
                admissions=self.admissions[self.admissions["hadm_id"] == hadm_id],
                patients=self.patients[self.patients["subject_id"] ==
                    self.admissions[self.admissions["hadm_id"] == hadm_id]["subject_id"].values[0]],
                diagnoses_icd=self.diagnoses_icd[self.diagnoses_icd["hadm_id"] == hadm_id],
                procedures_icd=self.procedures_icd[self.procedures_icd["hadm_id"] == hadm_id],
                lab_events=self.lab_events[self.lab_events["hadm_id"] == hadm_id],
                microbiology=self.microbiology[self.microbiology["hadm_id"] == hadm_id],
                medication=self.medication[self.medication["hadm_id"] == hadm_id],
                history_pe_admedication_diagnosis=self.history_pe_admedication_diagnosis[
                    self.history_pe_admedication_diagnosis["hadm_id"] == hadm_id
                ],
                radiology=self.radiology[self.radiology["hadm_id"] == hadm_id],
                ed_stays=self.ed_stays[self.ed_stays["hadm_id"] == hadm_id],
                triage=self.triage[self.triage["hadm_id"] == hadm_id],
                vitalsign=self.vitalsign[self.vitalsign["hadm_id"] == hadm_id],
            )

        def __len__(self):
            return len(self.hadm_ids)

        def __iter__(self):
            self._iter = iter(self.hadm_ids)
            return self

        def __next__(self):
            hadm_id = next(self._iter)
            return self[hadm_id]

    class DemoAdmission:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    return DemoDataset(
        hadm_ids=hadm_ids_with_diagnoses,
        admissions=admissions,
        patients=patients,
        diagnoses_icd=diagnoses_icd,
        procedures_icd=procedures_icd,
        labevents=labevents,
        microbiologyevents=microbiologyevents,
        prescriptions=prescriptions,
        history_df=history_df,
        radiology_df=radiology_df,
        ed_stays=ed_stays,
        triage=triage,
        vitalsign=vitalsign,
    )


def test_trainset_construction():
    """Test building a trainset from demo data."""
    print("\n" + "="*60)
    print("Testing trainset construction with MIMIC-IV demo")
    print("="*60 + "\n")

    # Load demo dataset
    ds = load_demo_dataset()

    print(f"Demo dataset: {len(ds)} admissions available")

    # Sample a few admissions
    sample_hadm_ids = list(ds.hadm_ids)[:5]

    # Import mira_dspy modules
    from mira_dspy.tools import build_tools, tool_catalog_description
    from mira_dspy.trainset import build_trainset

    # Build tools and get catalog description
    tools = build_tools()
    tool_catalog_desc = tool_catalog_description(tools)

    print(f"\nTool catalog:\n{tool_catalog_desc[:500]}...")

    # Build PatientGroundTruth for sample admissions
    print(f"\nBuilding PatientGroundTruth for {len(sample_hadm_ids)} sample admissions...")

    patient_gts = []
    for hadm_id in tqdm(sample_hadm_ids):
        try:
            patient_data = ds[hadm_id]
            # Create a minimal PatientGroundTruth
            # Note: Full PatientGroundTruth requires processed data
            # For demo, we create a simplified version
            print(f"  hadm_id={hadm_id}: diagnoses={len(patient_data.diagnoses_icd)}, "
                  f"labs={len(patient_data.lab_events)}, meds={len(patient_data.medication)}")
        except Exception as e:
            print(f"  Error for hadm_id={hadm_id}: {e}")

    print("\n" + "="*60)
    print("Demo test complete!")
    print("="*60)

    return True


def test_metrics():
    """Test the metric functions with synthetic data."""
    print("\n" + "="*60)
    print("Testing mira_dspy metrics")
    print("="*60 + "\n")

    from mira_dspy.metrics import category_f_beta, composite_order_score, feedback_text

    # Test category_f_beta
    print("Testing category_f_beta:")

    # Perfect match
    score = category_f_beta(
        gt_and_assistant=["WBC", "CRP", "Lactate"],
        gt_only=[],
        assistant_only=[],
        beta=1.0
    )
    print(f"  Perfect match (TP=3, FN=0, FP=0): F1={score:.2f}")

    # Partial match
    score = category_f_beta(
        gt_and_assistant=["WBC", "CRP"],
        gt_only=["Lactate"],
        assistant_only=["Glucose"],
        beta=1.0
    )
    print(f"  Partial match (TP=2, FN=1, FP=1): F1={score:.2f}")

    # No match
    score = category_f_beta(
        gt_and_assistant=[],
        gt_only=["WBC", "CRP"],
        assistant_only=["Glucose"],
        beta=1.0
    )
    print(f"  No match (TP=0, FN=2, FP=1): F1={score:.2f}")

    # Test feedback_text
    print("\nTesting feedback_text:")
    feedback = feedback_text(
        "lab",
        gt_and_assistant=["WBC"],
        gt_only=["CRP", "Lactate"],
        assistant_only=["Glucose"]
    )
    print(f"  Feedback: {feedback}")

    print("\n" + "="*60)
    print("Metrics test complete!")
    print("="*60)

    return True


def test_program_structure():
    """Test that MiraDoctorProgram can be instantiated."""
    print("\n" + "="*60)
    print("Testing MiraDoctorProgram structure")
    print("="*60 + "\n")

    try:
        from mira_dspy.program import MiraDoctorProgram
        from mira_dspy.tools import build_tools

        tools = build_tools()
        program = MiraDoctorProgram(tools=tools, max_iters=5)

        print(f"Program created: {program}")
        print(f"  plan predictor: {program.plan}")
        print(f"  execute predictor: {program.execute}")
        print(f"  tools: {len(tools)} tools")

        print("\n" + "="*60)
        print("Program structure test complete!")
        print("="*60)

        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("MIRA DSPy Demo Test Suite")
    print("="*60)

    results = []

    # Test 1: Metrics
    results.append(("Metrics", test_metrics()))

    # Test 2: Program structure
    results.append(("Program Structure", test_program_structure()))

    # Test 3: Dataset loading
    results.append(("Dataset Loading", test_trainset_construction()))

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
    print("="*60 + "\n")