# Medication Code Mapper (`codes/medication_codes.py`) 💊 🏷️

This module enriches medications from the **MIMIC-IV** `prescriptions.csv` and `medrecon.csv` extracts with widely-used, machine-readable identifiers and stores the result in a single CSV file.

## Structure 🗃️

```python
.
├── README.md
├── __init__.py
├── mappings
│   └── medication_ndc_rxnorm_snomedct_atc.csv
└── medication_codes.py
```

The bundled CSV is a pre-generated mapping so you can start using it immediately.  
Run the script when you need to refresh the data (e.g. new MIMIC dump, additional formularies).

---

## What it does 🔄 ⏳

| Step                   | Details                                                                                                                                                         |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1 Load source data** | Reads the `prescriptions.csv` (hospital stays) and `medrecon.csv` (ED visits) extracts.                                                                         |
| **2 De-duplicate**     | Builds the unique set of `(drug name + NDC)` pairs.                                                                                                             |
| **3 Resolve codes**    | For every row (in parallel, with retries & caching): <br>• **RxNav** → RxNorm ID (from NDC or drug name) <br>• **UMLS Crosswalk** → SNOMED CT & ATC from RxNorm |
| **4 Stream to CSV**    | Writes results in batches to `codes/mappings/medication_ndc_rxnorm_snomedct_atc.csv` so memory usage stays low.                                                 |

---

## Prerequisites ⚙️

| Requirement           | Why / how                                                                                                                                                    |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **UMLS API key**      | Needed for the cross-walk endpoints. Get one at <https://uts.nlm.nih.gov/>.                                                                                  |
| MIMIC-IV source files | `prescriptions.csv` and `medrecon.csv` must be available via `paths.py` (`MIRA_MIMIC_RAW_BASE_DIR` or explicit `MIRA_MIMIC_HOSP_DIR` + `MIRA_MIMIC_ED_DIR`). |
| Internet access       | RxNav & UMLS calls are made live when regenerating the file. Runtime fallback can also call openFDA.                                                         |
| Python deps           | Listed in the project’s dependency file (`requests`, `pandas`, `tenacity`, `tqdm`, etc.).                                                                    |

Use the project environment setup from `HospitalAgent/README.md` (venv at `src/.venv`).

## Create or extend **`HospitalAgent/src/.env`**:

```env
# Required
UMLS_API_KEY=YOUR_UTS_API_KEY 🔑

# Required unless you set explicit `MIRA_MIMIC_HOSP_DIR` + `MIRA_MIMIC_ED_DIR`
MIRA_MIMIC_RAW_BASE_DIR=/path/to/MIMIC_Dataset
# or set these explicitly:
MIRA_MIMIC_HOSP_DIR=/path/to/physionet.org/files/mimiciv/2.2/hosp
MIRA_MIMIC_ED_DIR=/path/to/physionet.org/files/mimic-iv-ed/2.2/ed
```

## Run the code (`__main__`) ▶️

```bash
cd /path/to/HospitalAgent
uv run --project src python -m codes.medication_codes
```

Check the progress bar in the terminal after a few seconds.
This overwrites `codes/mappings/medication_ndc_rxnorm_snomedct_atc.csv`.
Depending on your rate limits / API-keys, settings this might take a couple of hours (~ 5 hrs during tests) - feel free to modify the code and speed it up (shared sessions, increase max workers, etc ...)

## Runtime usage in tools 🧰

`get_drug_codes_from_name(drug_name)` is used by `tools.py` for medication coding at inference time:

- First tries the local CSV mapping.
- If missing, falls back to live API resolution (RxNav + UMLS, with openFDA used to infer NDC candidates).
