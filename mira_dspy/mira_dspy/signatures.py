import dspy


class PlanDifferentialWorkup(dspy.Signature):
    """Given a patient's chief complaint, history so far, and the catalog of available
    diagnostic/therapeutic tools, produce a structured differential-diagnosis workup
    plan describing which labs, imaging, procedures, microbiology tests, and
    medications to pursue next and why. Use if-else branching for alternative
    strategies (e.g. if ultrasound is unavailable, use CT). Only recommend actions
    that have not already been taken according to history_so_far. Prefer the tool
    with the highest diagnostic accuracy for the suspected condition(s), and follow
    current best-practice hospital guidelines."""

    chief_complaint: str = dspy.InputField(
        desc="The patient's presenting chief complaint(s)."
    )
    history_so_far: str = dspy.InputField(
        desc="Clinical history gathered so far: symptoms, past medical history, "
        "admission medication, and any results already available."
    )
    tool_catalog_desc: str = dspy.InputField(
        desc="Description of the diagnostic/therapeutic tools and their parameters "
        "available to act on this plan."
    )
    plan: str = dspy.OutputField(
        desc="A structured, numbered differential workup plan: which tests/treatments "
        "to pursue next, with concrete parameters, and if-else branches for alternatives."
    )


class ConductWorkup(dspy.Signature):
    """Given a patient's chief complaint, history so far, and a differential workup
    plan, carry out the plan by calling the available diagnostic/therapeutic tools
    (labs, urine, microbiology, radiology, procedures, medications) with concrete
    parameters, then produce a final concise diagnosis once the workup is complete.
    Call every tool the plan calls for before finishing; do not stop early."""

    chief_complaint: str = dspy.InputField(
        desc="The patient's presenting chief complaint(s)."
    )
    history_so_far: str = dspy.InputField(
        desc="Clinical history gathered so far: symptoms, past medical history, "
        "admission medication, and any results already available."
    )
    plan: str = dspy.InputField(desc="The differential workup plan to execute.")
    diagnosis: str = dspy.OutputField(
        desc="The final diagnosis in short form, e.g. `Left sided pneumonia`."
    )
