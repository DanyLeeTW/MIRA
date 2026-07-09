#!/usr/bin/env python3
"""
MIRA 完整模拟运行脚本 (使用模拟数据)

使用方法:
    cd src
    python ../scripts/run_mira_full.py --diagnosis appendicitis --max-patients 2
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd

# Use mock dataset directory
os.environ["MIRA_DIAGNOSIS_DATASETS_DIR"] = str(
    Path(__file__).parent.parent / "src" / "raw" / "derived" / "diagnosis_datasets"
)

from config import (
    MEDICAL_ASSISTANT_MODEL,
    MEDICAL_ASSISTANT_TEMPERATURE,
    PATIENT_ASSISTANT_MODEL,
    PATIENT_ASSISTANT_TEMPERATURE,
)
from dataset.mimic_dataset import MIMIC_Dataset
from paths import DIAGNOSIS_DATASETS_DIR
from assistants import MedAssistant, PatientAssistant, PatientContext, _create_openai_client
from conv import run_simulation, save_conversation
from backend.fhir_setup import setup_org_and_practitioner
from backend.fhir_client import post_fhir_resource
from openai import pydantic_function_tool
from tools import (
    Finish,
    LabRequestList,
    MedicationRequestList,
    MicrobiologyRequestList,
    PhysicalExamination,
    ProcedureRequestFHIR,
    ProcedureSearch,
    RadiologyRequestFHIR,
    UrineRequestList,
    Plan,
    PatientHistory,
)
from termcolor import colored
import requests
import time


def get_admission_medication(patient):
    """Get admission medication"""
    try:
        med_df = patient.history_pe_admedication_diagnosis.get("admission_medication")
        if med_df is not None and len(med_df) > 0:
            return str(med_df.values[0])
    except Exception:
        pass
    return "No current medication."


def get_admission_chief_complaint(patient):
    """Get chief complaint"""
    try:
        cc_df = patient.triage.chiefcomplaint
        if len(cc_df) > 0:
            return str(cc_df.values[0])
    except Exception:
        pass
    return "Abdominal pain"


async def run_patient_simulation(ds, idx, diagnosis):
    """Run simulation for a single patient"""

    # Get patient data
    patient_data = ds[idx]

    print(colored(f"\n--- Patient {idx} ({patient_data.admissions.hadm_id.values[0]}) ---", "blue"))

    # Create OpenAI client
    client = _create_openai_client()

    # Setup FHIR resources
    base_url = "http://localhost:8080/fhir"
    headers = {"Content-Type": "application/fhir+json"}

    session = requests.Session()

    try:
        org_id, practitioner_id = setup_org_and_practitioner(base_url, headers, session)
        print(f"  Organization: {org_id}, Practitioner: {practitioner_id}")
    except Exception as e:
        print(colored(f"  Warning: Could not setup FHIR: {e}", "yellow"))
        org_id, practitioner_id = "mock-org", "mock-practitioner"

    # Prepare tools
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

    # System prompts
    medical_prompt = """You are an emergency medicine physician conducting a patient consultation.

Your role:
1. Take a focused history based on the chief complaint
2. Perform relevant physical examinations
3. Order appropriate diagnostic tests (labs, imaging)
4. Make a diagnosis and treatment plan
5. Call the Finish tool when you have completed the consultation

Be thorough but efficient. The patient will respond to your questions.
"""

    patient_prompt = """You are a patient in the emergency department.

Chief complaint: {primary_symptom}

History summary: {anamnesis_summary}

