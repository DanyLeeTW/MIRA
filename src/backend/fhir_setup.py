import random
import uuid
from datetime import date, timedelta
from typing import Dict, List

import pandas as pd
from fhir.resources.organization import Organization
from fhir.resources.patient import Patient
from fhir.resources.practitioner import Practitioner

from .fhir_client import post_fhir_resource
from .log import logger


def generate_patient_resource(row: pd.Series, practitioner_id: str) -> Patient:
    """Generates a Patient FHIR resource from a MIMIC row and associates it with a Practitioner

    Args:
        row (pd.Series): A row from the MIMIC dataset
        practitioner_id (str): The ID of the Practitioner to associate with the Patient

    Returns:
        Patient: A FHIR Patient resource
    """
    subject_id = "Patient-" + str(row["subject_id"].values[0])
    gender = row["gender"].values[0]

    match gender:
        case "M":
            gender = "male"
        case "F":
            gender = "female"
        case _:
            gender = "unknown"

    birth_year = row["anchor_year"].values[0] - row["anchor_age"].values[0]
    birth_date = date(birth_year, 1, 1) + timedelta(days=random.randint(0, 364))

    json_obj = {
        "resourceType": "Patient",
        "id": str(subject_id),
        "active": True,
        "gender": gender.strip(),
        "name": [{"text": f"Patient_{subject_id}"}],
        "birthDate": birth_date.isoformat(),
        "generalPractitioner": [
            {
                "reference": f"Practitioner/{practitioner_id}",
                "display": "GPT-4o OpenAI",
            }
        ],
    }

    patient = Patient(**json_obj)
    return patient


def generate_organization_resource(name: str = "LLM FHIR Hospital") -> Organization:
    """Generates an Organization FHIR resource."""

    json_obj = {
        "resourceType": "Organization",
        "id": str(uuid.uuid4()),
        "active": True,
        "name": name,
    }

    organization = Organization(**json_obj)
    return organization


def generate_practitioner_resource(
    first_name: str = "MIRA",
    last_name: str = "AI",
    gender: str = "female",
    organization: Organization | None = None,
) -> Practitioner:
    """
    Generates a Practitioner FHIR resource.

    Args:
        first_name (str): First name of the practitioner.
        last_name (str): Last name of the practitioner.
        gender (str): Gender of the practitioner ('male', 'female', 'other', 'unknown').
        organization (Organization): The Organization resource the Practitioner belongs to.

    Returns:
        Practitioner: A FHIR Practitioner resource.
    """

    birth_year = 2024
    birth_date = date(birth_year, 1, 1)

    # Construct the Practitioner JSON object
    json_obj = {
        "resourceType": "Practitioner",
        "active": True,
        "gender": gender,
        "name": [{"use": "official", "family": last_name, "given": [first_name]}],
        "birthDate": birth_date.isoformat(),
        "qualification": [
            {
                "identifier": [
                    {
                        "system": "http://hl7.org/fhir/sid/us-npi",
                        "value": str(random.randint(1000000000, 9999999999)),
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0360",
                            "code": "MD",
                            "display": "Medical Super AI",
                        }
                    ],
                    "text": "Medical Super AI",
                },
                "period": {"start": "2010-01-01"},
                "issuer": {
                    "reference": f"Organization/{organization.id}",
                    "display": organization.name,
                },
            }
        ],
        "communication": [
            {
                "language": {
                    "coding": [
                        {
                            "system": "urn:ietf:bcp:47",  # see https://build.fhir.org/ig/IHE-Germany/ITI.XDS.VS/ValueSet-IHEXDSlanguageCode.html
                            "code": "en",
                            "display": "English",
                        }
                    ],
                    "text": "English",
                }
            }
        ],
    }

    practitioner = Practitioner(**json_obj)
    return practitioner


def setup_org_and_practitioner(
    organization_name: str = "LLM AI Hospital",
    practicioner_first_name: str = "GPT-4o",
    practicioner_last_name: str = "OpenAI",
    base_url: str | None = None,
    headers_list: Dict[str, str] | None = None,
    session=None,
):
    # set up resources for hospital and AI doctor
    organization = generate_organization_resource(name=organization_name)
    practitioner = generate_practitioner_resource(
        first_name=practicioner_first_name,
        last_name=practicioner_last_name,
        organization=organization,
    )

    # post resources to server
    organization_id = post_fhir_resource(
        organization, base_url=base_url, headers=headers_list, session=session
    )
    practitioner_id = post_fhir_resource(
        practitioner, base_url=base_url, headers=headers_list, session=session
    )

    logger.info(f"Created Organization with ID: {organization_id}")
    logger.info(f"Created Practitioner with ID: {practitioner_id}")

    return organization_id, practitioner_id


# helper functions
def get_patient_reference(patient_id: str) -> str:
    """Constructs a FHIR reference for a Patient."""
    if not patient_id or not isinstance(patient_id, str):
        raise ValueError("Invalid patient_id provided.")
    return f"Patient/{patient_id}"


def get_practitioner_reference(practitioner_id: str) -> str:
    """Constructs a FHIR reference for a Practitioner."""
    if not practitioner_id or not isinstance(practitioner_id, str):
        raise ValueError("Invalid practitioner_id provided.")
    return f"Practitioner/{practitioner_id}"


def get_performer_reference(organization_id: str) -> str:
    """Constructs a FHIR reference for an Organization."""
    if not organization_id or not isinstance(organization_id, str):
        raise ValueError("Invalid organization_id provided.")
    return f"Organization/{organization_id}"
