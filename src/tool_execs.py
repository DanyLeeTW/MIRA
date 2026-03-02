import asyncio
import json
import time
from typing import Dict, List, Optional

import pandas as pd
import requests
from backend.fhir_client import post_fhir_resource
from backend.log import logger
from config import (
    QDRANT_ICD_PROCEDURE_COLLECTION_NAME,
    QDRANT_ICD_PROCEDURE_EMBEDDING_MODEL,
    QDRANT_URL,
    REASONING_MODEL,
)
from dotenv import load_dotenv
from fhir.resources.resource import Resource
from fhir_handlers import *
from IPython.display import HTML, display
from paths import PANCREATIC_CANCER_INFO_PATH, QDRANT_STORAGE_DIR
from qdrant_client import QdrantClient
from qdrant_collection import Qdrant_Collection
from tools import *
from transformers import AutoModel

load_dotenv()


async def request_fetch_and_poll(
    patient_id: str,
    patient_hadm_id: str,
    handlers: List[FHIRResourceHandler],
    organization_id: str,
    headersList: Dict[str, str],
    session: requests.Session,
) -> str:
    logger.info(f"Requesting and polling results for patient {patient_id}")

    async def _post_resource(resource: Resource) -> Optional[str]:
        try:
            resource_id = await asyncio.to_thread(
                post_fhir_resource,
                resource=resource,
                headers=headersList,
                session=session,
            )
            return resource_id
        except Exception as e:
            logger.error(f"Error posting resource: {e}")
            return None

    async def _fetch_result(handler: FHIRResourceHandler) -> Optional[pd.Series]:
        try:
            return await handler.fetch_result(patient_id, patient_hadm_id)
        except Exception as e:
            logger.error(f"Error fetching result: {e}")
            return None

    # Convert handlers to FHIR ServiceRequests
    service_requests = [handler.to_fhir() for handler in handlers]
    # Post ServiceRequests asynchronously and capture their IDs
    service_request_ids = await asyncio.gather(
        *[_post_resource(sr) for sr in service_requests]
    )

    # Fetch results asynchronously
    results = await asyncio.gather(*[_fetch_result(handler) for handler in handlers])

    notes = []
    # Generate and post resources
    for handler, sr_id, result in zip(handlers, service_request_ids, results):
        try:
            # Generate result resources
            result_resources = await handler.generate_result_resource(
                result,
                patient_id,
                sr_id,
                organization_id,
            )

            if not isinstance(result_resources, list):
                result_resources = [result_resources]

            # Separate parent and child resources
            parent_resource = result_resources[0]
            child_resources = result_resources[1:]

            parent_resource.id = None

            if hasattr(parent_resource, "hasMember"):
                parent_resource.hasMember = None
            if hasattr(parent_resource, "result"):
                parent_resource.result = None

            # Post parent resource and get assigned ID
            parent_res_id = await _post_resource(parent_resource)
            if (
                not parent_res_id
                and parent_resource.resource_type == "DiagnosticReport"
                and hasattr(parent_resource, "presentedForm")
                and parent_resource.presentedForm
            ):
                logger.warning(
                    "Retrying DiagnosticReport post without presentedForm after initial failure."
                )
                parent_resource.presentedForm = None
                parent_res_id = await _post_resource(parent_resource)
            if not parent_res_id:
                logger.error("Failed to post parent resource")
                continue
            parent_resource.id = parent_res_id

            # Update child resources with correct "derivedFrom" reference
            for child in child_resources:
                child.id = None  # Let the server assign the ID
                if hasattr(child, "derivedFrom") and child.derivedFrom:
                    for ref in child.derivedFrom:
                        # Replace the local-id with the actual id
                        if "local-id" in ref.reference:
                            ref.reference = (
                                f"{parent_resource.resource_type}/{parent_res_id}"
                            )
                # Post child resource
                child_res_id = await _post_resource(child)
                if not child_res_id:
                    logger.error("Failed to post child resource")
                    continue
                child.id = child_res_id

            # Update parent resource with references to child resources
            if child_resources:
                if parent_resource.resource_type == "Observation":
                    parent_resource.hasMember = [
                        Reference(reference=f"Observation/{child.id}")
                        for child in child_resources
                    ]
                elif parent_resource.resource_type == "DiagnosticReport":
                    parent_resource.result = [
                        Reference(reference=f"Observation/{child.id}")
                        for child in child_resources
                    ]
                else:
                    # For other resource types, handle accordingly or skip
                    pass

                # Update the parent resource on the server
                await _post_resource(parent_resource)

            # Collect notes
            if hasattr(parent_resource, "note") and parent_resource.note:
                notes.append(parent_resource.note[0].text)
            for child in child_resources:
                if hasattr(child, "note") and child.note:
                    notes.append(child.note[0].text)
        except Exception as e:
            logger.error(f"Error generating result resource: {e}")

    logger.info(f"Completed request_and_poll for patient {patient_id}")
    return "".join(notes)


