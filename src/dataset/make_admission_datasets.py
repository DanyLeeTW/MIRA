"""
Build optional-admission experiment datasets from edited Excel case files.

This recreates:
- `pneumonia_admission_experiments`
- `pe_admission_experiments`

Input source:
- `src/raw/inputs/optional_admission/pneumonia/**/*.xlsx`
- `src/raw/inputs/optional_admission/pe/**/*.xlsx`

Output target:
- Diagnosis datasets directory from `paths.DIAGNOSIS_DATASETS_DIR`
  (default: `src/raw/derived/diagnosis_datasets`).

Usage:
1. From the `HospitalAgent/` root, ensure dependencies are installed (`uv pip install -e ./src`).
2. Run:
   `src/.venv/bin/python -m dataset.make_admission_datasets`
3. If target dataset folders already exist, answer the overwrite prompt (`y/n`) in the terminal.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dataset.labs import match_lab_events_to_loinc
from dataset.mimic_dataset_admission_experiments import (
    MIMIC_Dataset_Admission_Experiments,
)
from MimicEnums import RadiologyModalityValue, RadiologyRegionValue

SRC_DIR = Path(__file__).resolve().parent.parent
OPTIONAL_ADMISSION_INPUT_DIR = SRC_DIR / "raw" / "inputs" / "optional_admission"


def check_radiology_modality_region(df: pd.DataFrame) -> None:
    region_list = df.region.unique().tolist()
    modality_list = df.modality.unique().tolist()

    for region in region_list:
        assert region in list(RadiologyRegionValue.__members__.keys())

    for modality in modality_list:
        assert modality in list(RadiologyModalityValue.__members__.keys())


def set_patient_key_to_hadm_id(
    case: dict[str, pd.DataFrame], case_id: str | int
) -> dict[str, pd.DataFrame]:
    for key, value in case.items():
        value["hadm_id"] = case_id
    return case


def add_extracted_rad_events(case: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    for key, df in case.items():
        if key == "radiology":
            df["extracted_rad_events"] = df["text"]
    return case


def read_cases_from_excel_dir(base_dir: Path) -> dict[str, dict[str, pd.DataFrame]]:
    if not base_dir.exists():
        raise FileNotFoundError(f"Input folder does not exist: {base_dir}")

    excel_files: dict[str, str] = {}
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".xlsx"):
                filename = file.split(".")[0]
                full_path = os.path.join(root, file)
                excel_files[filename] = full_path

    cases: dict[str, dict[str, pd.DataFrame]] = {}
    for filename, filepath in excel_files.items():
        cases[filename] = {}
        excel = pd.ExcelFile(filepath)
        for sheet_name in excel.sheet_names:
            df = pd.read_excel(filepath, sheet_name=sheet_name)
            df = df.dropna(axis=1, how="all")
            cases[filename][sheet_name] = df

    return cases


def preprocess_cases(cases: dict[str, dict[str, pd.DataFrame]]) -> None:
    for case_id, case_data in cases.items():
        case_data["lab_events"] = match_lab_events_to_loinc(case_data["lab_events"])
        case_data = set_patient_key_to_hadm_id(case_data, int(case_id))
        check_radiology_modality_region(case_data["radiology"])
        case_data = add_extracted_rad_events(case_data)
        case_data["history_pe_admedication_diagnosis"] = case_data[
            "history_pe_admedication_diagnos"
        ]
        del case_data["history_pe_admedication_diagnos"]
        del case_data["vitalsign"]


def concatenate_cases(
    cases: dict[str, dict[str, pd.DataFrame]], add_missing_columns: bool
) -> dict[str, pd.DataFrame]:
    concatenated_data: dict[str, pd.DataFrame] = {}
    for case_id, case_data in cases.items():
        for key, df in case_data.items():
            if df.empty:
                continue

            if key not in concatenated_data:
                concatenated_data[key] = df
            else:
                extra_cols = set(df.columns) - set(concatenated_data[key].columns)
                if extra_cols:
                    print(
                        f"Warning: Dropping extra columns in {key} for case {case_id}: {extra_cols}"
                    )
                    df = df.drop(columns=list(extra_cols))

                missing_cols = set(concatenated_data[key].columns) - set(df.columns)
                if missing_cols:
                    if add_missing_columns:
                        for col in missing_cols:
                            df[col] = pd.NA
                    else:
                        error_msg = (
                            f"Missing required columns in {key} for case {case_id}: "
                            f"{missing_cols}"
                        )
                        raise AssertionError(error_msg)

                df = df[concatenated_data[key].columns]
                concatenated_data[key] = pd.concat(
                    [concatenated_data[key], df], ignore_index=True
                )

    return concatenated_data


def make_dataset(
    *,
    cases: dict[str, dict[str, pd.DataFrame]],
    concatenated_data: dict[str, pd.DataFrame],
    diagnosis: str,
    dataset_name: str,
) -> None:
    ds = MIMIC_Dataset_Admission_Experiments(
        diagnosis=diagnosis,
        hadm_ids=list(cases.keys()),
        lab_events=concatenated_data["lab_events"],
        history_pe_admedication_diagnosis=concatenated_data[
            "history_pe_admedication_diagnosis"
        ],
        radiology=concatenated_data["radiology"],
        medication=concatenated_data["pyxis"],
        medrecon=concatenated_data["medrecon"],
        pyxis=concatenated_data["pyxis"],
        triage=concatenated_data["triage"],
        patients=concatenated_data["cohort"],
    )
    ds.save_dataset(dataset_name)


def make_pneumonia_admission_dataset() -> None:
    input_dir = OPTIONAL_ADMISSION_INPUT_DIR / "pneumonia"
    cases = read_cases_from_excel_dir(input_dir)
    preprocess_cases(cases)
    concatenated_data = concatenate_cases(cases, add_missing_columns=False)
    make_dataset(
        cases=cases,
        concatenated_data=concatenated_data,
        diagnosis="pneumonia_related",
        dataset_name="pneumonia_admission_experiments",
    )


def make_pe_admission_dataset() -> None:
    input_dir = OPTIONAL_ADMISSION_INPUT_DIR / "pe"
    cases = read_cases_from_excel_dir(input_dir)
    preprocess_cases(cases)
    concatenated_data = concatenate_cases(cases, add_missing_columns=True)
    make_dataset(
        cases=cases,
        concatenated_data=concatenated_data,
        diagnosis="pulmonary_embolism_related",
        dataset_name="pe_admission_experiments",
    )


def main() -> None:
    print("Building pneumonia admission-experiments dataset...")
    make_pneumonia_admission_dataset()
    print("Building pulmonary embolism admission-experiments dataset...")
    make_pe_admission_dataset()
    print("Done.")


if __name__ == "__main__":
    main()
