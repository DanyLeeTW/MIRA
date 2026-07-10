import asyncio
from typing import List

import dspy

from .signatures import ConductWorkup, PlanDifferentialWorkup
from .tools import patient_context_scope


class MiraDoctorProgram(dspy.Module):
    """Replaces generate_routine() (self.plan) + MedAssistant.chat() (self.execute).

    Scope-limited to the "order tests + diagnose" stage; the patient interview
    (src/conv.py, PatientAssistant) is not part of this program at all -- see
    mira_dspy/runs/compile_and_run.py for how history_so_far is sourced.
    """

    def __init__(self, tools: List[dspy.Tool], max_iters: int = 20):
        super().__init__()
        self.plan = dspy.ChainOfThought(PlanDifferentialWorkup)
        self.execute = dspy.ReAct(ConductWorkup, tools=tools, max_iters=max_iters)

    async def aforward(
        self,
        chief_complaint: str,
        history_so_far: str,
        tool_catalog_desc: str,
        patient_context,
    ) -> dspy.Prediction:
        with patient_context_scope(patient_context):
            plan_pred = await self.plan.acall(
                chief_complaint=chief_complaint,
                history_so_far=history_so_far,
                tool_catalog_desc=tool_catalog_desc,
            )
            exec_pred = await self.execute.acall(
                chief_complaint=chief_complaint,
                history_so_far=history_so_far,
                plan=plan_pred.plan,
            )
        return dspy.Prediction(
            diagnosis=exec_pred.diagnosis,
            trajectory=exec_pred.trajectory,
            plan=plan_pred.plan,
        )

    def forward(
        self,
        chief_complaint: str,
        history_so_far: str,
        tool_catalog_desc: str,
        patient_context,
    ) -> dspy.Prediction:
        """Sync wrapper for MiraDoctorProgram.

        self.execute's tools wrap tool_execs.py's async FHIR/backend calls, so
        the native entrypoint is aforward(). This sync path exists for callers
        (e.g. optimizer/evaluator internals) that invoke the program synchronously.

        NOTE: Uses nest_asyncio to handle nested event loops. If called from an
        already-running event loop (e.g., inside GEPA), nest_asyncio.apply() must
        have been called. The compile_and_run.py entrypoint handles this.
        """
        try:
            # Check if we're inside a running event loop
            asyncio.get_running_loop()
            # We're in an async context - use nest_asyncio to allow nested run
            import nest_asyncio
            nest_asyncio.apply()
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            pass

        return asyncio.run(
            self.aforward(
                chief_complaint, history_so_far, tool_catalog_desc, patient_context
            )
        )
