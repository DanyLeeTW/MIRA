from typing import Any, Dict, List, Tuple

import dspy
from assistants import _create_openai_client
from evaluations.objectives import (
    evalaute_diagnosis,
    evaluate_blood_requests,
    evaluate_microbiology_requests,
    evaluate_procedure_requests,
    evaluate_radiology_requests,
    evaluate_urine_requests,
)
from evaluations.preprocess import PatientGroundTruth

ORDER_CATEGORIES = ["lab", "urine", "radiology", "procedure", "microbiology"]


def _trajectory_tool_args(trajectory: dict, tool_name: str) -> List[dict]:
    """All `tool_args` dicts for one tool name across a dspy.ReAct trajectory, in call order."""
    n_steps = 0
    while f"tool_name_{n_steps}" in trajectory:
        n_steps += 1
    return [
        trajectory[f"tool_args_{i}"]
        for i in range(n_steps)
        if trajectory.get(f"tool_name_{i}") == tool_name
    ]


def match_category(
    patient_gt: PatientGroundTruth, trajectory: dict, category: str
) -> Tuple[List[Any], List[Any], List[Any]]:
    """(gt_and_assistant, gt_only, assistant_only) for one order-score category.

    Reuses src/evaluations/objectives.py's evaluate_*_requests unmodified; this
    function's only job is reshaping a dspy.ReAct trajectory + PatientGroundTruth
    into the `matched_results` shape those functions expect (normally produced by
    src/evaluations/preprocess.py's extract_tool_use + merge_called_args, which
    target the old OpenAI-message-history format rather than a dspy trajectory).

    `procedure` is handled by reducing both sides to plain procedure-name strings
    (patient_gt.procedures' free-text long_title vs. the ProcedureRequestFHIR
    tool's `procedure` argument) rather than passing src/'s raw heterogeneous
    dicts (icd_code/icd_version/long_title vs. procedure) straight into
    measure_overlap, which would never compare equal regardless of any textual
    match -- see mira_dspy/README.md's Known Limitations for the exact-match
    caveat that remains even after this fix.
    """

    if category == "lab":
        assistant_values = [
            v
            for args in _trajectory_tool_args(trajectory, "LabRequestList")
            for v in args.get("lab_values", [])
        ]
        matched_results = {
            "lab_events": {"ground_truth": patient_gt.lab_events, "assistant": assistant_values}
        }
        overlap = evaluate_blood_requests(matched_results)
    elif category == "urine":
        assistant_values = [
            v
            for args in _trajectory_tool_args(trajectory, "UrineRequestList")
            for v in args.get("urine_values", [])
        ]
        matched_results = {
            "urine_events": {"ground_truth": patient_gt.urine_events, "assistant": assistant_values}
        }
        overlap = evaluate_urine_requests(matched_results)
    elif category == "microbiology":
        assistant_values = [
            v
            for args in _trajectory_tool_args(trajectory, "MicrobiologyRequestList")
            for v in args.get("microbiology_tests", [])
        ]
        matched_results = {
            "microbiology_events": {
                "ground_truth": patient_gt.microbiology_events,
                "assistant": assistant_values,
            }
        }
        overlap = evaluate_microbiology_requests(matched_results)
    elif category == "radiology":
        assistant_values = [
            {"modality": args.get("modality"), "region": args.get("region")}
            for args in _trajectory_tool_args(trajectory, "RadiologyRequestFHIR")
        ]
        matched_results = {
            "radiology_events": {
                "ground_truth": patient_gt.radiology_events,
                "assistant": assistant_values,
            }
        }
        overlap = evaluate_radiology_requests(matched_results)
    elif category == "procedure":
        assistant_values = [
            args.get("procedure")
            for args in _trajectory_tool_args(trajectory, "ProcedureRequestFHIR")
        ]
        gt_values = [p["long_title"] for p in patient_gt.procedures if p.get("long_title")]
        matched_results = {
            "procedures": {"ground_truth": gt_values, "assistant": assistant_values}
        }
        overlap = evaluate_procedure_requests(matched_results)
    else:
        raise ValueError(f"Unknown order-score category: {category!r}")

    return overlap["gt_and_assistant"], overlap["gt_only"], overlap["assistant_only"]


def category_f_beta(
    gt_and_assistant: List[Any], gt_only: List[Any], assistant_only: List[Any], beta: float = 1.0
) -> float:
    tp, fn, fp = len(gt_and_assistant), len(gt_only), len(assistant_only)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    if precision + recall == 0:
        return 0.0
    b2 = beta**2
    return (1 + b2) * precision * recall / (b2 * precision + recall)


def composite_order_score(
    patient_gt: PatientGroundTruth, trajectory: dict, beta: float = 1.0
) -> float:
    scores = {
        category: category_f_beta(*match_category(patient_gt, trajectory, category), beta=beta)
        for category in ORDER_CATEGORIES
    }
    return sum(scores.values()) / len(scores)  # macro-average, not micro


def feedback_text(
    category: str, gt_and_assistant: List[Any], gt_only: List[Any], assistant_only: List[Any]
) -> str:
    lines = []
    if gt_only:
        lines.append(
            f"Missed {category}: {', '.join(map(str, gt_only))} were in the actual workup "
            "but never ordered."
        )
    if assistant_only:
        lines.append(
            f"Unnecessary {category}: {', '.join(map(str, assistant_only))} were ordered but "
            "not part of the documented workup."
        )
    return " ".join(lines) or f"{category} ordering matched the documented workup exactly."


def mira_metric(
    gold, pred, trace=None, pred_name=None, pred_trace=None
) -> float | dspy.Prediction:
    """GEPA-compatible metric: 0.5 * diagnosis_score + 0.5 * order_score.

    `gold` is a dspy.Example carrying `patient_gt` (PatientGroundTruth) and
    `diagnosis_category` (the dataset's coarse diagnosis label, e.g.
    "appendicitis", used only as evalaute_diagnosis's matching criterion).

    Returns:
        float when pred_name is None (scalar score only)
        dspy.Prediction when pred_name is provided (for GEPA feedback)
    """

    order_score = composite_order_score(gold.patient_gt, pred.trajectory)

    diagnosis_matched_results = {
        "diagnosis": {
            "ground_truth": gold.patient_gt.diagnosis,
            "assistant": [{"diagnosis": pred.diagnosis}],
        }
    }
    diag_eval = evalaute_diagnosis(
        _create_openai_client(), diagnosis_matched_results, gold.diagnosis_category
    )
    diag_score = 1.0 if diag_eval["match"] else 0.0

    score = 0.5 * diag_score + 0.5 * order_score

    if pred_name is None:
        return score

    if pred_name.startswith("execute"):
        category_feedback = " ".join(
            feedback_text(category, *match_category(gold.patient_gt, pred.trajectory, category))
            for category in ORDER_CATEGORIES
        )
        feedback = f"Order-score {order_score:.2f}. {category_feedback}"
    else:
        match_word = "matched" if diag_eval["match"] else "did NOT match"
        feedback = (
            f"Diagnosis {match_word} the documented diagnosis ({diag_eval['reasoning']}). "
            f"Order-score {order_score:.2f} -- plan for any orders called out below."
        )

    return dspy.Prediction(score=score, feedback=feedback)
