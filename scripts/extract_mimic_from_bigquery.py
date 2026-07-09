#!/usr/bin/env python3
"""
MIRA BigQuery Data Extractor

从 BigQuery 导出 MIRA 需要的最小数据集（仅特定诊断的患者数据）。
这比下载整个 MIMIC-IV 数据集快很多。

用法:
    python extract_mimic_from_bigquery.py --diagnosis appendicitis --max-patients 50

需要先安装:
    pip install google-cloud-bigquery pandas db-dtypes
"""

import argparse
import os
from pathlib import Path

import pandas as pd
from google.cloud import bigquery

# MIRA 需要的诊断列表
DIAGNOSES = [
    "appendicitis",
    "cholecystitis",
    "diverticulitis",
    "pancreatitis",
    "uti",
    "pneumonia",
    "pulmonary_embolism",
    "pancreatic_cancer",
]

# BigQuery 数据集路径
PROJECT_ID = "physionet-data"
DATASET_HOSP = f"{PROJECT_ID}.mimiciv_hosp"
DATASET_ED = f"{PROJECT_ID}.mimiciv_ed"
DATASET_NOTE = f"{PROJECT_ID}.mimiciv_note"

# 诊断过滤条件 (基于 ICD codes 或 ED diagnosis)
DIAGNOSIS_FILTERS = {
    "appendicitis": {
        "icd_codes": ["K35", "K35.0", "K35.1", "K35.2", "K35.3", "K35.8", "K35.9"],
        "ed_diagnosis": [
            "Acute appendicitis without mention of peritonitis",
            "Unspecified acute appendicitis",
            "Acute appendicitis with peritoneal abscess",
        ],
    },
    "cholecystitis": {
        "icd_codes": ["K80.0", "K80.1", "K80.2", "K80.3", "K80.4", "K81.0", "K81.1", "K81.8", "K81.9"],
        "ed_diagnosis": [
            "Acute cholecystitis",
            "Calculus of gallbladder with acute cholecystitis",
        ],
    },
    "diverticulitis": {
        "icd_codes": ["K57.0", "K57.1", "K57.2", "K57.3", "K57.4", "K57.8", "K57.9"],
        "ed_diagnosis": ["Diverticulitis of colon"],
    },
    "pancreatitis": {
        "icd_codes": ["K85.0", "K85.1", "K85.2", "K85.3", "K85.8", "K85.9", "K86.0", "K86.1"],
        "ed_diagnosis": ["Acute pancreatitis", "Biliary acute pancreatitis"],
    },
    "uti": {
        "icd_codes": ["N39.0", "N10", "N11", "N12", "N30.0", "N30.9"],
        "ed_diagnosis": ["Urinary tract infection, site not specified"],
    },
    "pneumonia": {
        "icd_codes": ["J12", "J13", "J14", "J15", "J16", "J17", "J18.0", "J18.1", "J18.8", "J18.9"],
        "ed_diagnosis": ["Pneumonia, unspecified organism"],
    },
    "pulmonary_embolism": {
        "icd_codes": ["I26.0", "I26.9", "I26.01", "I26.02", "I26.09", "I26.92", "I26.93", "I26.94", "I26.99"],
        "ed_diagnosis": ["Other pulmonary embolism without acute cor pulmonale"],
    },
    "pancreatic_cancer": {
        "icd_codes": ["C25.0", "C25.1", "C25.2", "C25.3", "C25.4", "C25.7", "C25.8", "C25.9"],
        "ed_diagnosis": ["Malignant neoplasm of head of pancreas"],
    },
}


def get_client():
    """创建 BigQuery 客户端"""
    return bigquery.Client()


def get_hadm_ids_for_diagnosis(client: bigquery.Client, diagnosis: str, max_patients: int = None) -> list:
    """
    获取特定诊断的 hadm_id 列表
    """
    filters = DIAGNOSIS_FILTERS.get(diagnosis, {})
    icd_codes = filters.get("icd_codes", [])

    if not icd_codes:
        print(f"警告: 没有为 {diagnosis} 找到 ICD codes")
        return []

    # 构建 ICD code 查询条件
    icd_condition = " OR ".join([f"icd_code LIKE '{code}%'" for code in icd_codes])

    limit_clause = f"LIMIT {max_patients}" if max_patients else ""

    query = f"""
    SELECT DISTINCT hadm_id
    FROM `{DATASET_HOSP}.diagnoses_icd`
    WHERE {icd_condition}
    {limit_clause}
    """

    print(f"查询 {diagnosis} 的 hadm_ids...")
    print(f"  Query: {query[:200]}...")

    result = client.query(query).result()
    hadm_ids = [row.hadm_id for row in result]

    print(f"  找到 {len(hadm_ids)} 个 hadm_ids")
    return hadm_ids


def extract_table_for_hadm_ids(
    client: bigquery.Client,
    table_name: str,
    hadm_ids: list,
    output_dir: Path,
    dataset: str = DATASET_HOSP,
    subject_id_table: str = None,
):
    """
    提取特定 hadm_ids 的数据
    """
    if not hadm_ids:
        print(f"  跳过 {table_name}: 没有 hadm_ids")
        return None

    # 分批处理避免查询过长
    batch_size = 5000
    all_dfs = []

    for i in range(0, len(hadm_ids), batch_size):
        batch = hadm_ids[i:i + batch_size]
        hadm_list = ",".join(str(h) for h in batch)

        query = f"""
        SELECT *
        FROM `{dataset}.{table_name}`
        WHERE hadm_id IN ({hadm_list})
        """

        print(f"  查询 {table_name} (batch {i//batch_size + 1}/{(len(hadm_ids)-1)//batch_size + 1})...")
        result = client.query(query).result()
        df = result.to_dataframe()

        if not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        print(f"  {table_name}: 没有数据")
        return None

    final_df = pd.concat(all_dfs, ignore_index=True)
    output_path = output_dir / f"{table_name}.parquet"
    final_df.to_parquet(output_path, index=False)
    print(f"  保存 {table_name}: {len(final_df)} 行 -> {output_path}")

    return final_df