async def get_blood_value_results(
    patient_id: str,
    patient_hadm_id: str,
    organization_id: str,
    practitioner_id: str,
    session: requests.Session,
    headersList: Dict[str, str],
    lab_values: list,
    patient_data: pd.DataFrame,
    **kwargs,  # catch unused arguments
) -> str:
    """
    Processes multiple blood value requests for a patient.

    Args:
        patient_id (str): The ID of the patient.
        organization_id (str): The ID of the organization.
        practitioner_id (str): The ID of the practitioner.
        session (requests.Session): The HTTP session with retry logic.
        headersList (Dict[str, str]): The headers for HTTP requests.
        lab_values (List[Dict[str, Any]]): A list of dictionaries, each containing 'lab_value'.
        patient_data (pd.DataFrame): The DataFrame containing patient lab events.

    Returns:
        str: Concatenated notes from all observations.
    """

    patient_data_table = patient_data.lab_events

    logger.info("Requesting lab values ... 🩸🩸🩸")

    # Create LabRequestFHIR instances
    lab_requests_fhir = [
        LabRequestFHIR(
            lab_value=params["lab_value"],
            patient_id=patient_id,
            practitioner_id=practitioner_id,
            organization_id=organization_id,
        )
        for params in lab_values
    ]

    # Create LabRequestHandler instances
    lab_handlers = [
        LabRequestHandler(
            request=lab_request_fhir,
            patient_data=patient_data_table,
        )
        for lab_request_fhir in lab_requests_fhir
    ]

    # Call the asynchronous request_and_poll function
    notes = await request_fetch_and_poll(
        patient_id=patient_id,
        patient_hadm_id=patient_hadm_id,
        handlers=lab_handlers,
        organization_id=organization_id,
        headersList=headersList,
        session=session,
    )

    # display_notes = "**Requesting patient lab values ... 🩸🩸🩸**\n\n" + notes
    # display_action(display_notes, "get_blood_value_results")

    return notes


################################################################################


async def get_urine_value_results(
    patient_id: str,
    patient_hadm_id: str,
    organization_id: str,
    practitioner_id: str,
    session: requests.Session,
    headersList: Dict[str, str],
    urine_values: list,
    patient_data: pd.DataFrame,
    **kwargs,  # catch unused arguments
) -> str:
    """
    Processes multiple blood value requests for a patient.

    Args:
        patient_id (str): The ID of the patient.
        organization_id (str): The ID of the organization.
        practitioner_id (str): The ID of the practitioner.
        session (requests.Session): The HTTP session with retry logic.
        headersList (Dict[str, str]): The headers for HTTP requests.
        urine_values (List[Dict[str, Any]]): A list of dictionaries, each containing 'urine_value'.
        patient_data (pd.DataFrame): The DataFrame containing patient urine events.

    Returns:
        str: Concatenated notes from all observations.
    """

    patient_data_table = patient_data.lab_events

    logger.info("Requesting urine values ... 🫗💧🍻")

    # Create LabRequestFHIR instances
    urine_requests_fhir = [
        UrineRequestFHIR(
            urine_value=params["urine_value"],
            patient_id=patient_id,
            practitioner_id=practitioner_id,
            organization_id=organization_id,
        )
        for params in urine_values
    ]

    # Create LabRequestHandler instances
    urine_handlers = [
        UrineRequestHandler(
            request=urine_request_fhir,
            patient_data=patient_data_table,
        )
        for urine_request_fhir in urine_requests_fhir
    ]

    # Call the asynchronous request_and_poll function
    notes = await request_fetch_and_poll(
        patient_id=patient_id,
        patient_hadm_id=patient_hadm_id,
        handlers=urine_handlers,
        organization_id=organization_id,
        headersList=headersList,
        session=session,
    )

    # display_notes = "**Requesting patient lab values ... 🫗💧🍻**\n\n" + notes
    # display_action(display_notes, "get_blood_value_results")

    return notes


