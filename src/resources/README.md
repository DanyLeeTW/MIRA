# Resources

Stable, versioned input assets used by the core code.

Canonical working directory for referenced paths: `HospitalAgent/` (repository root).

- `pancreatic_cancer_info.json`
- `BIAS_DATASET_TO_HADM_IDS.json`
- `medication_routes.csv`

Notes:

- `pancreatic_cancer_info.json` is expected to be empty in the publication package and can be recreated by running `src/notebooks/extract_pancreatic_cancer_info.ipynb` (it writes directly to `src/resources/pancreatic_cancer_info.json`).

These are treated as source resources (not runtime outputs).
