import os
from pathlib import Path

from dotenv import load_dotenv

_MIRA_DSPY_DIR = Path(__file__).resolve().parent.parent
_SRC_DIR = _MIRA_DSPY_DIR.parent / "src"

# `src/.env` is the single source of truth for API credentials in this repo;
# load it here too since mira_dspy is a separate installable package.
load_dotenv(_SRC_DIR / ".env", override=False)

# Both task LM and optimizer/teacher LM stay on the same model the rest of the
# repo already uses (see src/config.py) -- this is an independent experiment
# measuring DSPy's effect on glm-5.2, not a reproduction of the paper's
# original gpt-4o/o1 numbers.
TASK_LM_MODEL: str = "glm-5.2"
OPTIMIZER_LM_MODEL: str = "glm-5.2"

OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL: str | None = os.getenv("OPENAI_BASE_URL")

COMPILED_DIR = _MIRA_DSPY_DIR / "compiled"


def _make_lm(model: str) -> "dspy.LM":
    import dspy

    return dspy.LM(
        f"openai/{model}",
        api_key=OPENAI_API_KEY,
        api_base=OPENAI_BASE_URL,
    )


def get_task_lm() -> "dspy.LM":
    """LM used by MiraDoctorProgram at inference/rollout time."""
    return _make_lm(TASK_LM_MODEL)


def get_optimizer_lm() -> "dspy.LM":
    """LM used by GEPA as the reflection/teacher model proposing new instructions."""
    return _make_lm(OPTIMIZER_LM_MODEL)


def configure_dspy() -> None:
    """Set the default DSPy LM to the task model. Call once per process."""
    import dspy

    dspy.configure(lm=get_task_lm())