async def get_medication_results(
    patient_id: str,
    patient_hadm_id: str,
    organization_id: str,
    practitioner_id: str,
    session: requests.Session,
    headersList: Dict[str, str],
    medications: list,
    patient_data: pd.DataFrame,
    **kwargs,  # catch unused arguments
) -> str:
    """
    Processes multiple medication requests for a patient.

    Args:
        patient_id (str): The ID of the patient.
        organization_id (str): The ID of the organization.
        practitioner_id (str): The ID of the practitioner.
        session (requests.Session): The HTTP session with retry logic.
        headersList (Dict[str, str]): The headers for HTTP requests.
        medications (List[Dict[str, Any]]): A list of dictionaries, each containing 'medication_value'.
        patient_data (pd.DataFrame): The DataFrame containing patient medication events.

    Returns:
        str: Concatenated notes from all observations.
    """

    patient_data_table = patient_data.medication  # Adjusted for medication data

    logger.info("Requesting medication values ... 💊💊💊")

    # Create MedicationRequestFHIR instances
    medication_requests_fhir = [
        MedicationRequestFHIR(
            drug_name=params["drug_name"],
            dosage_text=params["dosage_text"],  # Ensure these fields are provided
            dosage_value=params["dosage_value"],
            dosage_unit=params["dosage_unit"],
            period=params["period"],
            period_unit=params["period_unit"],
            frequency=params["frequency"],
            route=params["route"],
            patient_id=patient_id,
            organization_id=organization_id,
            practitioner_id=practitioner_id,
        )
        for params in medications
    ]

    # Create MedicationRequestHandler instances
    medication_handlers = [
        MedicationRequestHandler(
            request=medication_request_fhir,
            patient_data=patient_data_table,
        )
        for medication_request_fhir in medication_requests_fhir
    ]

    # Call the asynchronous request_fetch_and_poll function
    notes = await request_fetch_and_poll(
        patient_id=patient_id,
        patient_hadm_id=patient_hadm_id,
        handlers=medication_handlers,
        organization_id=organization_id,
        headersList=headersList,
        session=session,
    )

    # display_notes = "**Requesting and uploading patient medication ... 💊💊💊**\n\n" + notes
    # display_action(display_notes, "get_medication_results")

    return notes


# Define get_physical_exam_results function
async def get_physical_exam_results(
    patient_id: str,
    patient_hadm_id: str,
    organization_id: str,
    practitioner_id: str,
    session: requests.Session,
    headersList: Dict[str, str],
    patient_data: pd.DataFrame,
    **kwargs,  # catch unused arguments
) -> str:
    """
    Processes physical examination requests for a patient.

    Args:
        patient_id (str): The ID of the patient.
        organization_id (str): The ID of the organization.
        practitioner_id (str): The ID of the practitioner.
        session (requests.Session): The HTTP session with retry logic.
        headersList (Dict[str, str]): The headers for HTTP requests.
        pe_requests (list): A list of dictionaries representing PE requests.
        patient_data (pd.DataFrame): The DataFrame containing patient data.

    Returns:
        str: Concatenated notes from all observations.
    """

    logger.info("Requesting physical examination data ... 🩺🩺🩺")

    patient_data_table = patient_data.history_pe_admedication_diagnosis

    vital_sign_request_fhir = PhysicalExamRequestFHIR(
        patient_id=patient_id,
        practitioner_id=practitioner_id,
        organization_id=organization_id,
    )

    vital_sign_handler = PhysicalExamRequestHandler(
        request=vital_sign_request_fhir,
        patient_data=patient_data_table,
    )
    # Call the asynchronous request_and_poll function
    notes = await request_fetch_and_poll(
        patient_id=patient_id,
        patient_hadm_id=patient_hadm_id,
        handlers=[vital_sign_handler],
        organization_id=organization_id,
        headersList=headersList,
        session=session,
    )

    # display_notes = "**Performing physical examination ... 🩺🩺🩺**\n\n" + notes
    # display_action(display_notes, "get_physical_exam_results")

    return notes


