# **MIRA** - _Towards Autonomous Medical Artificial Intelligence Agents_

Repository for reproducing the experiments for the MIRA manuscript.

## Scope

- `src/` contains the core implementation, run entrypoints, evaluations, and structured data/output folders.

## Environment Setup

From the repository root (for example `.../MIRA/`, not the parent directory):

```bash
git clone https://github.com/Dyke-F/MIRA.git
cd MIRA
```

Run setup only from `MIRA/`:

```bash
python3.12 -m venv src/.venv
source src/.venv/bin/activate
python -m pip install -U pip uv
uv pip install -e ./src
```

Create `src/.env` (for example by copying `src/.env.example`) and filling in all environment variables.

## Sub-README Navigation (Read in this order)

Use this sequence before running any step scripts/notebooks:

1. `src/README.md`
   - Confirms package installation context (`uv pip install -e ./src`).
2. `src/dataset/README.md`
   - Required before `src/dataset/make_dataset.py` or `src/dataset/make_admission_datasets.py`.
   - Explains required MIMIC path environment variables.
3. `src/notebooks/README.md`
   - Required before notebook-based preprocessing (`extract_pancreatic_cancer_info.ipynb`, `build_procedure_db.ipynb`).
4. `src/backend/README.md`
   - Required before starting local HAPI FHIR and running code that posts FHIR resources.
5. `src/raw/README.md` and `src/resources/README.md`
   - Explain what data folders/files are expected to be empty vs generated.
6. `src/runs/README.md`
   - Required before simulation notebooks in `src/runs/`.
7. `src/evaluations/README.md`
   - Required before evaluation notebooks/scripts in `src/evaluations/`.
8. Optional maintenance only:
   - `src/MimicEnums/README.md`
   - `src/codes/README.md`

## Canonical `src/` Layout

```text
src/
├── runs/              # run entrypoints (python + notebooks)
├── evaluations/       # evaluation notebooks/scripts
├── dataset/           # dataset preparation logic
├── backend/           # FHIR backend integration
├── MimicEnums/        # enums used by tools/evaluation typing
├── tools.py ...       # core agent/tool code
├── paths.py           # central canonical paths
├── resources/         # stable input assets used by runs/tools
├── notebooks/         # non-entrypoint utility notebooks
└── raw/               # generated/runtime data (evaluable outputs, qdrant, archives)
```

## Reproduction Flow

From the repository root (`MIRA/`) unless a linked README says otherwise.
Before each step, read the linked sub-README first.

Canonical package order for end-to-end reproduction:
`src/dataset` -> `src/notebooks` (pancreatic context) -> `src/backend` + Qdrant -> `src/notebooks` (procedure DB) -> `src/runs` -> `src/evaluations`.
`src/MimicEnums` and `src/codes` regeneration are optional maintenance steps and are not required for standard runs.

1. Build diagnosis datasets (read first: `src/dataset/README.md`)

```bash
uv run --project src python src/dataset/make_dataset.py
```

This populates `src/raw/derived/diagnosis_datasets/` (or `MIRA_DIAGNOSIS_DATASETS_DIR` if overridden).

Optional (only for optional-admission experiments):

```bash
uv run --project src python src/dataset/make_admission_datasets.py
```

This requires edited Excel inputs under `src/raw/inputs/optional_admission/pneumonia/**/*.xlsx` and `src/raw/inputs/optional_admission/pe/**/*.xlsx`.

Useful env options for script runs:

```bash
# only run selected diagnoses (comma-separated)
export MIRA_DATASET_DIAGNOSES="appendicitis,pancreatitis"

# optional cap on number of diagnoses
export MIRA_MAX_DIAGNOSES=1

# optional per-diagnosis admission subset (fast smoke tests)
export MIRA_MAX_HADM_IDS_PER_DIAGNOSIS=20

# overwrite handling for existing dataset folders:
# ask (default) | yes | no
export MIRA_OVERWRITE_DATASETS=ask
```

