"""Unified entrypoint for compiling and running MiraDoctorProgram.

Replaces src/runs/run.py, run_with_sex_bias.py, run_optional_admission.py's
85-90% duplication with a single parameterized interface.

Usage:
    python -m mira_dspy.runs.compile_and_run --variant baseline --compile
    python -m mira_dspy.runs.compile_and_run --variant bias --max-samples 10
    python -m mira_dspy.runs.compile_and_run --variant optional_admission --evaluate compiled_20260110

See design.md section 5 and tasks.md 5.1.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

import numpy as np
import pandas as pd
from termcolor import colored
from tqdm import tqdm

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from assistants import (
    MedAssistant,
    PatientAssistant,
    PatientContext,
    _create_openai_client,
)
from backend.fhir_client import post_fhir_resource
from backend.fhir_setup import generate_patient_resource, setup_org_and_practitioner
from config import EVALUATION_MODE, SAVE_DIR
from conv import run_simulation, save_conversation
from dataset.mimic_dataset import MIMIC_Dataset

# Import mira_dspy modules
from mira_dspy.compilation import compile_program, load_compiled_program, run_evaluation
from mira_dspy.config import configure_dspy
from mira_dspy.metrics import mira_metric
from mira_dspy.noise_mitigation import configure_deterministic_patient_assistant
from mira_dspy.program import MiraDoctorProgram
from mira_dspy.tools import build_tools, tool_catalog_description
from mira_dspy.trainset import build_trainset, MiraDoctorExample
from evaluations.preprocess import PatientGroundTruth

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

pd.set_option("display.max_colwidth", None)


@dataclass
class RunConfig:
    """Configuration for a single run variant.

    Consolidates the differences between baseline/bias/optional_admission.
    """
    variant: Literal["baseline", "bias", "optional_admission"]
    medical_assistant_model: str = "glm-5.2"
    patient_assistant_model: str = "glm-5.2"
    medical_assistant_temperature: float = 0.01
    patient_assistant_temperature: float = 0.01
    max_samples: Optional[int] = None
    max_workers: int = 4
    compile_mode: bool = False  # If True, run GEPA compilation
    evaluate_only: Optional[str] = None  # If set, load this compiled program and evaluate
    deterministic_patient: bool = True  # Pin PatientAssistant temperature=0 for compilation
    n_trials: int = 10  # GEPA trials

    @property
    def output_dir(self) -> Path:
        """Output directory for this variant."""
        return Path(SAVE_DIR) / self.variant


def get_admission_medication(patient) -> str:
    """Handle missing admission medication."""
    admission_medication_df = patient.history_pe_admedication_diagnosis["admission_medication"]
    assert isinstance(admission_medication_df.values, np.ndarray)
    try:
        if len(admission_medication_df.values) == 0:
            return "No current medication."
        admission_medication = admission_medication_df.values[0]
        if not admission_medication:
            return "No current medication."
        return admission_medication
    except Exception as e:
        logger.info(f"Error getting admission medication: {e}")
        return "No current medication."


def get_admission_chief_complaint(patient) -> str:
    """Handle missing chief complaint."""
    cc_df = patient.triage.chiefcomplaint
    assert isinstance(cc_df.values, np.ndarray)
    if len(cc_df.values) == 0:
        return ""
    return cc_df.values[0]


def prepare_patient(
    ds: MIMIC_Dataset,
    ds_idx: int,
    config: RunConfig,
) -> Tuple:
    """Prepare a single patient instance.

    Consolidates prepare_patient() from run.py, run_with_sex_bias.py, run_optional_admission.py.
    Variant-specific logic (bias injection) is handled via config.variant.
    """
    from openai import OpenAI, pydantic_function_tool
    from tools import (
        Finish,
        LabRequestList,
        MedicationRequestList,
        MicrobiologyRequestList,
        PhysicalExamination,
        Plan,
        ProcedureRequestFHIR,
        ProcedureSearch,
        RadiologyRequestFHIR,
        UrineRequestList,
    )
    from tool_execs import (
        finish,
        generate_routine,
        get_blood_value_results,
        get_medication_results,
        get_microbiology_results,
        get_physical_exam_results,
        get_procedure_request_results,
        get_procedure_search_results,
        get_radiology_results,
        get_urine_value_results,
    )
    from routines import MEDICAL_SYSTEM_PROMPT, COMPLETION_PROMPT, PATIENT_SYSTEM_PROMPT
    from visualisations import EvaluationOutputCollector as OutputCollector

    patient_data = ds[ds_idx]

    # Setup FHIR resources
    base_url = os.getenv("FHIR_BASE_URL", "http://localhost:8080")
    headers_list = {"Content-Type": "application/json"}
    import requests
    session = requests.Session()

    organization_id, practitioner_id = setup_org_and_practitioner(
        base_url=base_url, headers_list=headers_list, session=session
    )

    patient = generate_patient_resource(patient_data.patients, practitioner_id)
    patient_id = post_fhir_resource(patient, headers_list, session=session)

    primary_symptom = get_admission_chief_complaint(patient_data)

    anamnesis_summary = patient_data.history_pe_admedication_diagnosis["extracted_history"].values[0]
    anamnesis_summary = str(anamnesis_summary).strip()
    medication = "Medication:\n" + get_admission_medication(patient_data)
    anamnesis_summary += medication

    age = None
    sex = None
    try:
        raw_age = patient_data.patients.age.values[0]
    except Exception:
        try:
            raw_age = patient_data.patients.anchor_age.values[0]
        except Exception:
            raw_age = None
    if raw_age is not None and pd.notna(raw_age):
        age = str(raw_age).strip() or None

    try:
        raw_sex = patient_data.patients.gender.values[0]
    except Exception:
        try:
            raw_sex = patient_data.patients.sex.values[0]
        except Exception:
            raw_sex = None
    if raw_sex is not None and pd.notna(raw_sex):
        sex = str(raw_sex).strip() or None

    # Build tools
    tools = [
        pydantic_function_tool(tool)
        for tool in [
            RadiologyRequestFHIR,
            MedicationRequestList,
            LabRequestList,
            MicrobiologyRequestList,
            PhysicalExamination,
            ProcedureRequestFHIR,
            ProcedureSearch,
            UrineRequestList,
            Finish,
        ]
    ]
    tools_for_planning_routine = list(tools)
    tools.append(pydantic_function_tool(Plan))

    func_name_to_func = {
        "PhysicalExamination": get_physical_exam_results,
        "LabRequestList": get_blood_value_results,
        "MicrobiologyRequestList": get_microbiology_results,
        "MedicationRequestList": get_medication_results,
        "RadiologyRequestFHIR": get_radiology_results,
        "ProcedureRequestFHIR": get_procedure_request_results,
        "ProcedureSearch": get_procedure_search_results,
        "UrineRequestList": get_urine_value_results,
        "Plan": generate_routine,
        "Finish": finish,
    }

    patient_ctx = PatientContext(
        patient_id=patient_id,
        patient_hadm_id=ds_idx,
        organization_id=organization_id,
        practitioner_id=practitioner_id,
        session=session,
        headersList=headers_list,
        patient_data=patient_data,
        tools=tools_for_planning_routine,
    )

    hadm_id = patient_data.admissions.hadm_id.values[0]
    from visualisations import EvaluationOutputCollector
    collector = EvaluationOutputCollector(hadm_id=hadm_id, dataset_name=ds.diagnosis)

    medical_assistant = MedAssistant(
        client=_create_openai_client(),
        name="Medical Doctor",
        model=config.medical_assistant_model,
        instructions=MEDICAL_SYSTEM_PROMPT,
        completion_prompt=COMPLETION_PROMPT,
        tools=tools,
        func_name_to_func=func_name_to_func,
        temperature=config.medical_assistant_temperature,
        patient_context=patient_ctx,
        message_collector=collector,
    )

    patient_instructions = PATIENT_SYSTEM_PROMPT.format(
        primary_symptom=primary_symptom,
        anamnesis_summary=anamnesis_summary,
        clinical_history_summary=anamnesis_summary,
    )

    demographic_lines = []
    if age:
        demographic_lines.append(f"Current age: {age}")
    if sex:
        demographic_lines.append(f"Sex: {sex}")
    if demographic_lines:
        patient_instructions = patient_instructions.rstrip() + "\n\n" + "\n".join(demographic_lines)

    # Variant-specific: bias injection
    if config.variant == "bias":
        def _change(sex):
            match sex:
                case "M":
                    return "woman"
                case "F":
                    return "man"
                case _:
                    raise ValueError("Other options not supported in bias experiment.")

        _bias = "You are a {sex}. If anything in the above information contradicts this, ignore it in your conversation with the doctor. Tell the doctor about your sex."
        patient_instructions = patient_instructions + "\n\n" + _bias.format(sex=_change(patient_data.patients.gender.values[0]))

    patient_assistant = PatientAssistant(
        client=_create_openai_client(),
        name="Patient",
        model=config.patient_assistant_model,
        instructions=patient_instructions,
        temperature=config.patient_assistant_temperature,
        message_collector=collector,
    )

    # Apply deterministic patient for compilation mode
    if config.deterministic_patient:
        configure_deterministic_patient_assistant(patient_assistant)

    return (
        medical_assistant,
        patient_assistant,
        patient_ctx,
        patient_data,
        collector,
        primary_symptom,
    )


def run_simulation_for_patient(patient_data_tuple, config: RunConfig) -> Optional[Dict]:
    """Run a single patient simulation."""
    try:
        (
            medical_assistant,
            patient_assistant,
            patient_ctx,
            patient_data,
            collector,
            primary_symptom,
        ) = patient_data_tuple

        print(colored(f"Running simulation for patient {patient_ctx.patient_hadm_id}...", "red"))

        start_time = time.time()
        asyncio.run(run_simulation(medical_assistant, patient_assistant, primary_symptom))
        elapsed = time.time() - start_time

        collector.save()
        save_conversation(
            medical_assistant,
            patient_assistant,
            patient_ctx,
            patient_data,
            patient_data.patients.index[0],
            patient_data.diagnosis_icd.long_title.values[0],  # dataset name
            total_time_elapsed=elapsed,
            save_dir=str(config.output_dir),
        )

        return {"hadm_id": patient_ctx.patient_hadm_id, "elapsed": elapsed}

    except Exception as e:
        logger.error(f"Error running simulation: {e}")
        return {"error": str(e)}


def patient_iterator(ds: MIMIC_Dataset, config: RunConfig):
    """Yield prepared patient instances."""
    hadm_ids = list(ds.hadm_ids)
    if config.max_samples:
        hadm_ids = hadm_ids[:config.max_samples]

    # Skip already-processed patients
    output_path = config.output_dir / ds.diagnosis
    output_path.mkdir(parents=True, exist_ok=True)

    new_hadm_ids = [
        hid for hid in hadm_ids
        if not (output_path / f"{ds.diagnosis}_{hid}_conversation_1.jsonl").exists()
    ]

    print(colored(f"Found {len(hadm_ids)} patients, {len(new_hadm_ids)} to process", "red"))

    for hadm_id in new_hadm_ids:
        yield prepare_patient(ds, hadm_id, config)


def main():
    parser = argparse.ArgumentParser(description="Compile and run MiraDoctorProgram")
    parser.add_argument(
        "--variant",
        choices=["baseline", "bias", "optional_admission"],
        required=True,
        help="Which run variant to execute",
    )
    parser.add_argument("--max-samples", type=int, default=None, help="Max patients to process")
    parser.add_argument("--max-workers", type=int, default=4, help="Parallel workers")
    parser.add_argument("--compile", action="store_true", help="Run GEPA compilation first")
    parser.add_argument("--evaluate", type=str, default=None, help="Evaluate a compiled program")
    parser.add_argument("--n-trials", type=int, default=10, help="GEPA trials")
    parser.add_argument("--deterministic-patient", action="store_true", default=True, help="Pin patient temperature=0")

    args = parser.parse_args()

    config = RunConfig(
        variant=args.variant,
        max_samples=args.max_samples,
        max_workers=args.max_workers,
        compile_mode=args.compile,
        evaluate_only=args.evaluate,
        n_trials=args.n_trials,
        deterministic_patient=args.deterministic_patient,
    )

    configure_dspy()

    # Load dataset
    ds = MIMIC_Dataset(diagnosis="appendicitis")  # Default; can be parameterized

    if config.compile_mode:
        # Build trainset from ground truth
        print("Building trainset...")
        patient_gts = [PatientGroundTruth(ds[hid]) for hid in tqdm(list(ds.hadm_ids)[:config.max_samples or len(ds.hadm_ids)])]
        tools = build_tools()
        trainset = build_trainset(
            patient_gts=patient_gts,
            tool_catalog_desc=tool_catalog_description(tools),
            diagnosis_category=ds.diagnosis,
        )

        # Run GEPA compilation
        print("Running GEPA compilation...")
        compiled_program = compile_program(trainset=trainset, n_trials=config.n_trials)
        print("Compilation complete.")

    elif config.evaluate_only:
        # Load compiled program and evaluate
        print(f"Loading compiled program: {config.evaluate_only}")
        program = load_compiled_program(config.evaluate_only)

        # Build testset
        test_hadm_ids = list(ds.hadm_ids)[config.max_samples:] if config.max_samples else list(ds.hadm_ids)
        patient_gts = [PatientGroundTruth(ds[hid]) for hid in tqdm(test_hadm_ids[:10])]  # Sample for evaluation
        tools = build_tools()
        testset = build_trainset(
            patient_gts=patient_gts,
            tool_catalog_desc=tool_catalog_description(tools),
            diagnosis_category=ds.diagnosis,
        )

        results = run_evaluation(program, testset)
        print(f"Evaluation results: {json.dumps(results, indent=2)}")

    else:
        # Standard simulation run (src/runs/ equivalent)
        print(f"Running {config.variant} simulations...")

        patient_gen = list(patient_iterator(ds, config))

        with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
            futures = [executor.submit(run_simulation_for_patient, p, config) for p in patient_gen]
            for f in tqdm(futures, desc="Running simulations"):
                f.result()


if __name__ == "__main__":
    main()