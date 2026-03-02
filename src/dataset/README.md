# Dataset Preparation

This folder contains code to build diagnosis-specific datasets from MIMIC-IV CSV sources and store them under `src/raw/derived/diagnosis_datasets` (or `MIRA_DIAGNOSIS_DATASETS_DIR` when set).

Canonical working directory for commands in this README: `HospitalAgent/` (repository root), using `src/.venv`.

Before running, configure MIMIC raw paths via `src/.env` (or exported environment variables):

- `MIRA_MIMIC_RAW_BASE_DIR` (base folder containing `physionet.org/files/...`)
- Optional explicit overrides: `MIRA_MIMIC_HOSP_DIR`, `MIRA_MIMIC_NOTE_DIR`, `MIRA_MIMIC_ED_DIR`
- Optional output override: `MIRA_DIAGNOSIS_DATASETS_DIR`

## Current Structure

```text
dataset/
├── README.md
├── __init__.py
├── config.py
├── consort_tracker.py
├── data.py
├── discharge.py
├── extracters.py
├── formats.py
├── labs.py
├── medication.py
├── microbiology.py
├── mimic_dataset.py
├── mimic_dataset_admission_experiments.py
├── procedures.py
├── radiology.py
├── utils.py
├── validators.py
├── make_dataset.py
├── make_admission_datasets.py
└── labitems_map/
    └── d_labitems_to_loinc.csv (1)
```

## Steps

1. Set `MIRA_MIMIC_RAW_BASE_DIR` (or explicit `MIRA_MIMIC_*_DIR` overrides).
2. Optional `make_dataset.py` runtime controls:

```bash
# only run selected diagnoses (comma-separated names from dataset/config.py)
export MIRA_DATASET_DIAGNOSES="appendicitis,pancreatitis"

# optional cap on diagnosis count
export MIRA_MAX_DIAGNOSES=1

# optional cap on admissions per diagnosis
export MIRA_MAX_HADM_IDS_PER_DIAGNOSIS=20

# overwrite behavior for existing dataset folders: ask (default) | yes | no
export MIRA_OVERWRITE_DATASETS=ask
```

3. From `HospitalAgent/`, run:

```bash
uv run --project src python src/dataset/make_dataset.py
```

4. Optional admission-focused extraction:

```bash
uv run --project src python src/dataset/make_admission_datasets.py
```

`make_admission_datasets.py` expects edited Excel inputs in both folders:

- `src/raw/inputs/optional_admission/pneumonia/**/*.xlsx`
- `src/raw/inputs/optional_admission/pe/**/*.xlsx`

If either folder is missing, the script raises `FileNotFoundError`.

Generated outputs are written into `src/raw/derived/diagnosis_datasets` (or `MIRA_DIAGNOSIS_DATASETS_DIR` if set).

(1) from https://github.com/MIT-LCP/mimic-code/blob/e39825259beaa9d6bc9b99160049a5d251852aae/mimic-iv/mapping/d_labitems_to_loinc.csv