You should respond naturally to the physician's questions.
Provide relevant information about your symptoms, medical history, and current medications.
Be cooperative but only share information when asked.
"""

    completion_prompt = "Please wrap up the consultation and provide your final diagnosis and treatment plan."

    # Get patient info
    chief_complaint = get_admission_chief_complaint(patient_data)

    try:
        history = patient_data.history_pe_admedication_diagnosis.get("extracted_history")
        anamnesis = str(history.values[0]) if history is not None and len(history) > 0 else "No significant history"
    except Exception:
        anamnesis = "No significant history"

    # Create patient context
    patient_context = PatientContext(
        patient_id=str(idx),
        patient_hadm_id=str(idx),
        organization_id=org_id,
        practitioner_id=practitioner_id,
        session=session,
        headersList=headers,
        patient_data=patient_data,
        tools=tools,
    )

    # Initialize assistants
    medical_assistant = MedAssistant(
        client=client,
        name="Medical Doctor",
        model=MEDICAL_ASSISTANT_MODEL,
        instructions=medical_prompt,
        completion_prompt=completion_prompt,
        tools=tools,
        func_name_to_func={
            "PhysicalExamination": lambda **kwargs: {"result": "Normal exam. Mild RLQ tenderness."},
            "LabRequestList": lambda **kwargs: {"result": "Labs ordered: CBC, BMP, LFTs"},
            "RadiologyRequestFHIR": lambda **kwargs: {"result": "CT ordered: Abdomen/Pelvis"},
            "Finish": lambda **kwargs: {"result": "Consultation completed"},
        },
        temperature=MEDICAL_ASSISTANT_TEMPERATURE,
        max_steps=10,
        patient_context=patient_context,
    )

    patient_instructions = patient_prompt.format(
        primary_symptom=chief_complaint,
        anamnesis_summary=anamnesis,
        clinical_history_summary=anamnesis,
    )

    patient_assistant = PatientAssistant(
        client=client,
        name="Patient",
        model=PATIENT_ASSISTANT_MODEL,
        instructions=patient_instructions,
        temperature=PATIENT_ASSISTANT_TEMPERATURE,
    )

    print(colored(f"  Chief complaint: {chief_complaint}", "cyan"))

    # Run simulation
    start_time = time.time()
    try:
        await run_simulation(medical_assistant, patient_assistant, chief_complaint)
        elapsed = time.time() - start_time
        print(colored(f"  Simulation completed in {elapsed:.1f}s", "green"))
        return True
    except Exception as e:
        print(colored(f"  Error: {e}", "red"))
        import traceback
        traceback.print_exc()
        return False


async def main():
    parser = argparse.ArgumentParser(description="Run MIRA simulation")
    parser.add_argument("--diagnosis", type=str, default="appendicitis")
    parser.add_argument("--max-patients", type=int, default=2)
    args = parser.parse_args()

    print(colored(f"\n{'='*60}", "blue"))
    print(colored(f"MIRA Simulation - Diagnosis: {args.diagnosis}", "blue"))
    print(colored(f"{'='*60}", "blue"))
    print(colored(f"Medical Model: {MEDICAL_ASSISTANT_MODEL}", "green"))
    print(colored(f"Patient Model: {PATIENT_ASSISTANT_MODEL}", "green"))

    # Load dataset
    print(colored(f"\nLoading dataset from: {DIAGNOSIS_DATASETS_DIR}", "cyan"))

    try:
        ds = MIMIC_Dataset(
            diagnosis=args.diagnosis,
            dataset_dir=DIAGNOSIS_DATASETS_DIR / args.diagnosis
        )
        print(colored(f"Dataset loaded: {len(ds.hadm_ids)} patients", "green"))
    except Exception as e:
        print(colored(f"Error loading dataset: {e}", "red"))
        return

    # Run simulations
    num_patients = min(args.max_patients, len(ds.hadm_ids))
    print(colored(f"\nRunning {num_patients} patient simulations...", "yellow"))

    success = 0
    for i in range(num_patients):
        result = await run_patient_simulation(ds, i, args.diagnosis)
        if result:
            success += 1

    print(colored(f"\n{'='*60}", "blue"))
    print(colored(f"Completed: {success}/{num_patients} successful", "green" if success == num_patients else "yellow"))
    print(colored(f"{'='*60}", "blue"))


if __name__ == "__main__":
    asyncio.run(main())
