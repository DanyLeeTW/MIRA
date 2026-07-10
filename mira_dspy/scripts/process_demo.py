"""Process MIMIC-IV demo data into a format compatible with mira_dspy.

This script creates a minimal dataset from the demo CSV files that can be used
to test the mira_dspy pipeline without requiring the full preprocessed data.

Usage:
    cd mira_dspy
    source .venv/bin/activate
    python scripts/process_demo.py
"""

import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pandas as pd
from tqdm import tqdm

# Configure paths
MIMIC_DEMO_DIR = Path(__file__).parent.parent.parent / "mimic_demo" / "2.2"
HOSP_DIR = MIMIC_DEMO_DIR / "hosp"
ED_DIR = MIMIC_DEMO_DIR / "ed"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "demo_processed"


def load_raw_tables():
    """Load all raw CSV tables from demo dataset."""
    print("Loading raw tables...")

    tables = {
        "admissions": pd.read_csv(HOSP_DIR / "admissions.csv"),
        "patients": pd.read_csv(HOSP_DIR / "patients.csv"),
        "diagnoses_icd": pd.read_csv(HOSP_DIR / "diagnoses_icd.csv"),
        "procedures_icd": pd.read_csv(HOSP_DIR / "procedures_icd.csv"),
        "labevents": pd.read_csv(HOSP_DIR / "labevents.csv"),
        "microbiologyevents": pd.read_csv(HOSP_DIR / "microbiologyevents.csv"),
        "prescriptions": pd.read_csv(HOSP_DIR / "prescriptions.csv"),
        "d_labitems": pd.read_csv(HOSP_DIR / "d_labitems.csv"),
        "d_icd_diagnoses": pd.read_csv(HOSP_DIR / "d_icd_diagnoses.csv"),
    }

    # Load ED data if available
    try:
        tables["ed_stays"] = pd.read_csv(ED_DIR / "edstays.csv")
        tables["triage"] = pd.read_csv(ED_DIR / "triage.csv")
    except FileNotFoundError:
        tables["ed_stays"] = pd.DataFrame(columns=["hadm_id", "subject_id"])
        tables["triage"] = pd.DataFrame(columns=["hadm_id", "subject_id"])

    return tables


def build_admission_records(tables: dict) -> dict:
    """Build per-admission records with all associated data."""
    print("Building admission records...")

    admissions = tables["admissions"]
    admissions_with_data = admissions[
        admissions["hadm_id"].isin(tables["diagnoses_icd"]["hadm_id"])
    ]

    records = {}
    hadm_ids = set(admissions_with_data["hadm_id"].unique())

    print(f"Processing {len(hadm_ids)} admissions with diagnoses...")

    for hadm_id in tqdm(hadm_ids):
        # Get admission info
        adm = admissions[admissions["hadm_id"] == hadm_id].iloc[0]
        subject_id = adm["subject_id"]

        # Get patient info
        patient = tables["patients"][tables["patients"]["subject_id"] == subject_id]
        if len(patient) == 0:
            continue
        patient = patient.iloc[0]

        # Get diagnoses
        diagnoses = tables["diagnoses_icd"][tables["diagnoses_icd"]["hadm_id"] == hadm_id]

        # Get primary diagnosis (seq_num == 1)
        primary_diag = diagnoses[diagnoses["seq_num"] == 1]
        if len(primary_diag) == 0:
            primary_diag = diagnoses.iloc[0] if len(diagnoses) > 0 else None

        # Get procedures
        procedures = tables["procedures_icd"][tables["procedures_icd"]["hadm_id"] == hadm_id]

        # Get labs
        labs = tables["labevents"][tables["labevents"]["hadm_id"] == hadm_id]

        # Get microbiology
        micro = tables["microbiologyevents"][
            tables["microbiologyevents"]["hadm_id"] == hadm_id
        ]

        # Get medications
        meds = tables["prescriptions"][tables["prescriptions"]["hadm_id"] == hadm_id]

        # Build lab summary (first 24h)
        if len(labs) > 0:
            labs = labs.sort_values("charttime")
            lab_summary = []
            lab_items = labs.merge(tables["d_labitems"], on="itemid", how="left")
            for _, row in lab_items.head(50).iterrows():
                label = row.get("label", "Unknown")
                value = row.get("valuenum", row.get("value", ""))
                unit = row.get("valueuom", "")
                if pd.notna(value):
                    lab_summary.append(f"{label}: {value} {unit}")
        else:
            lab_summary = []

        # Build medication summary
        if len(meds) > 0:
            med_summary = []
            for _, row in meds.head(20).iterrows():
                drug = row.get("drug", "Unknown")
                dose = row.get("dose_val_rx", "")
                unit = row.get("dose_unit_rx", "")
                med_summary.append(f"{drug} {dose}{unit}")
        else:
            med_summary = []

        # Build procedure summary
        if len(procedures) > 0:
            proc_summary = procedures["icd_code"].tolist()
        else:
            proc_summary = []

        # Get chief complaint from triage (use stay_id which maps to hadm_id)
        triage = tables["triage"][tables["triage"]["stay_id"] == hadm_id]
        if len(triage) > 0 and "chiefcomplaint" in triage.columns:
            chief_complaint = triage.iloc[0].get("chiefcomplaint", "Unknown")
            if pd.isna(chief_complaint):
                chief_complaint = "Unknown"
        else:
            chief_complaint = "Unknown"

        # Build synthetic history (since demo lacks discharge notes)
        history = f"""Patient is a {patient.get('anchor_age', 'unknown')} year old {patient.get('gender', 'unknown').lower()}.

Chief Complaint: {chief_complaint}

Admission Type: {adm.get('admission_type', 'unknown')}

Recent Lab Results:
{chr(10).join(lab_summary[:10]) if lab_summary else 'No lab results available.'}

Current Medications:
{chr(10).join(med_summary[:10]) if med_summary else 'No current medications.'}
"""

        # Get diagnosis label
        if primary_diag is not None and len(primary_diag) > 0:
            icd_code = primary_diag.iloc[0]["icd_code"]
            # Look up diagnosis name
            diag_lookup = tables["d_icd_diagnoses"][
                tables["d_icd_diagnoses"]["icd_code"] == icd_code
            ]
            if len(diag_lookup) > 0:
                diagnosis_name = diag_lookup.iloc[0].get("long_title", icd_code)
            else:
                diagnosis_name = icd_code
        else:
            diagnosis_name = "Unknown"

        records[hadm_id] = {
            "hadm_id": hadm_id,
            "subject_id": subject_id,
            "gender": patient.get("gender"),
            "age": patient.get("anchor_age"),
            "admission_type": adm.get("admission_type"),
            "chief_complaint": chief_complaint,
            "history": history,
            "diagnosis_icd": icd_code if primary_diag is not None else None,
            "diagnosis_name": diagnosis_name,
            "lab_events_count": len(labs),
            "microbiology_count": len(micro),
            "medication_count": len(meds),
            "procedure_codes": proc_summary,
        }

    return records


