import contextvars
from typing import List, Optional

import dspy
from assistants import PatientContext
from MimicEnums import (
    BloodValue,
    MicroBiologyValue,
    PeriodUnit,
    RadiologyModalityValue,
    RadiologyRegionValue,
    RouteUnit,
    UrineValue,
)
from pydantic import BaseModel, Field
from tool_execs import (
    get_blood_value_results,
    get_medication_results,
    get_microbiology_results,
    get_physical_exam_results,
    get_procedure_request_results,
    get_procedure_search_results,
    get_radiology_results,
    get_urine_value_results,
)
from tools import (
    MedicationRequestList,
    MicrobiologyRequestList,
    PhysicalExamination,
    ProcedureRequestFHIR,
    ProcedureSearch,
    RadiologyRequestFHIR,
    UrineRequestList,
)
from tools import LabRequestList as _LabRequestListModel

# `dspy.ReAct`'s tool list is fixed at construction time and must stay the same
# object across an entire GEPA compile run (GEPA optimizes the predictors of one
# persistent program). But each rollout needs its own FHIR/session context
# (patient_id, session, patient_data, ...). Rather than baking one patient's
# context into the tools (which would make them one-shot), each rollout binds
# its PatientContext into this contextvar for its duration; the tool closures
# below read it at call time. This keeps the per-admission plumbing invisible
# to the LLM-facing tool schema (no "session_id" argument for the model to fill in).
_active_patient_context: contextvars.ContextVar[PatientContext] = contextvars.ContextVar(
    "mira_dspy_active_patient_context"
)


class patient_context_scope:
    """Bind `patient_context` for the duration of one rollout's tool calls."""

    def __init__(self, patient_context: PatientContext):
        self._patient_context = patient_context
        self._token = None

    def __enter__(self) -> "patient_context_scope":
        self._token = _active_patient_context.set(self._patient_context)
        return self

    def __exit__(self, *exc_info) -> None:
        _active_patient_context.reset(self._token)


def _current_context() -> PatientContext:
    try:
        return _active_patient_context.get()
    except LookupError as e:
        raise RuntimeError(
            "No PatientContext bound for this tool call. Invoke MiraDoctorProgram "
            "only inside `with patient_context_scope(ctx): ...`."
        ) from e


class MedicationOrder(BaseModel):
    """A single medication order, mirroring MedicationRequestFHIR's LLM-facing fields."""

    drug_name: str = Field(description="The name of the drug", examples=["Amoxicillin"])
    dosage_text: str = Field(
        description="The dosage, strength or concentration a single medication as text",
        examples=["10mEq ER Tablet once a day"],
    )
    dosage_value: float = Field(
        description="The prescribed dosage for the patient in one intake", examples=[500]
    )
    dosage_unit: str = Field(description="The unit of the dosage value", examples=["mg"])
    period: int = Field(description="The period of the dosage", examples=[1])
    period_unit: PeriodUnit = Field(description="The unit of the period", examples=["d"])
    frequency: int = Field(
        description="The frequency of the dosage per period", examples=[3]
    )
    route: RouteUnit = Field(description="The route of the dosage", examples=["Oral"])


async def _lab_request(lab_values: List[BloodValue]) -> str:
    ctx = _current_context()
    return await get_blood_value_results(
        lab_values=[{"lab_value": v} for v in lab_values], **ctx.to_dict()
    )


async def _urine_request(urine_values: List[UrineValue]) -> str:
    ctx = _current_context()
    return await get_urine_value_results(
        urine_values=[{"urine_value": v} for v in urine_values], **ctx.to_dict()
    )


async def _microbiology_request(microbiology_tests: List[MicroBiologyValue]) -> str:
    ctx = _current_context()
    return await get_microbiology_results(
        microbiology_tests=[{"microbiology_value": v} for v in microbiology_tests],
        **ctx.to_dict(),
    )


async def _radiology_request(
    modality: RadiologyModalityValue,
    region: RadiologyRegionValue,
    info: Optional[str] = None,
) -> str:
    ctx = _current_context()
    return await get_radiology_results(
        modality=modality, region=region, info=info, **ctx.to_dict()
    )


async def _procedure_search(procedure: str) -> str:
    ctx = _current_context()
    return await get_procedure_search_results(procedure=procedure, **ctx.to_dict())


async def _procedure_request(procedure: str) -> str:
    ctx = _current_context()
    return await get_procedure_request_results(procedure=procedure, **ctx.to_dict())


async def _medication_request(medications: List[MedicationOrder]) -> str:
    ctx = _current_context()
    return await get_medication_results(
        medications=[m.model_dump() for m in medications], **ctx.to_dict()
    )


async def _physical_examination() -> str:
    ctx = _current_context()
    return await get_physical_exam_results(**ctx.to_dict())


def build_tools() -> List[dspy.Tool]:
    """Build the fixed tool list for MiraDoctorProgram.self.execute (dspy.ReAct).

    These are stateless closures over `_current_context()`, not over a specific
    patient -- build this once and reuse the same list/program across an entire
    compile run; bind each rollout's patient via `patient_context_scope`.

    Tool names intentionally match the FHIR pydantic model class names in
    `tools.py` (`LabRequestList`, `RadiologyRequestFHIR`, ...) so that
    `src.evaluations.preprocess.match_ground_truth_and_assistant`'s
    `_GROUND_TRUTH_TO_ASSISTANT_ALIGNS` mapping keeps working unmodified.
    """

    return [
        dspy.Tool(_lab_request, name="LabRequestList", desc=_LabRequestListModel.__doc__),
        dspy.Tool(_urine_request, name="UrineRequestList", desc=UrineRequestList.__doc__),
        dspy.Tool(
            _microbiology_request,
            name="MicrobiologyRequestList",
            desc=MicrobiologyRequestList.__doc__,
        ),
        dspy.Tool(
            _radiology_request, name="RadiologyRequestFHIR", desc=RadiologyRequestFHIR.__doc__
        ),
        dspy.Tool(_procedure_search, name="ProcedureSearch", desc=ProcedureSearch.__doc__),
        dspy.Tool(
            _procedure_request, name="ProcedureRequestFHIR", desc=ProcedureRequestFHIR.__doc__
        ),
        dspy.Tool(
            _medication_request, name="MedicationRequestList", desc=MedicationRequestList.__doc__
        ),
        dspy.Tool(
            _physical_examination, name="PhysicalExamination", desc=PhysicalExamination.__doc__
        ),
    ]


def tool_catalog_description(tools: List[dspy.Tool]) -> str:
    """Render a tool catalog description for PlanDifferentialWorkup's input.

    dspy.ReAct already knows its own tools' names/args/descriptions natively;
    this is only for the planning-stage predictor, mirroring how the original
    `generate_routine()` received a stringified tool list as prompt context.
    """

    return "\n".join(str(tool) for tool in tools)
