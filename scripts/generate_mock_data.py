#!/usr/bin/env python3
"""
生成 MIRA 的模拟数据用于测试

这个脚本创建符合 MIRA 数据格式的模拟数据，
让你可以在没有 MIMIC-IV 数据的情况下运行和测试流程。

使用方法:
    python scripts/generate_mock_data.py --output-dir src/raw/derived/diagnosis_datasets/demo_test
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

# 诊断类型
DIAGNOSES = ["appendicitis", "cholecystitis", "diverticulitis", "pancreatitis", "uti", "pneumonia", "pulmonary_embolism", "pancreatic_cancer"]

def generate_mock_data(diagnosis: str, num_patients: int = 10):
    """生成模拟患者数据"""
    
    np.random.seed(42)
    
    patients = []
    admissions = []
    diagnoses_icd = []
    labevents = []
    microbiology = []
    radiology = []
    discharge = []
    
    for i in range(num_patients):
        subject_id = 10000000 + i
        hadm_id = 20000000 + i
        stay_id = 30000000 + i
        
        # 患者基本信息
        patients.append({
            "subject_id": subject_id,
            "gender": np.random.choice(["M", "F"]),
            "anchor_age": np.random.randint(30, 80),
            "anchor_year": 2020,
            "anchor_year_group": "2020-2022",
            "dod": None,
        })
        
        # 入院信息
        admissions.append({
            "subject_id": subject_id,
            "hadm_id": hadm_id,
            "admittime": "2020-01-01 10:00:00",
            "dischtime": "2020-01-05 15:00:00",
            "deathtime": None,
            "admission_type": "emergency",
            "admission_location": "EMERGENCY ROOM",
            "discharge_location": "HOME",
            "insurance": "Medicare",
            "language": "ENGLISH",
            "marital_status": "MARRIED",
            "race": "WHITE",
            "edregtime": "2020-01-01 09:00:00",
            "edouttime": "2020-01-01 10:00:00",
            "hospital_expire_flag": 0,
        })
        
        # ICD 诊断代码
        icd_codes = {
            "appendicitis": ["K35.80", "K35.89", "K35.91"],
            "cholecystitis": ["K80.00", "K81.00", "K81.10"],
            "diverticulitis": ["K57.00", "K57.30", "K57.90"],
            "pancreatitis": ["K85.00", "K85.10", "K85.90"],
            "uti": ["N39.0", "N30.00", "N30.90"],
            "pneumonia": ["J18.9", "J15.9", "J12.9"],
            "pulmonary_embolism": ["I26.99", "I26.09", "I26.92"],
            "pancreatic_cancer": ["C25.0", "C25.9", "C25.8"],
        }
        
        for icd in icd_codes.get(diagnosis, ["R69"]):
            diagnoses_icd.append({
                "subject_id": subject_id,
                "hadm_id": hadm_id,
                "seq_num": 1,
                "icd_code": icd,
                "icd_version": 10,
            })
        
        # 实验室检查
        lab_items = [
            ("WBC", 5.0, 15.0, "K/uL"),
            ("Hemoglobin", 10.0, 16.0, "g/dL"),
            ("Platelet", 150, 400, "K/uL"),
            ("Creatinine", 0.5, 2.0, "mg/dL"),
            ("Sodium", 135, 145, "mEq/L"),
            ("Potassium", 3.5, 5.5, "mEq/L"),
            ("Glucose", 70, 200, "mg/dL"),
        ]
        
        for lab_name, low, high, unit in lab_items:
            labevents.append({
                "subject_id": subject_id,
                "hadm_id": hadm_id,
                "labevent_id": len(labevents) + 1,
                "itemid": len(labevents) + 1000,
                "charttime": "2020-01-01 12:00:00",
                "valuenum": np.random.uniform(low, high),
                "valueuom": unit,
                "label": lab_name,
                "fluid": "Blood",
                "category": "Hematology",
            })
        
        # 放射检查
        radiology.append({
            "subject_id": subject_id,
            "hadm_id": hadm_id,
            "note_id": f"radiology_{i}",
            "chartdate": "2020-01-01",
            "text": f"CT Abdomen/Pelvis: Findings consistent with {diagnosis.replace('_', ' ')}. No acute abnormalities noted.",
        })
        
        # 出院小结
        discharge.append({
            "subject_id": subject_id,
            "hadm_id": hadm_id,
            "note_id": f"discharge_{i}",
            "chartdate": "2020-01-05",
            "text": f"DISCHARGE SUMMARY\n\nDiagnosis: {diagnosis.replace('_', ' ').title()}\n\nPatient presented with symptoms consistent with {diagnosis.replace('_', ' ')}. Appropriate workup was performed. Patient was treated and discharged in stable condition.",
        })
    
    return {
        "patients": pd.DataFrame(patients),
        "admissions": pd.DataFrame(admissions),
        "diagnoses_icd": pd.DataFrame(diagnoses_icd),
        "labevents": pd.DataFrame(labevents),
        "radiology": pd.DataFrame(radiology),
        "discharge": pd.DataFrame(discharge),
    }


def main():
    parser = argparse.ArgumentParser(description="生成 MIRA 模拟数据")
    parser.add_argument("--diagnosis", type=str, default="appendicitis", help="诊断类型")
    parser.add_argument("--num-patients", type=int, default=10, help="患者数量")
    parser.add_argument("--output-dir", type=str, default="src/raw/derived/diagnosis_datasets/demo_test", help="输出目录")
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir) / args.diagnosis
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"生成 {args.diagnosis} 的模拟数据 ({args.num_patients} 患者)...")
    data = generate_mock_data(args.diagnosis, args.num_patients)
    
    for table_name, df in data.items():
        output_path = output_dir / f"{table_name}.parquet"
        df.to_parquet(output_path, index=False)
        print(f"  保存 {table_name}: {len(df)} 行 -> {output_path}")
    
    print(f"\n完成! 数据保存在: {output_dir}")
    print("\n要使用这些数据运行 MIRA:")
    print(f"  export MIRA_DIAGNOSIS_DATASETS_DIR={Path(args.output_dir).absolute()}")
    print(f"  export MIRA_DATASET_DIAGNOSES={args.diagnosis}")
    print(f"  export MIRA_MAX_HADM_IDS_PER_DIAGNOSIS={args.num_patients}")


if __name__ == "__main__":
    main()
