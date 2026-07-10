"""Construct DSPy Examples from PatientGroundTruth for GEPA compilation.

Each Example represents a single admission's ground-truth data, ready for
MiraDoctorProgram's forward() inputs + expected outputs. The patient interview
(conv.py's ping-pong) is frozen; trainset construction starts from the
post-interview state (history_so_far) that MiraDoctorProgram.forward() expects.

See design.md section 4 and spec.md's "trainset" requirement.
"""

from typing import List

import dspy

from evaluations.preprocess import PatientGroundTruth


class MiraDoctorExample(dspy.Example):
    """A single admission's Example for MiraDoctorProgram compilation.

    Inputs (what the program receives):
    - chief_complaint: str -- patient's presenting symptom
    - history_so_far: str -- clinical history from the frozen interview + admission medication
    - tool_catalog_desc: str -- description of available tools (same for all examples)

    Expected outputs (what the metric compares against):
    - patient_gt: PatientGroundTruth -- full ground truth for order/diagnosis evaluation
    - diagnosis_category: str -- coarse label for evalaute_diagnosis()'s matching criterion
    """

    def __init__(
        self,
        chief_complaint: str,
        history_so_far: str,
        tool_catalog_desc: str,
        patient_gt: PatientGroundTruth,
        diagnosis_category: str,
    ):
        super().__init__(
            chief_complaint=chief_complaint,
            history_so_far=history_so_far,
            tool_catalog_desc=tool_catalog_desc,
            patient_gt=patient_gt,
            diagnosis_category=diagnosis_category,
        )
        # Mark inputs for DSPy -- outputs are implicit (not passed to forward())
        self.with_inputs("chief_complaint", "history_so_far", "tool_catalog_desc")


def _extract_chief_complaint(patient_gt: PatientGroundTruth) -> str:
    """Extract chief complaint from the patient's triage data."""
    # PatientGroundTruth.patient_data.triage holds the admission triage row
    cc_df = patient_gt.patient_data.triage.chiefcomplaint
    if cc_df is None or len(cc_df.values) == 0:
        return "Unknown chief complaint"
    cc = cc_df.values[0]
    return str(cc).strip() if cc else "Unknown chief complaint"


def _build_history_so_far(patient_gt: PatientGroundTruth) -> str:
    """Build the post-interview history string for MiraDoctorProgram.

    This mirrors the anamnesis_summary construction in src/runs/run.py's
    prepare_patient(), but without the interview transcript (conv.py's ping-pong
    is frozen and produces the actual history_so_far at runtime). For trainset
    construction, we use the extracted_history + admission_medication as a
    proxy for what the frozen interview would yield.

    NOTE: This is a static proxy; real compilation runs the full interview first
    and then MiraDoctorProgram on the actual transcript. For GEPA's per-predictor
    feedback loop, the interview transcript from each rollout is what matters.
    """
    extracted_history = patient_gt.patient_data.history_pe_admedication_diagnosis[
        "extracted_history"
    ].values[0]
    extracted_history = str(extracted_history).strip()

    admission_med = patient_gt.admission_medication
    if admission_med and admission_med.strip():
        medication_str = f"\n\nMedication:\n{admission_med}"
    else:
        medication_str = "\n\nMedication: No current medication."

    return extracted_history + medication_str


def build_trainset(
    patient_gts: List[PatientGroundTruth],
    tool_catalog_desc: str,
    diagnosis_category: str,
) -> List[MiraDoctorExample]:
    """Build a trainset from PatientGroundTruth instances.

    Args:
        patient_gts: List of PatientGroundTruth instances (one per admission)
        tool_catalog_desc: Tool catalog description string (same for all examples)
        diagnosis_category: Coarse diagnosis label for evalaute_diagnosis() matching

    Returns:
        List of MiraDoctorExample ready for dspy.GEPA.compile()
    """
    examples = []
    for patient_gt in patient_gts:
        chief_complaint = _extract_chief_complaint(patient_gt)
        history_so_far = _build_history_so_far(patient_gt)
        example = MiraDoctorExample(
            chief_complaint=chief_complaint,
            history_so_far=history_so_far,
            tool_catalog_desc=tool_catalog_desc,
            patient_gt=patient_gt,
            diagnosis_category=diagnosis_category,
        )
        examples.append(example)
    return examples