# Define get_physical_exam_results function
async def get_microbiology_results(
    patient_id: str,
    patient_hadm_id: str,
    organization_id: str,
    practitioner_id: str,
    session: requests.Session,
    headersList: Dict[str, str],
    microbiology_tests: list,
    patient_data: pd.DataFrame,
    **kwargs,  # catch unused arguments
) -> str:
    """
    Processes microbiology requests for a patient.

    Args:
        patient_id (str): The ID of the patient.
        organization_id (str): The ID of the organization.
        practitioner_id (str): The ID of the practitioner.
        session (requests.Session): The HTTP session with retry logic.
        headersList (Dict[str, str]): The headers for HTTP requests.
        pe_requests (list): A list of dictionaries representing PE requests.
        patient_data (pd.DataFrame): The DataFrame containing patient data.

    Returns:
        str: Concatenated notes from all observations.
    """

    logger.info("Requesting microbiology examination data ... 🦠🧫🧬")

    patient_data_table = patient_data.microbiology

    # Create MicrobiologyRequestFHIR instances
    microbiology_requests_fhir = [
        MicrobiologyRequestFHIR(
            microbiology_value=params["microbiology_value"],
            patient_id=patient_id,
            practitioner_id=practitioner_id,
            organization_id=organization_id,
        )
        for params in microbiology_tests
    ]

    microbiology_handlers = [
        MicrobiologyRequestHandler(
            request=microbiology_request_fhir,
            patient_data=patient_data_table,
        )
        for microbiology_request_fhir in microbiology_requests_fhir
    ]

    # Call the asynchronous request_and_poll function
    notes = await request_fetch_and_poll(
        patient_id=patient_id,
        patient_hadm_id=patient_hadm_id,
        handlers=microbiology_handlers,
        organization_id=organization_id,
        headersList=headersList,
        session=session,
    )

    # display_notes = "**Requesting microbiology tests ... 🦠🧫🧬**\n\n" + notes
    # display_action(display_notes, "get_microbiology_results")

    return notes


async def get_radiology_results(
    patient_id: str,
    patient_hadm_id: str,
    organization_id: str,
    practitioner_id: str,
    session: requests.Session,
    headersList: Dict[str, str],
    modality: RadiologyModalityValue,
    region: RadiologyRegionValue,
    info: Optional[str],
    patient_data: pd.DataFrame,
    **kwargs,  # catch unused arguments
) -> str:
    """
    Processes radiology requests for a patient.

    Args:
        patient_id (str): The ID of the patient.
        organization_id (str): The ID of the organization.
        practitioner_id (str): The ID of the practitioner.
        session (requests.Session): The HTTP session with retry logic.
        headersList (Dict[str, str]): The headers for HTTP requests.
        modality (RadiologyModalityValue): The imaging modality to be used.
        region (RadiologyRegionValue): The body region to be imaged.
        info (Optional[str]): Additional clinical information or questions.
        patient_data (pd.DataFrame): The DataFrame containing patient data.

    Returns:
        str: Concatenated notes from all reports.
    """

    logger.info("Requesting radiology examination data ... 🩻🩻🩻")

    # Create RadiologyRequestFHIR instances
    radiology_request_fhir = RadiologyRequestFHIR(
        modality=modality,
        region=region,
        info=info or None,
        patient_id=patient_id,
        practitioner_id=practitioner_id,
        organization_id=organization_id,
    )

    # Create RadiologyRequestHandler instances
    radiology_handler = RadiologyRequestHandler(
        request=radiology_request_fhir,
        patient_data=patient_data,  # Adjust if necessary
    )

    # Call the asynchronous request_and_poll function
    notes = await request_fetch_and_poll(
        patient_id=patient_id,
        patient_hadm_id=patient_hadm_id,
        handlers=[radiology_handler],
        organization_id=organization_id,
        headersList=headersList,
        session=session,
    )

    # display_notes = "**Requesting radiology examination data ... 🩻🩻🩻**\n\n" + notes
    # display_action(display_notes, "get_radiology_results")

    return notes


def connect_qdrant(embedding_client):
    """Connect to a Qdrant collection"""

    qdrant_client = QdrantClient(url=QDRANT_URL)
    collection = Qdrant_Collection(
        qdrant_client,
        embedding_client,
        QDRANT_ICD_PROCEDURE_COLLECTION_NAME,
        QDRANT_ICD_PROCEDURE_EMBEDDING_MODEL,
    )

    print(qdrant_client.get_collections())

    return qdrant_client, collection


