"""Noise-mitigation strategies for the frozen PatientAssistant during compilation.

PatientAssistant (conv.py's ping-pong) is not a dspy.Predict, so GEPA treats it as
"environment noise" -- the optimizer cannot shape its outputs. Two mitigation
options per design.md section 1:

1. **Deterministic mode**: Pin temperature=0.0 + seed, sacrificing realism for
   stable optimization signal.
2. **Multi-rollout averaging**: Accept noise, run multiple rollouts per Example,
   average the metric across them.

This module implements option 1 (deterministic PatientAssistant) as the default,
with option 2 available via MultiRolloutMetric wrapper.

See design.md section 1 and spec.md's "Frozen patient simulator" requirement.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Optional, Union

import dspy


def configure_deterministic_patient_assistant(
    patient_assistant,
    temperature: float = 0.0,
    seed: int = 42,
) -> None:
    """Pin PatientAssistant's temperature and seed for deterministic outputs.

    This ensures the frozen interview produces identical transcripts across
    GEPA rollouts, eliminating noise from the optimizer's perspective.

    Args:
        patient_assistant: The PatientAssistant instance to configure
        temperature: Set to 0.0 for deterministic outputs
        seed: Seed for reproducibility (OpenAI SDK uses seed param)

    NOTE: OpenAI's seed parameter is passed to chat.completions.create(), but
    PatientAssistant.chat_completion() doesn't currently accept it. This function
    patches the instance's temperature attribute; seed injection would require
    modifying PatientAssistant.chat_completion() or passing it via the client.
    """
    patient_assistant.temperature = temperature
    # OpenAI SDK's seed is passed per-call; we can't patch it without modifying
    # chat_completion(). For now, temperature=0.0 provides near-determinism.


class MultiRolloutMetric:
    """Wrap mira_metric to average across multiple rollouts per Example.

    For noisy PatientAssistant environments, run N rollouts per gold/pred pair
    and return the mean metric. This smooths over interview transcript variance.

    NOTE: This wrapper requires access to the program instance to re-execute
    rollouts. The current implementation averages the metric over multiple calls
    with the same prediction, which is useful when the metric itself has variance.
    For true multi-rollout with program re-execution, pass the program via trace.

    Usage:
        metric = MultiRolloutMetric(base_metric=mira_metric, n_rollouts=3)
        gepa = dspy.GEPA(metric=metric, ...)
    """

    def __init__(
        self,
        base_metric: Callable,
        n_rollouts: int = 3,
        max_workers: int = 4,
    ):
        self.base_metric = base_metric
        self.n_rollouts = n_rollouts
        self.max_workers = max_workers

    def __call__(
        self,
        gold: dspy.Example,
        pred: dspy.Prediction,
        trace: Optional[List] = None,
        pred_name: Optional[str] = None,
        pred_trace: Optional[List] = None,
    ) -> Union[float, dspy.Prediction]:
        """Run N rollouts and average the metric.

        The program (pred) is evaluated N times against the same gold Example.
        For metrics with inherent variance (e.g., LLM judges), this smooths
        the signal. Each call invokes the base_metric independently.

        NOTE: This does NOT re-run the program; it averages the metric evaluation.
        For true multi-rollout with program re-execution, the program instance
        would need to be accessible via trace or pred_trace.
        """
        if self.n_rollouts <= 1:
            return self.base_metric(gold, pred, trace, pred_name, pred_trace)

        def _single_rollout(_) -> Union[float, dspy.Prediction]:
            return self.base_metric(gold, pred, trace, pred_name, pred_trace)

        # ThreadPoolExecutor handles parallel metric evaluation
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(_single_rollout, range(self.n_rollouts)))

        # Extract scores from results (handle both float and dspy.Prediction)
        scores = []
        first_prediction = None
        for r in results:
            if isinstance(r, dspy.Prediction):
                # Use getattr for safe attribute access on Prediction
                score = getattr(r, "score", 0.0)
                if first_prediction is None:
                    first_prediction = r
            else:
                score = float(r) if r is not None else 0.0
            scores.append(score)

        mean_score = sum(scores) / len(scores) if scores else 0.0

        # Return GEPA-compatible result
        if pred_name is not None and first_prediction is not None:
            # Return new Prediction with averaged score + original feedback
            return dspy.Prediction(
                score=mean_score,
                feedback=getattr(first_prediction, "feedback", ""),
            )

        return mean_score