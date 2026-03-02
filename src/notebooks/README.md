# Notebooks

Utility notebooks that are not primary run entrypoints.

Main experiment entrypoint notebooks remain in `../runs/`.

Canonical working directory for all paths below: `HospitalAgent/` (repository root).

## Canonical order (aligned with `HospitalAgent/README.md`)

1. `extract_pancreatic_cancer_info.ipynb`
   - Run after diagnosis datasets are built (`uv run --project src python src/dataset/make_dataset.py`).
   - Required only when running pancreatic-cancer cases.
   - Writes directly to `../resources/pancreatic_cancer_info.json`.

2. `build_procedure_db.ipynb`
   - Run after local Qdrant is running.
   - Builds/refreshes the ICD procedure vector collection used by runtime retrieval.
   - Uses canonical local storage at `../raw/runtime/qdrant/main` when using the local-persistence cell.

## Prerequisites

- Project dependencies are installed from `HospitalAgent/` (see root README environment setup).
- `OPENAI_API_KEY` is set for `extract_pancreatic_cancer_info.ipynb`.
- MIMIC raw paths are configured in `src/.env` (or exported env vars) so `dataset.data.BASE_HOSP` resolves.
- For `build_procedure_db.ipynb`, start Qdrant from `HospitalAgent/`:

```bash
docker run -p 6333:6333 -p 6334:6334 \
  -v "$(pwd)/src/raw/runtime/qdrant/main:/qdrant/storage:z" \
  qdrant/qdrant
```

## In this folder

- `extract_pancreatic_cancer_info.ipynb`: extracts pancreatic-cancer context and writes directly to `../resources/pancreatic_cancer_info.json`.
- `build_procedure_db.ipynb`: builds/refreshes the local Qdrant ICD procedure vector collection used by runtime retrieval.