def save_processed_data(records: dict, output_dir: Path):
    """Save processed records to JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save individual records
    records_dir = output_dir / "records"
    records_dir.mkdir(exist_ok=True)

    print(f"Saving {len(records)} records to {output_dir}...")

    for hadm_id, record in tqdm(records.items()):
        # Convert numpy types to native Python types for JSON serialization
        record_serializable = {}
        for k, v in record.items():
            if isinstance(v, (int, float, str, bool, list, dict, type(None))):
                record_serializable[k] = v
            elif hasattr(v, "item"):  # numpy type
                record_serializable[k] = v.item()
            else:
                record_serializable[k] = str(v)

        path = records_dir / f"{hadm_id}.json"
        with open(path, "w") as f:
            json.dump(record_serializable, f, indent=2)

    # Save summary
    summary = {
        "total_admissions": len(records),
        "hadm_ids": [int(h) for h in records.keys()],  # Convert to native int
        "schema_version": "1.0",
        "source": "mimic_demo_2.2",
    }

    with open(output_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Save as DataFrame for easy loading
    df = pd.DataFrame.from_dict(records, orient="index")
    df.to_csv(output_dir / "admissions_summary.csv", index=False)

    print(f"Saved to {output_dir}")


def main():
    print("="*60)
    print("Processing MIMIC-IV Demo for mira_dspy")
    print("="*60)

    # Load raw tables
    tables = load_raw_tables()

    # Build admission records
    records = build_admission_records(tables)

    # Save processed data
    save_processed_data(records, OUTPUT_DIR)

    # Print summary
    print("\n" + "="*60)
    print("Processing Complete!")
    print("="*60)
    print(f"Total admissions processed: {len(records)}")
    print(f"Output directory: {OUTPUT_DIR}")

    # Show sample record
    if records:
        sample_id = list(records.keys())[0]
        sample = records[sample_id]
        print(f"\nSample record (hadm_id={sample_id}):")
        print(f"  Diagnosis: {sample['diagnosis_name']}")
        print(f"  Labs: {sample['lab_events_count']} events")
        print(f"  Medications: {sample['medication_count']} orders")
        print(f"  Procedures: {len(sample['procedure_codes'])} codes")


if __name__ == "__main__":
    main()