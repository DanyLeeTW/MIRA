# mira-dspy

DSPy-structured re-implementation of the MIRA workup+diagnosis agent, parallel to `src/` (the paper's reference implementation, which this package does not modify).

Scope: only the "order tests + diagnose" stage (`generate_routine()` + `MedAssistant.chat()` in `src/`) is rewritten with DSPy `Signature`/`Module`/`ReAct`. The patient history-taking dialogue (`src/conv.py`, `PatientAssistant`) is out of scope; `history_so_far` is sourced from the MIMIC admission's own discharge-letter-derived narrative (`PatientGroundTruth`/`anamnesis_summary`), not a live simulated interview.

See `openspec/changes/add-dspy-structured-agent/` (or its archived spec once merged) for the full proposal, design rationale, and requirements.

## Setup

`mira_dspy` uses its **own virtual environment** (`mira_dspy/.venv`), separate from `src/.venv`. This isn't incidental: `dspy-ai` (any version from 2.4.0 through the current 3.x) has a hard dependency conflict with `hospitalagent-src`'s exact pins (`openai==1.44.1`, `httpx==0.27.2`, `jinja2==3.1.4`) -- older dspy-ai needs `pydantic==2.5.0` (below `hospitalagent-src`'s `>=2.11.4` floor), newer dspy-ai's `litellm` dependency needs `openai>=1.66.1`/`httpx>=0.28.0`/`jinja2==3.1.6`. There's no version where both sides resolve together. `src/pyproject.toml` is not touched; `overrides.txt` only relaxes those three bounds for *this* venv's resolution of a second, still-editable install of the same `src/` files.

```bash
cd mira_dspy
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -e ../src --override overrides.txt
uv pip install --python .venv/bin/python -e . --override overrides.txt
```

`src/.venv` and every existing `src/` workflow are unaffected.

## Known limitations

- **`procedure` category exact-match**: order-score matching for the `procedure` category reuses `src/evaluations/objectives.py`'s exact-match set-overlap logic. `ProcedureRequestFHIR.procedure` is free text, so synonymous phrasings (e.g. "Diagnostic laparoscopy" vs "Laparoscopic exploration") are scored as non-matching, which can understate that category's true F1. A fix exists (reuse `ProcedureSearch`'s `jinaai/jina-embeddings-v3` + Qdrant similarity threshold match) but is intentionally deferred; revisit if the `procedure` category's scores look untrustworthy in practice. This limitation is documented in `mira_dspy/metrics.py:match_category()` docstring and proposal.md's Known Limitations section.
- **`evalaute_diagnosis` model pin**: the diagnosis-match LLM judge (imported unmodified from `src/evaluations/objectives.py`) is hardcoded to call `model="gpt-4o"` on whatever `OpenAI()` client it's given, independent of this package's `glm-5.2` task/optimizer LM configuration. This is existing `src/` behavior, left as-is.
