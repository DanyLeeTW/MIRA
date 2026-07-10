"""Process MIMIC-IV demo data with real clinical notes.

This version uses the actual discharge summaries and radiology reports
from the demo dataset, providing richer context for mira_dspy.
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
NOTE_DIR = MIMIC_DEMO_DIR / "note"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "demo_with_notes"


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

    # Load clinical notes
    try:
        tables["discharge"] = pd.read_csv(NOTE_DIR / "discharge.csv")
        tables["radiology_notes"] = pd.read_csv(NOTE_DIR / "radiology.csv")
        print(f"  Loaded {len(tables['discharge'])} discharge notes")
        print(f"  Loaded {len(tables['radiology_notes'])} radiology reports")
    except FileNotFoundError as e:
        print(f"  Warning: Could not load notes: {e}")
        tables["discharge"] = pd.DataFrame(columns=["hadm_id"])
        tables["radiology_notes"] = pd.DataFrame(columns=["hadm_id"])

    # Load ED data
    try:
        tables["ed_stays"] = pd.read_csv(ED_DIR / "edstays.csv")
        tables["triage"] = pd.read_csv(ED_DIR / "triage.csv")
    except FileNotFoundError:
        tables["ed_stays"] = pd.DataFrame(columns=["stay_id"])
        tables["triage"] = pd.DataFrame(columns=["stay_id"])

    return tables


def extract_discharge_sections(text: str) -> dict:
    """Extract key sections from discharge summary."""
    if not isinstance(text, str):
        return {
            "chief_complaint": "Unknown",
            "history": "No history available.",
            "diagnosis_text": "Unknown",
        }

    sections = {
        "chief_complaint": "Unknown",
        "history": "No history available.",
        "diagnosis_text": "Unknown",
    }

    # Extract Chief Complaint
    if "CHIEF COMPLAINT:" in text:
        start = text.find("CHIEF COMPLAINT:") + len("CHIEF COMPLAINT:")
        end = text.find("\n\n", start)
        if end == -1:
            end = text.find("\n", start)
        sections["chief_complaint"] = text[start:end].strip()

    # Extract History of Present Illness
    if "HISTORY OF PRESENT ILLNESS:" in text:
        start = text.find("HISTORY OF PRESENT ILLNESS:") + len("HISTORY OF PRESENT ILLNESS:")
        # Find next section header (all caps followed by colon)
        end = len(text)
        for marker in ["\n\nPHYSICAL EXAM", "\n\nDISCHARGE DIAGNOSIS", "\n\nPAST MEDICAL",
                       "\n\nHOSPITAL COURSE", "\n\nFAMILY HISTORY", "\n\nSOCIAL HISTORY"]:
            pos = text.find(marker, start)
            if pos != -1 and pos < end:
                end = pos
        sections["history"] = text[start:end].strip()

    # Extract Discharge Diagnosis
    if "DISCHARGE DIAGNOSIS:" in text:
        start = text.find("DISCHARGE DIAGNOSIS:") + len("DISCHARGE DIAGNOSIS:")
        end = text.find("\n\n", start)
        if end == -1:
            end = min(start + 500, len(text))
        sections["diagnosis_text"] = text[start:end].strip()

    return sections


def build_admission_records(tables: dict) -> dict:
    """Build per-admission records with real clinical notes."""
    print("Building admission records with clinical notes...")

    admissions = tables["admissions"]
    admissions_with_notes = set(tables["discharge"]["hadm_id"].unique()) if len(tables["discharge"]) > 0 else set()

    # Get admissions that have either diagnoses or discharge notes
    admissions_with_diagnoses = set(tables["diagnoses_icd"]["hadm_id"].unique())
    hadm_ids = admissions_with_notes | admissions_with_diagnoses

    print(f"Found {len(admissions_with_notes)} admissions with discharge notes")
    print(f"Processing {len(hadm_ids)} total admissions...")

    records = {}

    for hadm_id in tqdm(hadm_ids):
        # Get admission info
        adm_df = admissions[admissions["hadm_id"] == hadm_id]
        if len(adm_df) == 0:
            continue
        adm = adm_df.iloc[0]
        subject_id = adm["subject_id"]

        # Get patient info
        patient_df = tables["patients"][tables["patients"]["subject_id"] == subject_id]
        if len(patient_df) == 0:
            continue
        patient = patient_df.iloc[0]

        # Get discharge note (real clinical text!)
        discharge_df = tables["discharge"][tables["discharge"]["hadm_id"] == hadm_id]
        if len(discharge_df) > 0:
            discharge_text = discharge_df.iloc[0]["text"]
            sections = extract_discharge_sections(discharge_text)
            chief_complaint = sections["chief_complaint"]
            history = sections["history"]
            diagnosis_text = sections["diagnosis_text"]
        else:
            # Fallback to triage data
            triage_df = tables["triage"][tables["triage"]["stay_id"] == hadm_id]
            if len(triage_df) > 0 and "chiefcomplaint" in triage_df.columns:
                chief_complaint = triage_df.iloc[0].get("chiefcomplaint", "Unknown")
                if pd.isna(chief_complaint):
                    chief_complaint = "Unknown"
            else:
                chief_complaint = "Unknown"
            history = f"Patient is a {patient.get('anchor_age', 'unknown')} year old."
            diagnosis_text = "Unknown"

        # Get radiology reports
        rad_df = tables["radiology_notes"][tables["radiology_notes"]["hadm_id"] == hadm_id]
        radiology_reports = []
        if len(rad_df) > 0:
            for _, row in rad_df.head(5).iterrows():
                text = row.get("text", "")
                if isinstance(text, str) and len(text) > 50:
                    radiology_reports.append(text[:500])

        # Get diagnoses
        diagnoses = tables["diagnoses_icd"][tables["diagnoses_icd"]["hadm_id"] == hadm_id]
        primary_diag = diagnoses[diagnoses["seq_num"] == 1]
        if len(primary_diag) == 0 and len(diagnoses) > 0:
            primary_diag = diagnoses.iloc[0:1]

        # Get diagnosis label
        if len(primary_diag) > 0:
            icd_code = primary_diag.iloc[0]["icd_code"]
            diag_lookup = tables["d_icd_diagnoses"][
                tables["d_icd_diagnoses"]["icd_code"] == icd_code
            ]
            if len(diag_lookup) > 0:
                diagnosis_name = diag_lookup.iloc[0].get("long_title", icd_code)
            else:
                diagnosis_name = icd_code
        else:
            icd_code = None
            diagnosis_name = diagnosis_text[:200] if diagnosis_text != "Unknown" else "Unknown"

        # Get procedures
        procedures = tables["procedures_icd"][tables["procedures_icd"]["hadm_id"] == hadm_id]
        proc_codes = procedures["icd_code"].tolist() if len(procedures) > 0 else []

        # Get labs
        labs = tables["labevents"][tables["labevents"]["hadm_id"] == hadm_id]

        # Get microbiology
        micro = tables["microbiologyevents"][
            tables["microbiologyevents"]["hadm_id"] == hadm_id
        ]

        # Get medications
        meds = tables["prescriptions"][tables["prescriptions"]["hadm_id"] == hadm_id]

        records[hadm_id] = {
            "hadm_id": int(hadm_id),
            "subject_id": int(subject_id),
            "gender": patient.get("gender"),
            "age": int(patient.get("anchor_age")) if pd.notna(patient.get("anchor_age")) else None,
            "admission_type": adm.get("admission_type"),
            "chief_complaint": chief_complaint,
            "history": history,
            "diagnosis_icd": icd_code,
            "diagnosis_name": diagnosis_name,
            "diagnosis_text": diagnosis_text,
            "radiology_reports": radiology_reports,
            "lab_events_count": int(len(labs)),
            "microbiology_count": int(len(micro)),
            "medication_count": int(len(meds)),
            "procedure_codes": proc_codes,
        }

    return records


def save_processed_data(records: dict, output_dir: Path):
    """Save processed records to JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    records_dir = output_dir / "records"
    records_dir.mkdir(exist_ok=True)

    print(f"Saving {len(records)} records to {output_dir}...")

    for hadm_id, record in tqdm(records.items()):
        # Convert numpy types
        record_serializable = {}
        for k, v in record.items():
            if isinstance(v, (int, float, str, bool, list, dict, type(None))):
                record_serializable[k] = v
            elif hasattr(v, "item"):
                record_serializable[k] = v.item()
            else:
                record_serializable[k] = str(v)

        path = records_dir / f"{hadm_id}.json"
        with open(path, "w") as f:
            json.dump(record_serializable, f, indent=2)

    summary = {
        "total_admissions": len(records),
        "hadm_ids": [int(h) for h in records.keys()],
        "schema_version": "2.0",
        "source": "mimic_demo_2.2_with_notes",
        "features": ["discharge_summaries", "radiology_reports", "clinical_notes"],
    }

    with open(output_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    df = pd.DataFrame.from_dict(records, orient="index")
    df.to_csv(output_dir / "admissions_summary.csv", index=False)

    print(f"Saved to {output_dir}")


def main():
    print("="*60)
    print("Processing MIMIC-IV Demo with Clinical Notes")
    print("="*60)

    tables = load_raw_tables()
    records = build_admission_records(tables)
    save_processed_data(records, OUTPUT_DIR)

    print("\n" + "="*60)
    print("Processing Complete!")
    print("="*60)
    print(f"Total admissions processed: {len(records)}")
    print(f"Output directory: {OUTPUT_DIR}")

    # Show sample
    if records:
        # Find a record with rich notes
        sample_id = None
        for hid, rec in records.items():
            if len(rec.get("radiology_reports", [])) > 0 and rec.get("history") != "No history available.":
                sample_id = hid
                break
        if sample_id is None:
            sample_id = list(records.keys())[0]

        sample = records[sample_id]
        print(f"\nSample record (hadm_id={sample_id}):")
        print(f"  Diagnosis: {sample['diagnosis_name']}")
        print(f"  Chief Complaint: {sample['chief_complaint'][:100]}...")
        print(f"  History length: {len(sample['history'])} chars")
        print(f"  Radiology reports: {len(sample.get('radiology_reports', []))}")
        print(f"  Labs: {sample['lab_events_count']} events")


if __name__ == "__main__":
    main()