async def get_procedure_search_results(
    patient_id: str,
    patient_hadm_id: str,
    organization_id: str,
    practitioner_id: str,
    session: requests.Session,
    headersList: Dict[str, str],
    procedure: str,
    # procedure_extended: str,
    patient_data: pd.DataFrame,
    **kwargs,  # catch unused arguments
    # collection: Qdrant_Collection,
) -> str:
    """
    Processes procedure requests for a patient.

    Returns:
        str: Concatenated notes from all reports.
    """

    logger.info("Processing procedure request ... 💉🏥🩹")
    logger.info("Loading Procedure Collections ...")

    embedding_client = AutoModel.from_pretrained(
        "jinaai/jina-embeddings-v3", trust_remote_code=True
    )
    try:
        qdrant_client, collection = connect_qdrant(embedding_client)
    except Exception as e:
        try:
            import os
            import shutil
            import subprocess

            cli_dir = os.path.dirname(
                shutil.which("docker") or "/opt/homebrew/bin/docker"
            )
            os.environ["PATH"] += os.pathsep + cli_dir

            # Try to start Qdrant server
            _ = subprocess.run(
                [
                    "docker",
                    "run",
                    "-p",
                    "6333:6333",
                    "-p",
                    "6334:6334",
                    "-e",
                    "QDRANT__TELEMETRY_DISABLED=true",
                    "-v",
                    f"{QDRANT_STORAGE_DIR}:/qdrant/storage:z",
                    "-d",  # Run container in background
                    "qdrant/qdrant",
                ]
            )
            logger.info("Waiting for 10 seconds for Qdrant server to start ...")
            time.sleep(10)

            qdrant_client, collection = connect_qdrant(embedding_client)

        except Exception as e:
            logger.error(
                f"""Error loading procedure collection: {e}.
                Make sure to run
                    
                    `docker run -p 6333:6333 -p 6334:6334 -e QDRANT__TELEMETRY_DISABLED=true -v {QDRANT_STORAGE_DIR}:/qdrant/storage:z qdrant/qdrant`
                
                to start the Qdrant server on port 6333."""
            )
            raise e

    # Create ProcedureRequestFHIR instance
    procedure_request = ProcedureSearch(
        procedure=procedure,
        # procedure_extended=procedure_extended,
        patient_id=patient_id,
        practitioner_id=practitioner_id,
        organization_id=organization_id,
    )
    # print(colored(f"Procedure Request: {procedure_request}", "yellow"))

    # Create ProcedureRequestHandler instance
    procedure_handler = ProcedureSearchRequestHandler(
        request=procedure_request,
        patient_data=patient_data,
        collection=collection,
    )
    # print(colored(f"Procedure Handler: {procedure_handler}", "yellow"))

    # Call the asynchronous request_fetch_and_poll function
    notes = await request_fetch_and_poll(
        patient_id=patient_id,
        patient_hadm_id=patient_hadm_id,
        handlers=[procedure_handler],
        organization_id=organization_id,
        headersList=headersList,
        session=session,
    )

    # display_notes = "**Processing procedure request ... 💉🏥🩹**\n\n" + notes
    # display_action(display_notes, "get_procedure_results")
    # print(colored(notes, "cyan"))
    return notes


async def get_procedure_request_results(
    patient_id: str,
    patient_hadm_id: str,
    organization_id: str,
    practitioner_id: str,
    session: requests.Session,
    headersList: Dict[str, str],
    procedure: str,
    # procedure_extended: str,
    patient_data: pd.DataFrame,
    **kwargs,  # catch unused arguments
) -> str:
    """
    Processes procedure requests for a patient.

    Returns:
        str: Concatenated notes from all reports.
    """

    logger.info("Processing procedure request ... 💉🏥🩹")
    logger.info("Loading Procedure Collections ...")

    # Create ProcedureRequestFHIR instance
    procedure_request_fhir = ProcedureRequestFHIR(
        procedure=procedure,
        # procedure_extended=procedure_extended,
        patient_id=patient_id,
        practitioner_id=practitioner_id,
        organization_id=organization_id,
    )

    # print(colored(f"Procedure Request FHIR: {procedure_request_fhir}", "cyan"))

    # Create ProcedureRequestHandler instance
    procedure_handler = ProcedureRequestHandler(
        request=procedure_request_fhir,
        patient_data=patient_data,
        collection=None,
    )

    # print(colored(f"Procedure Handler: {procedure_handler}", "cyan"))

    # Call the asynchronous request_fetch_and_poll function
    notes = await request_fetch_and_poll(
        patient_id=patient_id,
        patient_hadm_id=patient_hadm_id,
        handlers=[procedure_handler],
        organization_id=organization_id,
        headersList=headersList,
        session=session,
    )

    # print(colored(notes, "cyan"))

    return notes


