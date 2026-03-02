from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

SRC_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SRC_DIR.parent

# Ensure `src/.env` values are available even when paths are imported
# before other modules call `load_dotenv()`.
load_dotenv(SRC_DIR / ".env", override=False)

RAW_DIR = SRC_DIR / "raw"
RUNS_DIR = SRC_DIR / "runs"
EVALUATIONS_DIR = SRC_DIR / "evaluations"
RESOURCES_DIR = SRC_DIR / "resources"
NOTEBOOKS_DIR = SRC_DIR / "notebooks"


def _env_path(env_var: str, default: Path) -> Path:
    value = os.getenv(env_var)
    if value:
        return Path(value).expanduser()
    return default


# Canonical output/input locations
EVALUABLE_OUTPUTS_BASELINE_DIR = (
    RAW_DIR / "evaluable_outputs" / "baseline" / "EVALUABLE_OUTPUTS"
)
EVALUABLE_OUTPUTS_BIAS_DIR = RAW_DIR / "evaluable_outputs" / "bias"
EVALUABLE_OUTPUTS_OPTIONAL_ADMISSION_DIR = (
    RAW_DIR
    / "evaluable_outputs"
    / "optional_admission"
    / "EVALUABLE_OUTPUTS_OPTIONAL_ADMISSION"
)
EVALUABLE_OUTPUTS_HUMAN_BC_DIR = (
    RAW_DIR / "evaluable_outputs" / "human_bc" / "EVALUABLE_OUTPUTS_HU_BC"
)

RESULTS_BACKUP_DIR = RAW_DIR / "archive" / "results_backup"
QDRANT_STORAGE_DIR = _env_path(
    "MIRA_QDRANT_STORAGE_DIR", RAW_DIR / "runtime" / "qdrant" / "main"
)

# Dataset directories
DIAGNOSIS_DATASETS_DIR = _env_path(
    "MIRA_DIAGNOSIS_DATASETS_DIR", RAW_DIR / "derived" / "diagnosis_datasets"
)

PREPROCESSED_DATA_DIR = _env_path(
    "MIRA_PREPROCESSED_DATA_DIR", RAW_DIR / "inputs" / "preprocessed_data"
)

# Raw MIMIC-IV source locations
MIMIC_RAW_BASE_DIR = _env_path("MIRA_MIMIC_RAW_BASE_DIR", PROJECT_DIR / "MIMIC_Dataset")
MIMIC_HOSP_DIR = _env_path(
    "MIRA_MIMIC_HOSP_DIR",
    MIMIC_RAW_BASE_DIR / "physionet.org" / "files" / "mimiciv" / "2.2" / "hosp",
)
MIMIC_NOTE_DIR = _env_path(
    "MIRA_MIMIC_NOTE_DIR",
    MIMIC_RAW_BASE_DIR / "physionet.org" / "files" / "mimic-iv-note" / "2.2" / "note",
)
MIMIC_ED_DIR = _env_path(
    "MIRA_MIMIC_ED_DIR",
    MIMIC_RAW_BASE_DIR / "physionet.org" / "files" / "mimic-iv-ed" / "2.2" / "ed",
)

# Static resources
PANCREATIC_CANCER_INFO_PATH = RESOURCES_DIR / "pancreatic_cancer_info.json"
BIAS_DATASET_TO_HADM_IDS_PATH = RESOURCES_DIR / "BIAS_DATASET_TO_HADM_IDS.json"
MEDICATION_ROUTES_PATH = RESOURCES_DIR / "medication_routes.csv"
D_LABITEMS_TO_LOINC_PATH = _env_path(
    "MIRA_D_LABITEMS_TO_LOINC_PATH",
    SRC_DIR / "dataset" / "labitems_map" / "d_labitems_to_loinc.csv",
)

# Eval GUI outputs
EVAL_GUI_REPORTS_DIR = RAW_DIR / "apps" / "eval_gui" / "reports"
EVAL_GUI_REPORTS_HU_DIR = RAW_DIR / "apps" / "eval_gui" / "reports_hu"
