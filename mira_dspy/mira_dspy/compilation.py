"""GEPA-based compilation entrypoint for MiraDoctorProgram.

This module provides the compile() function that runs dspy.GEPA on
MiraDoctorProgram against a MIMIC-derived trainset, persisting the optimized
program to mira_dspy/compiled/.

See design.md section 4 and spec.md's "GEPA-based compilation" requirement.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import dspy

from .config import COMPILED_DIR, get_optimizer_lm, configure_dspy
from .metrics import mira_metric
from .program import MiraDoctorProgram
from .tools import build_tools


def compile_program(
    trainset: List,
    n_trials: int = 10,
    max_iters: int = 20,
    compiled_name: Optional[str] = None,
    _save_intermediate: bool = True,
) -> dspy.Module:
    """Compile MiraDoctorProgram using GEPA.

    Args:
        trainset: List of MiraDoctorExample instances (from build_trainset())
        n_trials: Number of GEPA optimization trials (passed as max_metric_calls)
        max_iters: Max ReAct iterations per rollout
        compiled_name: Name for the compiled program (default: timestamp)

    Returns:
        Optimized MiraDoctorProgram instance
    """
    configure_dspy()

    # Build the program with shared tools
    tools = build_tools()
    program = MiraDoctorProgram(tools=tools, max_iters=max_iters)

    # GEPA optimizer -- uses the same model for reflection as task LM
    # Note: DSPy 3.2.1 GEPA uses reflection_lm (not teacher_lm) and auto/max_metric_calls
    optimizer_lm = get_optimizer_lm()
    gepa = dspy.GEPA(
        metric=mira_metric,
        reflection_lm=optimizer_lm,
        auto="medium",  # Equivalent to moderate optimization effort
    )

    # Run compilation
    print(f"Starting GEPA compilation with {len(trainset)} examples...")
    compiled_program = gepa.compile(
        program,
        trainset=trainset,
    )

    # Persist the compiled program
    compiled_name = compiled_name or datetime.now().strftime("compiled_%Y%m%d_%H%M%S")
    compiled_dir = COMPILED_DIR / compiled_name
    compiled_dir.mkdir(parents=True, exist_ok=True)

    # Save the program state
    program_path = compiled_dir / "program.json"
    compiled_program.save(str(program_path))

    # Save metadata
    metadata = {
        "compiled_at": datetime.now().isoformat(),
        "n_trials": n_trials,
        "max_iters": max_iters,
        "trainset_size": len(trainset),
        "task_lm": "glm-5.2",
        "optimizer_lm": "glm-5.2",
    }
    metadata_path = compiled_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Compiled program saved to {compiled_dir}")
    return compiled_program


def load_compiled_program(compiled_name: str, max_iters: int = 20) -> dspy.Module:
    """Load a previously compiled program.

    Args:
        compiled_name: Name of the compiled program directory
        max_iters: Max ReAct iterations (must match compilation)

    Returns:
        Compiled MiraDoctorProgram instance
    """
    compiled_dir = COMPILED_DIR / compiled_name
    program_path = compiled_dir / "program.json"

    if not program_path.exists():
        raise FileNotFoundError(f"No compiled program found at {program_path}")

    # Build fresh program structure and load state
    tools = build_tools()
    program = MiraDoctorProgram(tools=tools, max_iters=max_iters)
    program.load(str(program_path))

    return program


def run_evaluation(
    program: MiraDoctorProgram,
    testset: List,
) -> dict:
    """Evaluate a compiled program on a held-out testset.

    Args:
        program: Compiled MiraDoctorProgram (or uncompiled baseline)
        testset: List of MiraDoctorExample instances for evaluation

    Returns:
        Dictionary with aggregated metrics (mean/std per component)
    """
    configure_dspy()

    from concurrent.futures import ThreadPoolExecutor
    from tqdm import tqdm

    def _evaluate_single(example) -> dict:
        """Run single example and return metric breakdown."""
        try:
            # Build patient context from example
            from assistants import PatientContext
            from backend.fhir_client import post_fhir_resource
            from backend.fhir_setup import (
                generate_patient_resource,
                setup_org_and_practitioner,
            )

            patient_gt = example.patient_gt
            patient_data = patient_gt.patient_data

            # Setup FHIR resources (mirrors prepare_patient in run.py)
            base_url = os.getenv("FHIR_BASE_URL", "http://localhost:8080")
            headers_list = {"Content-Type": "application/json"}
            import requests
            session = requests.Session()

            organization_id, practitioner_id = setup_org_and_practitioner(
                base_url=base_url, headers_list=headers_list, session=session
            )

            patient = generate_patient_resource(
                patient_data.patients, practitioner_id
            )
            patient_id = post_fhir_resource(patient, headers_list, session=session)

            patient_context = PatientContext(
                patient_id=patient_id,
                patient_hadm_id=str(patient_data.admissions.hadm_id.values[0]),
                organization_id=organization_id,
                practitioner_id=practitioner_id,
                session=session,
                headersList=headers_list,
                patient_data=patient_data,
                tools=[],
            )

            # Run the program
            pred = program(
                chief_complaint=example.chief_complaint,
                history_so_far=example.history_so_far,
                tool_catalog_desc=example.tool_catalog_desc,
                patient_context=patient_context,
            )

            # Compute metric
            metric_result = mira_metric(example, pred, pred_name="evaluate")

            if isinstance(metric_result, dspy.Prediction):
                score = metric_result.score
            else:
                score = metric_result

            return {
                "score": score,
                "hadm_id": patient_data.admissions.hadm_id.values[0],
            }

        except Exception as e:
            return {
                "error": str(e),
                "hadm_id": getattr(
                    example.patient_gt.patient_data, "hadm_id", "unknown"
                ),
            }

    # Run evaluation in parallel
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = list(tqdm(
            executor.map(_evaluate_single, testset),
            total=len(testset),
            desc="Evaluating"
        ))
        results = list(futures)

    # Aggregate results
    scores = [r["score"] for r in results if "score" in r]
    errors = [r for r in results if "error" in r]

    mean_score = sum(scores) / len(scores) if scores else 0.0
    variance = sum((s - mean_score) ** 2 for s in scores) / len(scores) if scores else 0.0

    return {
        "mean_score": mean_score,
        "std_score": variance ** 0.5,
        "n_success": len(scores),
        "n_errors": len(errors),
        "errors": errors[:5] if errors else [],  # First 5 errors for debugging
    }