Important:

- If `MIRA_OVERWRITE_DATASETS=ask` and a diagnosis dataset already exists, the script waits for terminal input:
  `Dataset exists at ... Overwrite? (y/n):`
- You must type `y` and press Enter to continue that diagnosis. If you type `n`, that diagnosis is skipped.
- For unattended full runs, use `export MIRA_OVERWRITE_DATASETS=yes`.

For full extraction across all diagnoses, clear subset envs:

```bash
unset MIRA_DATASET_DIAGNOSES
unset MIRA_MAX_HADM_IDS_PER_DIAGNOSIS
unset MIRA_MAX_DIAGNOSES
uv run --project src python src/dataset/make_dataset.py
```

2. Prepare pancreatic cancer context resource (required when running pancreatic cancer cases; read first: `src/notebooks/README.md`)

Requires `OPENAI_API_KEY` and diagnosis datasets from Step 1.

```bash
# open and run all cells
src/notebooks/extract_pancreatic_cancer_info.ipynb
```

This notebook writes directly to `src/resources/pancreatic_cancer_info.json`.

3. (Optional) Regenerate MIMIC enums/code maps (read first: `src/MimicEnums/README.md` and `src/codes/README.md`)

Not required for standard runs. The generated enums are already versioned under `src/MimicEnums/`.
Use `src/MimicEnums/make_enums_and_code_maps.py` only when intentionally refreshing enum/code-map artifacts.
Medication code-map regeneration is separate and optional; see `src/codes/README.md`.

4. Start local FHIR backend (read first: `src/backend/README.md`)

```bash
docker compose -f src/backend/hapi-fhir-server/docker-compose.yml up -d
```

5. Start Qdrant (local; read first: `src/notebooks/README.md` and `src/raw/README.md`)

```bash
docker run -p 6333:6333 -p 6334:6334 \
  -v "$(pwd)/src/raw/runtime/qdrant/main:/qdrant/storage:z" \
  -e QDRANT__TELEMETRY_DISABLED=true \
  qdrant/qdrant
```

6. Build procedure vector DB (read first: `src/notebooks/README.md`)

Run this after Step 5 so Qdrant is available.

```bash
# open and run all cells
src/notebooks/build_procedure_db.ipynb
```

7. Run simulations (read first: `src/runs/README.md`)

- Baseline: `src/runs/run_simulation.ipynb` (uses `src/runs/run.py`)
- Bias: `src/runs/run_simulation_bias.ipynb` (uses `src/runs/run.py` + `src/runs/run_with_sex_bias.py`)
- Optional admission experiments: `src/runs/run_simulation_optional_admission.ipynb` (uses `src/runs/run_optional_admission.py`)
- Optional leakage/adversarial analysis: `src/runs/run_leakage_and_adversarial.ipynb` (uses existing simulation outputs)
- Before running each notebook, review its first parameter cells (`DATASET_NAMES`, sample-size settings, selected `hadm_id`s).
  - Experimetns can be ressource-intensive and take long, so some notebooks contain `break` or `run_cell=False` commands that need to be removed/set to True before `full runs` can be done.
  - Open run notebooks from `src/runs/` so local imports resolve as written.

Run outputs are written under `src/raw/evaluable_outputs/`.

8. Run evaluations (read first: `src/evaluations/README.md`)

Follow `src/evaluations/README.md`:

- `evaluations_MIRA.ipynb` for evaluating the MIRA agent.
- `evaluations_HUMANS.ipynb` only if human baseline outputs are available.

## Detailed READMEs

- `src/backend/README.md`
- `src/codes/README.md`
- `src/dataset/README.md`
- `src/MimicEnums/README.md`
- `src/notebooks/README.md`
- `src/raw/README.md`
- `src/resources/README.md`
- `src/runs/README.md`
- `src/evaluations/README.md`