def extract_ed_table_for_stay_ids(
    client: bigquery.Client,
    table_name: str,
    stay_ids: list,
    output_dir: Path,
):
    """
    提取 ED 数据（基于 stay_id）
    """
    if not stay_ids:
        return None

    batch_size = 5000
    all_dfs = []

    for i in range(0, len(stay_ids), batch_size):
        batch = stay_ids[i:i + batch_size]
        stay_list = ",".join(str(s) for s in batch)

        query = f"""
        SELECT *
        FROM `{DATASET_ED}.{table_name}`
        WHERE stay_id IN ({stay_list})
        """

        print(f"  查询 ED.{table_name} (batch {i//batch_size + 1})...")
        result = client.query(query).result()
        df = result.to_dataframe()

        if not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        return None

    final_df = pd.concat(all_dfs, ignore_index=True)
    output_path = output_dir / f"{table_name}.parquet"
    final_df.to_parquet(output_path, index=False)
    print(f"  保存 ED.{table_name}: {len(final_df)} 行")

    return final_df


def extract_diagnosis_dataset(
    diagnosis: str,
    output_base_dir: Path,
    max_patients: int = None,
):
    """
    提取特定诊断的完整数据集
    """
    client = get_client()
    output_dir = output_base_dir / diagnosis
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"提取诊断: {diagnosis}")
    print(f"输出目录: {output_dir}")
    print(f"{'='*60}")

    # 1. 获取 hadm_ids
    hadm_ids = get_hadm_ids_for_diagnosis(client, diagnosis, max_patients)
    if not hadm_ids:
        print(f"错误: 没有找到 {diagnosis} 的患者")
        return

    # 2. 获取 subject_ids 和 stay_ids
    hadm_list = ",".join(str(h) for h in hadm_ids[:5000])  # 限制第一批

    # 获取 subject_ids
    subject_query = f"""
    SELECT DISTINCT subject_id
    FROM `{DATASET_HOSP}.admissions`
    WHERE hadm_id IN ({hadm_list})
    """
    subject_ids = [row.subject_id for row in client.query(subject_query).result()]

    # 获取 stay_ids (ED)
    stay_query = f"""
    SELECT DISTINCT stay_id
    FROM `{DATASET_ED}.edstays`
    WHERE hadm_id IN ({hadm_list})
    """
    stay_ids = [row.stay_id for row in client.query(stay_query).result()]

    print(f"  Subject IDs: {len(subject_ids)}")
    print(f"  Stay IDs (ED): {len(stay_ids)}")

    # 3. 提取 Hosp 表
    print("\n提取 Hosp 数据...")
    hosp_tables = [
        "admissions",
        "patients",
        "transfers",
        "diagnoses_icd",
        "d_icd_diagnoses",
        "procedures_icd",
        "d_icd_procedures",
        "prescriptions",
        "labevents",
        "d_labitems",
        "microbiologyevents",
    ]

    for table in hosp_tables:
        try:
            if table in ["patients", "d_icd_diagnoses", "d_icd_procedures", "d_labitems"]:
                # 这些表不需要 hadm_id 过滤
                query = f"SELECT * FROM `{DATASET_HOSP}.{table}`"
                result = client.query(query).result()
                df = result.to_dataframe()
                df.to_parquet(output_dir / f"{table}.parquet", index=False)
                print(f"  {table}: {len(df)} 行 (完整表)")
            else:
                extract_table_for_hadm_ids(client, table, hadm_ids, output_dir, DATASET_HOSP)
        except Exception as e:
            print(f"  错误 {table}: {e}")

    # 4. 提取 Note 表
    print("\n提取 Note 数据...")
    note_tables = ["discharge", "radiology", "radiology_detail"]

    for table in note_tables:
        try:
            extract_table_for_hadm_ids(client, table, hadm_ids, output_dir, DATASET_NOTE)
        except Exception as e:
            print(f"  错误 {table}: {e}")

    # 5. 提取 ED 表
    print("\n提取 ED 数据...")
    ed_tables = ["edstays", "diagnosis", "medrecon", "pyxis", "triage", "vitalsign"]

    for table in ed_tables:
        try:
            extract_ed_table_for_stay_ids(client, table, stay_ids, output_dir)
        except Exception as e:
            print(f"  错误 ED.{table}: {e}")

    print(f"\n完成! 数据保存在: {output_dir}")
    return output_dir


def main():
    parser = argparse.ArgumentParser(description="从 BigQuery 导出 MIMIC-IV 数据")
    parser.add_argument(
        "--diagnosis",
        type=str,
        choices=DIAGNOSES,
        help="要提取的诊断",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="提取所有诊断",
    )
    parser.add_argument(
        "--max-patients",
        type=int,
        default=None,
        help="每个诊断最大患者数 (用于测试)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./mimic_extract",
        help="输出目录",
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    if args.all:
        for diagnosis in DIAGNOSES:
            try:
                extract_diagnosis_dataset(diagnosis, output_dir, args.max_patients)
            except Exception as e:
                print(f"错误: {diagnosis}: {e}")
    elif args.diagnosis:
        extract_diagnosis_dataset(args.diagnosis, output_dir, args.max_patients)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