# @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=15))
def generate_routine(tools, patient_info, **kwargs):
    """
    Generates a routine for a patient based on the provided tools and patient information.
    """

    from dotenv import load_dotenv
    from openai import OpenAI
    from routines import ROUTINE_PROMPT

    load_dotenv()
    client = OpenAI()

    try:
        messages = [
            {
                "role": "user",
                "content": f"""
                    {ROUTINE_PROMPT}

                    Available Tools and options:
                    {tools}

                    The patient information so far:
                    {patient_info}
                    """,
            }
        ]

        response = client.chat.completions.create(
            model=REASONING_MODEL, messages=messages
        )
        output = response.choices[0].message.content

        return output

    except Exception as e:
        print(f"An error occurred: {e}")
        raise Exception("Could not generate a plan for the patient. Exiting.")


def generate_routine_optional_admission(tools, patient_info, **kwargs):
    """
    Generates a routine for a patient based on the provided tools and patient information.
    """

    from dotenv import load_dotenv
    from openai import OpenAI
    from routines_optional_admission import ROUTINE_PROMPT

    load_dotenv()
    client = OpenAI()

    try:
        messages = [
            {
                "role": "user",
                "content": f"""
                    {ROUTINE_PROMPT}

                    Available Tools and options:
                    {tools}

                    The patient information so far:
                    {patient_info}
                    """,
            }
        ]

        response = client.chat.completions.create(
            model=REASONING_MODEL, messages=messages
        )
        output = response.choices[0].message.content

        return output

    except Exception as e:
        print(f"An error occurred: {e}")
        raise Exception("Could not generate a plan for the patient. Exiting.")


def finish(**kwargs):
    """Finishes the patient case by sending the patient to the in-hospital admission department or discharging them."""
    return kwargs["diagnosis"]


def close_case(**kwargs):
    """Closes the patient case by sending the patient to the in-hospital admission department or discharging them."""
    return kwargs


def patient_history(**kwargs):
    """Lookup available information about the patient history from previous visits or from external sources."""

    with open(PANCREATIC_CANCER_INFO_PATH, mode="r") as f:
        patient_infos = json.load(f)

    hadm_id = kwargs["patient_hadm_id"]
    existing_patient_info = patient_infos[str(hadm_id)]

    admission_reason = existing_patient_info["admission_reason"]
    existing_info = existing_patient_info["existing_info"]
    diagnosis_status = existing_patient_info["has_diagnosis"]["diagnosis_status"]
    if diagnosis_status:
        external_staging = existing_patient_info["has_diagnosis"]["external_staging"]
    else:
        external_staging = None
    if external_staging:
        external_staging_str = "\n".join(
            [
                f"{imaging['imaging_type']} scan in the {imaging['region']} region: {imaging['result']}"
                for imaging in external_staging
            ]
        )
    else:
        external_staging_str = "No external staging information available."

    additional_patient_info = f"\n\nThe reason for the current hospital admission: {admission_reason}\nThe existing information on the patient from previous visits: {existing_info}\nThe external staging information: {external_staging_str}"

    return additional_patient_info


async def get_vitalsign_results(
    patient_id: str,
    patient_hadm_id: str,
    organization_id: str,
    practitioner_id: str,
    session: requests.Session,
    headersList: Dict[str, str],
    patient_data: pd.DataFrame,
    **kwargs,  # catch unused arguments
) -> str:
    """
    Processes physical examination requests for a patient.

    Args:
        patient_id (str): The ID of the patient.
        organization_id (str): The ID of the organization.
        practitioner_id (str): The ID of the practitioner.
        session (requests.Session): The HTTP session with retry logic.
        headersList (Dict[str, str]): The headers for HTTP requests.
        patient_data (pd.DataFrame): The DataFrame containing patient data.

    Returns:
        str: Concatenated notes from all observations.
    """

    logger.info("Requesting vitalsigns data ... 🩺🩺🩺")

    patient_data_table = patient_data.triage  # not vitalsigns table!

    # Create PhysicalExamRequestFHIR instances
    pe_request_fhir = VitalSignsRequestFHIR(
        patient_id=patient_id,
        practitioner_id=practitioner_id,
        organization_id=organization_id,
    )

    # Create VitalSignRequestHandler instances
    pe_handler = VitalSignRequestHandler(
        request=pe_request_fhir,
        patient_data=patient_data_table,
    )
    # Call the asynchronous request_and_poll function
    notes = await request_fetch_and_poll(
        patient_id=patient_id,
        patient_hadm_id=patient_hadm_id,
        handlers=[pe_handler],
        organization_id=organization_id,
        headersList=headersList,
        session=session,
    )

    return notes
