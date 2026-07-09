#!/usr/bin/env python3
"""
为 MIMIC-IV Demo 生成补充数据（包括 radiology_detail）
"""

import pandas as pd
import numpy as np
from pathlib import Path

DEMO_DIR = Path("mimic_demo/2.2")
HOSP_DIR = DEMO_DIR / "hosp"
NOTE_DIR = DEMO_DIR / "note"
ED_DIR = DEMO_DIR / "ed"
NOTE_DIR.mkdir(exist_ok=True)
ED_DIR.mkdir(exist_ok=True)

def generate_discharge_notes():
    patients = pd.read_csv(HOSP_DIR / "patients.csv")
    admissions = pd.read_csv(HOSP_DIR / "admissions.csv")
    diagnoses_icd = pd.read_csv(HOSP_DIR / "diagnoses_icd.csv")
    d_icd_diagnoses = pd.read_csv(HOSP_DIR / "d_icd_diagnoses.csv")
    
    diagnoses_annot = diagnoses_icd.merge(
        d_icd_diagnoses[["icd_code", "icd_version", "long_title"]],
        on=["icd_version", "icd_code"],
        how="left"
    )
    
    discharge_records = []
    for _, adm in admissions.iterrows():
        subject_id = adm["subject_id"]
        hadm_id = adm["hadm_id"]
        patient_diagnoses = diagnoses_annot[diagnoses_annot["hadm_id"] == hadm_id]
        diagnosis_text = "; ".join(patient_diagnoses["long_title"].dropna().head(3).tolist())
        if not diagnosis_text:
            diagnosis_text = "Unspecified condition"
        
        text = f"""DISCHARGE SUMMARY

Patient ID: {subject_id}
Admission ID: {hadm_id}

CHIEF COMPLAINT:
Patient presented to the emergency department with acute symptoms.

HISTORY OF PRESENT ILLNESS:
Patient was admitted for evaluation and management. Workup was performed including laboratory studies and imaging as indicated.

DIAGNOSIS:
{diagnosis_text}

HOSPITAL COURSE:
Patient was treated appropriately during hospitalization. Condition improved with treatment.

DISPOSITION:
Patient was discharged home in stable condition.

FOLLOW-UP:
Follow-up with primary care physician in 1-2 weeks.
"""
        discharge_records.append({
            "note_id": f"discharge_{hadm_id}",
            "subject_id": subject_id,
            "hadm_id": hadm_id,
            "note_type": "discharge",
            "chartdate": adm.get("dischtime", "2020-01-01"),
            "text": text
        })
    
    df = pd.DataFrame(discharge_records)
    df.to_csv(NOTE_DIR / "discharge.csv", index=False)
    print(f"Generated {len(df)} discharge notes")


def generate_radiology_and_detail():
    admissions = pd.read_csv(HOSP_DIR / "admissions.csv")
    
    radiology_records = []
    detail_records = []
    
    for _, adm in admissions.iterrows():
        subject_id = adm["subject_id"]
        hadm_id = adm["hadm_id"]
        note_id = f"radiology_{hadm_id}"
        
        text = f"""RADIOLOGY REPORT

Exam: CT Abdomen and Pelvis with Contrast
Patient ID: {subject_id}
Admission ID: {hadm_id}

INDICATION:
Abdominal pain evaluation.

FINDINGS:
The visualized portions of the abdomen and pelvis are within normal limits. No acute intra-abdominal process identified.

IMPRESSION:
No acute findings. Clinical correlation recommended.
"""
        radiology_records.append({
            "note_id": note_id,
            "subject_id": subject_id,
            "hadm_id": hadm_id,
            "note_type": "radiology",
            "chartdate": adm.get("admittime", "2020-01-01"),
            "text": text
        })
        
        detail_records.append({
            "note_id": note_id,
            "subject_id": subject_id,
            "hadm_id": hadm_id,
            "field_name": "report",
            "field_value": text,
            "seq_num": 1
        })
    
    pd.DataFrame(radiology_records).to_csv(NOTE_DIR / "radiology.csv", index=False)
    pd.DataFrame(detail_records).to_csv(NOTE_DIR / "radiology_detail.csv", index=False)
    print(f"Generated {len(radiology_records)} radiology reports + details")


def generate_ed_tables():
    admissions = pd.read_csv(HOSP_DIR / "admissions.csv")
    
    edstays_records = []
    triage_records = []
    vitalsign_records = []
    diagnosis_ed_records = []
    medrecon_records = []
    
    for _, adm in admissions.iterrows():
        subject_id = adm["subject_id"]
        hadm_id = adm["hadm_id"]
        stay_id = hadm_id
        
        edstays_records.append({
            "subject_id": subject_id,
            "stay_id": stay_id,
            "hadm_id": hadm_id,
            "intime": adm.get("admittime", "2020-01-01 10:00:00"),
            "outtime": adm.get("admittime", "2020-01-01 12:00:00"),
        })
        
        triage_records.append({
            "subject_id": subject_id,
            "stay_id": stay_id,
            "temperature": round(np.random.uniform(36.5, 38.5), 1),
            "heartrate": np.random.randint(60, 100),
            "resprate": np.random.randint(12, 20),
            "o2sat": np.random.randint(95, 100),
            "sbp": np.random.randint(110, 140),
            "dbp": np.random.randint(70, 90),
            "pain": np.random.randint(0, 10),
            "chiefcomplaint": "Abdominal pain",
        })
        
        vitalsign_records.append({
            "subject_id": subject_id,
            "stay_id": stay_id,
            "charttime": adm.get("admittime", "2020-01-01 11:00:00"),
            "temperature": round(np.random.uniform(36.5, 38.0), 1),
            "heartrate": np.random.randint(60, 100),
            "resprate": np.random.randint(12, 20),
            "o2sat": np.random.randint(95, 100),
        })
        
        diagnosis_ed_records.append({
            "subject_id": subject_id,
            "stay_id": stay_id,
            "icd_code": "R10.9",
            "icd_version": 10,
        })
        
        medrecon_records.append({
            "subject_id": subject_id,
            "stay_id": stay_id,
            "name": "Medication Reconciliation",
            "formulary_drug_cd": "N/A"
        })
    
    pd.DataFrame(edstays_records).to_csv(ED_DIR / "edstays.csv", index=False)
    pd.DataFrame(triage_records).to_csv(ED_DIR / "triage.csv", index=False)
    pd.DataFrame(vitalsign_records).to_csv(ED_DIR / "vitalsign.csv", index=False)
    pd.DataFrame(diagnosis_ed_records).to_csv(ED_DIR / "diagnosis.csv", index=False)
    pd.DataFrame(medrecon_records).to_csv(ED_DIR / "medrecon.csv", index=False)
    print(f"Generated ED tables: {len(edstays_records)} records each")


def main():
    print("Generating supplemental data for MIMIC-IV Demo...")
    print(f"  HOSP: {HOSP_DIR}")
    print(f"  NOTE: {NOTE_DIR}")
    print(f"  ED:   {ED_DIR}")
    print()
    generate_discharge_notes()
    generate_radiology_and_detail()
    generate_ed_tables()
    print("\nDone! Demo data is now complete.")

if __name__ == "__main__":
    main()
