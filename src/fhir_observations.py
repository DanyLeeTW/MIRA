# mypy: ignore-errors

import base64
import uuid
from datetime import datetime
from typing import Any, List, Optional, Union

import pandas as pd
from fhir.resources.annotation import Annotation
from fhir.resources.attachment import Attachment
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.diagnosticreport import DiagnosticReport
from fhir.resources.fhirtypes import DateTime
from fhir.resources.observation import Observation
from fhir.resources.procedure import Procedure, ProcedurePerformer
from fhir.resources.quantity import Quantity
from fhir.resources.reference import Reference
from mimic_to_fhir import VS_METADATA
from tools import (
    LabRequestFHIR,
    MedicationRequestFHIR,
    MicrobiologyRequestFHIR,
    PhysicalExamRequestFHIR,
    ProcedureRequestFHIR,
    RadiologyRequestFHIR,
    UrineRequestFHIR,
    VitalSigns,
)


def valid(item):
    # check if item is not NaN and not "___"
    return pd.notna(item) and item != "___"


def _extract_procedure_payload(result: Optional[Any]) -> Optional[dict]:
    if result is None:
        return None

    points = getattr(result, "points", None)
    if points:
        payload = getattr(points[0], "payload", None)
        if isinstance(payload, dict):
            return payload

    if isinstance(result, dict):
        if isinstance(result.get("payload"), dict):
            return result["payload"]
        if "icd_code" in result:
            return result

    if isinstance(result, list) and result:
        first = result[0]
        if isinstance(first, dict):
            if isinstance(first.get("payload"), dict):
                return first["payload"]
            if "icd_code" in first:
                return first

    return None


def _build_procedure_code(
    procedure_text: str, payload: Optional[dict]
) -> CodeableConcept:
    if payload is None:
        return CodeableConcept(text=procedure_text)

    code = payload.get("icd_code")
    display = payload.get("long_title") or procedure_text
    icd_version = payload.get("icd_version")
    if code is None:
        return CodeableConcept(text=display)

    if str(icd_version) == "10":
        system = "http://www.cms.gov/Medicare/Coding/ICD10"
    elif str(icd_version) == "9":
        system = "http://hl7.org/fhir/sid/icd-9-cm"
    else:
        system = (
            "https://www.who.int/standards/classifications/classification-of-diseases"
        )

    return CodeableConcept(
        coding=[Coding(system=system, code=str(code), display=display)],
        text=display,
    )


def generate_urine_observation_resource(
    urine_request: UrineRequestFHIR,
    result: Union[pd.Series, None],
    patient_id: str,
    service_request_id: str,
    organization_id: str,
) -> Observation:
    """
    Generates an Observation FHIR resource from a urine result.

    Args:
        result (pd.Series | None): The urine result data or None if not available.
        patient_id (str): The ID of the patient.
        service_request_id (str): The ID of the originating ServiceRequest.
        organization_id (str): The ID of the Organization.

    Returns:
        Observation: The generated Observation resource.

    Raises:
        ValueError: If the lab result does not match the requested lab value.
    """

    observation_id = str(uuid.uuid4())

    if result is None:
        llm_input = f"{urine_request.urine_value.value}: N/A\n"
        json_obj = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "laboratory",
                            "display": "Laboratory",
                        }
                    ],
                    "text": "Laboratory",
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems",
                        "code": urine_request._urine_value_loinc_code,
                        "display": f"LOINC Code: {urine_request._urine_value_loinc_code}",
                    },
                    {
                        "system": "https://fhir-terminology.ohdsi.org",
                        "code": urine_request._urine_value_omop_concept_code,
                        "display": f"OMOP Concept Code: {urine_request._urine_value_omop_concept_code}",
                    },
                ]
            },
            "subject": {
                "reference": f"Patient/{patient_id}",
                "display": f"Patient ID: {patient_id}",
            },
            "effectiveDateTime": datetime.now().isoformat(),
            "issued": datetime.now().isoformat() + "Z",
            "performer": [
                {
                    "reference": f"Organization/{organization_id}",
                    "display": "LLM FHIR Hospital",
                }
            ],
            "basedOn": [
                {
                    "reference": f"ServiceRequest/{service_request_id}",
                }
            ],
            "dataAbsentReason": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/data-absent-reason",
                        "code": "unknown",
                        "display": "unknown",
                    }
                ],
                "text": "Lab result not available.",
            },
            "note": [{"text": llm_input}],
        }
    else:
        # fallback in case the values from the dataset tables are available but invalid (converted to "___" or else)

        value = pd.NA
        if valid(result["valuenum"]) and isinstance(
            result["valuenum"], (int, float, str)
        ):
            try:
                value = float(result["valuenum"])
            except ValueError:
                value = pd.NA

        elif valid(result["value"]) and isinstance(result["value"], str):
            try:
                value = float(result["value"])
            except ValueError:
                value = pd.NA

        elif valid(result["flag"]) and isinstance(result["flag"], str):
            # Usually flags are not numeric, so likely pd.NA here
            value = result["flag"]

        if pd.isna(value):
            if valid(result["valuenum"]):
                new_value = result["valuenum"]
            elif valid(result["value"]):
                new_value = result["value"]
                if new_value == "None":
                    new_value = result["flag"] if valid(result["flag"]) else "N/A"
            elif valid(result["flag"]):
                new_value = result["flag"]
            else:
                new_value = "N/A"  # Fallback to pd.NA if all fields are invalid

            llm_input = f"{result['label']}: {new_value}\n"
            json_obj = {
                "resourceType": "Observation",
                "id": observation_id,
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "laboratory",
                                "display": "Laboratory",
                            }
                        ],
                        "text": "Laboratory",
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems",
                            "code": str(
                                result["itemid"]
                            ),  # LOINC code from the dataset
                            "display": f"LOINC Code: {result['itemid']}",
                        },
                        {
                            "system": "https://fhir-terminology.ohdsi.org",
                            "code": str(
                                result["omop_concept_code"]
                            ),  # OMOP Concept Code
                            "display": f"OMOP Concept Code: {result['omop_concept_code']}",
                        },
                    ]
                },
                "subject": {
                    "reference": f"Patient/{patient_id}",
                    "display": f"Patient ID: {patient_id}",
                },
                "effectiveDateTime": result["charttime"].isoformat(),
                "issued": result["charttime"].isoformat() + "Z",
                "performer": [
                    {
                        "reference": f"Organization/{organization_id}",
                        "display": "LLM FHIR Hospital",
                    }
                ],
                "basedOn": [
                    {
                        "reference": f"ServiceRequest/{service_request_id}",
                    }
                ],
                "dataAbsentReason": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/data-absent-reason",
                            "code": "invalid",
                            "display": "Invalid",
                        }
                    ],
                    "text": "Lab result data is invalid.",
                },
                "note": [{"text": llm_input}],
            }
        else:
            llm_input = f"{result['label']}: {value} {result['valueuom_x']} ({result['ref_range_lower']} - {result['ref_range_upper']})\n"
            json_obj = {
                "resourceType": "Observation",
                "id": observation_id,
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "laboratory",
                                "display": "Laboratory",
                            }
                        ],
                        "text": "Laboratory",
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems",
                            "code": str(
                                result["itemid"]
                            ),  # LOINC code from the dataset
                            "display": f"LOINC Code: {result['itemid']}",
                        },
                        {
                            "system": "https://fhir-terminology.ohdsi.org",
                            "code": str(
                                result["omop_concept_code"]
                            ),  # OMOP Concept Code
                            "display": f"OMOP Concept Code: {result['omop_concept_code']}",
                        },
                    ]
                },
                "subject": {
                    "reference": f"Patient/{patient_id}",
                    "display": f"Patient ID: {patient_id}",
                },
                "effectiveDateTime": result["charttime"].isoformat(),
                "issued": result["charttime"].isoformat() + "Z",
                "valueQuantity": {
                    "value": value,
                    "unit": result["valueuom_x"],
                    "system": "http://unitsofmeasure.org",
                    "code": str(result["itemid"]),
                },
                "performer": [
                    {
                        "reference": f"Organization/{organization_id}",
                        "display": "LLM FHIR Hospital",
                    }
                ],
                "basedOn": [
                    {
                        "reference": f"ServiceRequest/{service_request_id}",
                    }
                ],
                "note": [{"text": llm_input}],
            }

    # Add 'note' only if llm_input is not None
    # if llm_input:
    #     json_obj["note"] = [{"text": llm_input}]

    observation = Observation(**json_obj)  # type: ignore
    return observation


def generate_lab_observation_resource(
    lab_request: LabRequestFHIR,
    result: Union[pd.Series, None],
    patient_id: str,
    service_request_id: str,
    organization_id: str,
) -> Observation:
    """
    Generates an Observation FHIR resource from a lab result.

    Args:
        result (pd.Series | None): The lab result data or None if not available.
        patient_id (str): The ID of the patient.
        service_request_id (str): The ID of the originating ServiceRequest.
        organization_id (str): The ID of the Organization.

    Returns:
        Observation: The generated Observation resource.

    Raises:
        ValueError: If the lab result does not match the requested lab value.
    """

    observation_id = str(uuid.uuid4())

    if result is None:
        llm_input = f"{lab_request.lab_value.value}: N/A\n"
        json_obj = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "laboratory",
                            "display": "Laboratory",
                        }
                    ],
                    "text": "Laboratory",
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems",
                        "code": lab_request._lab_value_loinc_code,
                        "display": f"LOINC Code: {lab_request._lab_value_loinc_code}",
                    },
                    {
                        "system": "https://fhir-terminology.ohdsi.org",
                        "code": lab_request._lab_value_omop_concept_code,
                        "display": f"OMOP Concept Code: {lab_request._lab_value_omop_concept_code}",
                    },
                ]
            },
            "subject": {
                "reference": f"Patient/{patient_id}",
                "display": f"Patient ID: {patient_id}",
            },
            "effectiveDateTime": datetime.now().isoformat(),
            "issued": datetime.now().isoformat() + "Z",
            "performer": [
                {
                    "reference": f"Organization/{organization_id}",
                    "display": "LLM FHIR Hospital",
                }
            ],
            "basedOn": [
                {
                    "reference": f"ServiceRequest/{service_request_id}",
                }
            ],
            "dataAbsentReason": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/data-absent-reason",
                        "code": "unknown",
                        "display": "unknown",
                    }
                ],
                "text": "Lab result not available.",
            },
            "note": [{"text": llm_input}],
        }
    else:
        if valid(result["valuenum"]):
            value = result["valuenum"]
        elif valid(result["value"]):
            value = result["value"]
        elif valid(result["flag"]):
            value = result["flag"]
        else:
            value = pd.NA  # Fallback to pd.NA if all fields are invalid

        if pd.isna(value):
            llm_input = f"{result['label']}: N/A"
            json_obj = {
                "resourceType": "Observation",
                "id": observation_id,
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "laboratory",
                                "display": "Laboratory",
                            }
                        ],
                        "text": "Laboratory",
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems",
                            "code": str(
                                result["itemid"]
                            ),  # LOINC code from the dataset
                            "display": f"LOINC Code: {result['itemid']}",
                        },
                        {
                            "system": "https://fhir-terminology.ohdsi.org",
                            "code": str(
                                result["omop_concept_code"]
                            ),  # OMOP Concept Code
                            "display": f"OMOP Concept Code: {result['omop_concept_code']}",
                        },
                    ]
                },
                "subject": {
                    "reference": f"Patient/{patient_id}",
                    "display": f"Patient ID: {patient_id}",
                },
                "effectiveDateTime": result["charttime"].isoformat(),
                "issued": result["charttime"].isoformat() + "Z",
                "performer": [
                    {
                        "reference": f"Organization/{organization_id}",
                        "display": "LLM FHIR Hospital",
                    }
                ],
                "basedOn": [
                    {
                        "reference": f"ServiceRequest/{service_request_id}",
                    }
                ],
                "dataAbsentReason": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/data-absent-reason",
                            "code": "invalid",
                            "display": "Invalid",
                        }
                    ],
                    "text": "Lab result data is invalid.",
                },
                "note": [{"text": llm_input}],
            }
        else:
            # if all fields are valid, we return the lab result
            llm_input = f"{result['label']}: {value} {result['valueuom_x']} ({result['ref_range_lower']} - {result['ref_range_upper']})\n"

            json_obj = {
                "resourceType": "Observation",
                "id": observation_id,
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "laboratory",
                                "display": "Laboratory",
                            }
                        ],
                        "text": "Laboratory",
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems",
                            "code": str(
                                result["itemid"]
                            ),  # LOINC code from the dataset
                            "display": f"LOINC Code: {result['itemid']}",
                        },
                        {
                            "system": "https://fhir-terminology.ohdsi.org",
                            "code": str(
                                result["omop_concept_code"]
                            ),  # OMOP Concept Code
                            "display": f"OMOP Concept Code: {result['omop_concept_code']}",
                        },
                    ]
                },
                "subject": {
                    "reference": f"Patient/{patient_id}",
                    "display": f"Patient ID: {patient_id}",
                },
                "effectiveDateTime": result["charttime"].isoformat(),
                "issued": result["charttime"].isoformat() + "Z",
                "valueQuantity": {
                    "value": value,
                    "unit": result["valueuom_x"],
                    "system": "http://unitsofmeasure.org",
                    "code": str(result["itemid"]),
                },
                "performer": [
                    {
                        "reference": f"Organization/{organization_id}",
                        "display": "LLM FHIR Hospital",
                    }
                ],
                "basedOn": [
                    {
                        "reference": f"ServiceRequest/{service_request_id}",
                    }
                ],
                "note": [{"text": llm_input}],
            }

    # Add 'note' only if llm_input is not None
    # if llm_input:
    #     json_obj["note"] = [{"text": llm_input}]

    observation = Observation(**json_obj)  # type: ignore
    return observation


def generate_medication_observation_resource(
    medication_request: MedicationRequestFHIR,
    result: Optional[pd.Series],
    patient_id: str,
    service_request_id: str,
    organization_id: str,
) -> Observation:
    """
    Generates an Observation FHIR resource from a medication result.

    Args:
        medication_request (MedicationRequestFHIR): The medication request object.
        result (pd.Series | None): The medication result data or None if not available.
        patient_id (str): The ID of the patient.
        service_request_id (str): The ID of the originating ServiceRequest.
        organization_id (str): The ID of the Organization.

    Returns:
        Observation: The generated Observation resource.
    """

    observation_id = str(uuid.uuid4())

    llm_input = f"""
        {result["drug_name"]}: {result["dosage_text"]} {result["dosage_value"]} {result["dosage_unit"]}, {result["frequency"]} x {result["period"]}{result["period_unit"].name}, {result["route"].value}\n 
    """
    llm_input = str(llm_input).strip()
    llm_input = llm_input + "\n"

    try:
        dosage_value = float(result["dosage_value"])  # type: ignore
    except (ValueError, TypeError):
        dosage_value = None

    dosage_unit = str(result["dosage_unit"]).strip() if result["dosage_unit"] else None  # type: ignore
    medication_codings = []

    def _append_codes(system: str, raw_codes: Optional[str]):
        if raw_codes is None:
            return
        for code in str(raw_codes).split(";"):
            normalized = code.strip()
            if normalized:
                medication_codings.append(
                    {
                        "system": system,
                        "code": normalized,
                        "display": medication_request.drug_name,
                    }
                )

    _append_codes(
        "http://hl7.org/fhir/sid/ndc", medication_request._medication_codes.get("ndc")
    )
    _append_codes(
        "http://www.nlm.nih.gov/research/umls/rxnorm",
        medication_request._medication_codes.get("rxnorm_code"),
    )
    _append_codes(
        "http://snomed.info/sct",
        medication_request._medication_codes.get("snomed_ct_code"),
    )
    _append_codes(
        "http://www.whocc.no/atc",
        medication_request._medication_codes.get("atc_codes"),
    )

    json_obj = {
        "resourceType": "Observation",
        "id": observation_id,
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "medication",
                        "display": "Medication",
                    }
                ],
                "text": "Medication",
            }
        ],
        "code": {
            "coding": medication_codings,
            "text": medication_request.drug_name,
        },
        "subject": {
            "reference": f"Patient/{patient_id}",
            "display": f"Patient ID: {patient_id}",
        },
        "effectiveDateTime": result["issued"].isoformat(),
        "issued": result["issued"].isoformat() + "Z",
        "valueQuantity": {
            "value": dosage_value,
            "unit": dosage_unit,
            "system": "http://unitsofmeasure.org",
            "code": dosage_unit,
        },
        "performer": [
            {
                "reference": f"Organization/{organization_id}",
                "display": "LLM FHIR Hospital",
            }
        ],
        "basedOn": [
            {
                "reference": f"MedicationRequest/{service_request_id}",
            }
        ],
        "note": [{"text": llm_input}],
    }

    if llm_input:
        json_obj["note"] = [{"text": llm_input}]

    observation = Observation(**json_obj)
    return observation


def generate_pe_observation_resource(
    pe_request: PhysicalExamRequestFHIR,
    result: Optional[str],  # or None
    patient_id: str,
    service_request_id: str,
    organization_id: str,
) -> Observation:
    """
    Generates an Observation FHIR resource from physical examination data.

    Args:
        pe_request (PhysicalExamRequestFHIR): The physical examination request object.
        result (Optional[str]): The physical examination data or None if not available.
        patient_id (str): The ID of the patient.
        service_request_id (str): The ID of the originating ServiceRequest.
        organization_id (str): The ID of the Organization.

    Returns:
        Observation: The generated Observation resource.
    """
    observation_id = str(uuid.uuid4())

    if result is None:
        llm_input = "Physical Examination:\n    Phyical Examination not available."

        json_obj = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "exam",
                            "display": "Examination",
                        }
                    ],
                    "text": "Physical Examination",
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://mimic.mit.edu/fhir/mimic/CodeSystem/physical-exam-codes",
                        "code": pe_request._pe_code,
                        "display": "Physical Examination",
                    }
                ]
            },
            "subject": {
                "reference": f"Patient/{patient_id}",
                "display": f"Patient ID: {patient_id}",
            },
            "effectiveDateTime": datetime.now().isoformat(),
            "issued": datetime.now().isoformat() + "Z",
            "performer": [
                {
                    "reference": f"Organization/{organization_id}",
                    "display": "LLM FHIR Hospital",
                }
            ],
            "basedOn": [
                {
                    "reference": f"ServiceRequest/{service_request_id}",
                }
            ],
            "dataAbsentReason": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/data-absent-reason",
                        "code": "unknown",
                        "display": "unknown",
                    }
                ],
                "text": "Physical examination data not available.",
            },
            "note": [{"text": llm_input}],  # To be sent to the LLM
        }
    else:
        # Physical examination data is available
        llm_input = f"Physical Examination:\n   {result}"

        json_obj = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "exam",
                            "display": "Examination",
                        }
                    ],
                    "text": "Physical Examination",
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://mimic.mit.edu/fhir/mimic/CodeSystem/physical-exam-codes",
                        "code": pe_request._pe_code,
                        "display": "Physical Examination",
                    }
                ]
            },
            "subject": {
                "reference": f"Patient/{patient_id}",
                "display": f"Patient ID: {patient_id}",
            },
            "effectiveDateTime": datetime.now().isoformat(),
            "issued": datetime.now().isoformat() + "Z",
            "valueString": result,  # the result of the physcial examination
            "performer": [
                {
                    "reference": f"Organization/{organization_id}",
                    "display": "LLM FHIR Hospital",
                }
            ],
            "basedOn": [
                {
                    "reference": f"ServiceRequest/{service_request_id}",
                }
            ],
            "note": [{"text": llm_input}],  # input to the LLM
        }

    json_obj["note"] = [{"text": llm_input}]

    observation = Observation(**json_obj)  # type: ignore
    return observation


def generate_micro_test_observation_resource(
    microbiology_request: MicrobiologyRequestFHIR,
    result: Union[pd.Series, None],
    patient_id: str,
    service_request_id: str,
    organization_id: str,
) -> Observation:
    """
    Generates an ObservationMicroTest FHIR resource from a microbiologyevents row.

    Args:
        result (pd.Series | None): The microbiolgoy result data or None if not available.
        patient_id (str): The ID of the patient.
        service_request_id (str): The ID of the originating ServiceRequest.
        organization_id (str): The ID of the Organization performing the request.

    Returns:
        Observation: The generated Observation resource.
    """
    observation_id = str(uuid.uuid4())
    microbiology_codings = [
        {
            "system": "http://mimic.mit.edu/fhir/mimic/CodeSystem/microbiology-test-itemid",
            "code": microbiology_request._microbiology_test_itemid_code,
            "display": microbiology_request.microbiology_value.value,
        }
    ]

    if result is None:
        llm_input = f"{microbiology_request.microbiology_value.value}: N/A\n"
        json_obj = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "microbiology",
                            "display": "Microbiology",
                        }
                    ],
                    "text": "Microbiology",
                }
            ],
            "code": {"coding": microbiology_codings},
            "subject": {
                "reference": f"Patient/{patient_id}",
                "display": f"Patient ID: {patient_id}",
            },
            "effectiveDateTime": datetime.now().isoformat(),
            "issued": datetime.now().isoformat() + "Z",
            "performer": [
                {
                    "reference": f"Organization/{organization_id}",
                    "display": "LLM FHIR Hospital",
                }
            ],
            "dataAbsentReason": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/data-absent-reason",
                        "code": "unknown",
                        "display": "unknown",
                    }
                ],
                "text": "Microbiology result not available.",
            },
            "basedOn": [
                {
                    "reference": f"ServiceRequest/{service_request_id}",
                }
            ],
            "valueString": llm_input,
            "note": [{"text": llm_input}],
        }
    else:
        # we might have data from the same micro_specimen_id but over different times
        ## first blood culture result just shows bacteria
        ## second one shows resistance testing etc ...
        ## -> merge them together

        result_str = result["grouped_microbio_str"].unique()[0]
        llm_input = (
            f"""{microbiology_request.microbiology_value.value}:\n  {result_str}"""
        )

        json_obj = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "microbiology",
                            "display": "Microbiology",
                        }
                    ],
                    "text": "Microbiology",
                }
            ],
            "code": {"coding": microbiology_codings},
            "subject": {
                "reference": f"Patient/{patient_id}",
                "display": f"Patient ID: {patient_id}",
            },
            "effectiveDateTime": datetime.now().isoformat(),
            "issued": datetime.now().isoformat() + "Z",
            "performer": [
                {
                    "reference": f"Organization/{organization_id}",
                    "display": "LLM FHIR Hospital",
                }
            ],
            "basedOn": [
                {
                    "reference": f"ServiceRequest/{service_request_id}",
                }
            ],
            "valueString": llm_input,
            "note": [{"text": llm_input}],  # inpu to the LLM
        }
    # Create the Observation resource
    observation = Observation(**json_obj)  # type: ignore

    return observation


def generate_micro_org_observation_resource(
    microbiology_request: MicrobiologyRequestFHIR,
    result: pd.Series,
    patient_id: str,
    parent_observation_id: str,
    organization_id: str,
) -> Observation:
    """
    Generates a MimicObservationMicroOrg FHIR resource from a microbiology organism result.

    Args:
        microbiology_request (MicrobiologyRequestFHIR): The microbiology test request object.
        result (pd.Series): The microbiology organism result data.
        patient_id (str): The ID of the patient.
        parent_observation_id (str): The ID of the parent Microbiology Test Observation.
        organization_id (str): The ID of the Organization.

    Returns:
        Observation: The generated MimicObservationMicroOrg resource.
    """

    _ = microbiology_request
    # try:
    #     org_id = int(result.get("org_itemid", "unknown"))
    # except:
    org_id = (
        str(result["org_itemid"].unique()[0])
        if pd.notna(result["org_itemid"].unique()[0])
        else "Unknown Organism"
    )
    org_name = (
        str(result["org_name"].unique()[0])
        if pd.notna(result["org_name"].unique()[0])
        else "Unknown Organism"
    )

    observation_id = str(uuid.uuid4())

    observation = Observation(
        resource_type="Observation",
        id=observation_id,
        status="final",
        category=[
            CodeableConcept(
                coding=[
                    Coding(
                        system="http://terminology.hl7.org/CodeSystem/observation-category",
                        code="microbiology",
                        display="Microbiology",
                    )
                ],
                text="Microbiology",
            )
        ],
        code=CodeableConcept(
            coding=[
                Coding(
                    system="http://mimic.mit.edu/fhir/mimic/CodeSystem/microbiology-organism-codes",
                    code=org_id,
                    display=org_name,
                ),
            ],
            text="Microbiology Organism",
        ),
        subject=Reference(
            reference=f"Patient/{patient_id}",
            display=f"Patient ID: {patient_id}",
        ),
        effectiveDateTime=DateTime.validate(datetime.now().isoformat()),
        issued=DateTime.validate(datetime.now().isoformat() + "Z"),
        performer=[
            Reference(
                reference=f"Organization/{organization_id}",
                display="LLM FHIR Hospital",
            )
        ],
        derivedFrom=[
            Reference(
                reference=f"Observation/{parent_observation_id}",
            )
        ],
        valueString=org_name,
        # note=[Annotation(text="Organism observation note")], # DO NOT RETURN TO LLM
    )

    return observation


def generate_micro_susc_observation_resource(
    microbiology_request: MicrobiologyRequestFHIR,
    antibiotic_result: dict,
    patient_id: str,
    parent_observation_id: str,
    organization_id: str,
) -> Observation:
    """
    Generates a MimicObservationMicroSusc FHIR resource from a microbiology susceptibility result.

    Args:
        microbiology_request (MicrobiologyRequestFHIR): The microbiology test request object.
        antibiotic_result (dict): The antibiotic susceptibility result data.
        patient_id (str): The ID of the patient.
        parent_observation_id (str): The ID of the parent Organism Observation.
        organization_id (str): The ID of the Organization.

    Returns:
        Observation: The generated MimicObservationMicroSusc resource.
    """

    _ = microbiology_request
    try:
        ab_id = int(antibiotic_result.get("ab_itemid", "unknown"))
    except:
        ab_id = antibiotic_result.get("ab_itemid", "unknown")

    observation_id = str(uuid.uuid4())

    observation = Observation(
        resource_type="Observation",
        id=observation_id,
        status="final",
        category=[
            CodeableConcept(
                coding=[
                    Coding(
                        system="http://terminology.hl7.org/CodeSystem/observation-category",
                        code="microbiology",
                        display="Microbiology",
                    )
                ],
                text="Microbiology",
            )
        ],
        code=CodeableConcept(
            coding=[
                Coding(
                    system="http://mimic.mit.edu/fhir/mimic/CodeSystem/antibiotic-codes",
                    code=ab_id,
                    display=antibiotic_result.get("ab_name", "Unknown Antibiotic"),
                ),
            ],
            text="Antibiotic Susceptibility",
        ),
        subject=Reference(
            reference=f"Patient/{patient_id}",
            display=f"Patient ID: {patient_id}",
        ),
        effectiveDateTime=DateTime.validate(datetime.now().isoformat()),
        issued=DateTime.validate(datetime.now().isoformat() + "Z"),
        performer=[
            Reference(
                reference=f"Organization/{organization_id}",
                display="LLM FHIR Hospital",
            )
        ],
        derivedFrom=[
            Reference(
                reference=f"Observation/{parent_observation_id}",
            )
        ],
        interpretation=[
            CodeableConcept(
                coding=[
                    Coding(
                        system="http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        code=antibiotic_result.get("interpretation", "unknown"),
                        display=antibiotic_result.get("interpretation", "Unknown"),
                    )
                ]
            )
        ],
        # note=[Annotation(text="Susceptibility observation note")], # DO NOT RETURN TO LLM
    )

    return observation


def generate_microbiology_observations(
    microbiology_request: MicrobiologyRequestFHIR,
    result: Union[pd.DataFrame, None],
    patient_id: str,
    service_request_id: str,
    organization_id: str,
):
    micro_test_observation = generate_micro_test_observation_resource(
        microbiology_request, result, patient_id, service_request_id, organization_id
    )

    observations = [micro_test_observation]

    # Check if result is None or empty
    if result is None or result.empty:
        # No further observations to generate
        return observations

    # Ensure 'org_name' exists in the DataFrame
    if "org_name" not in result.columns or result["org_name"].isnull().all():
        # No organisms identified
        return observations

    micro_test_observation_has_members = []

    # Proceed to generate organism and susceptibility observations
    unique_org_names = result["org_name"].dropna().unique()
    for org_name in unique_org_names:
        org_df = result[result["org_name"] == org_name]

        # Generate microbiology organism observation resource for each unique organism
        micro_org_observation = generate_micro_org_observation_resource(
            microbiology_request,
            org_df,
            patient_id,
            micro_test_observation.id,  # Reference to the parent test observation
            organization_id,
        )
        observations.append(micro_org_observation)
        micro_test_observation_has_members.append(
            Reference(reference=f"Observation/{micro_org_observation.id}")  # type: ignore
        )

        # Collect susceptibility observation references
        micro_org_observation_has_members = []

        # Check for antibiotic susceptibility results for each organism
        for _, antibiotic_result in org_df.iterrows():
            if pd.notnull(antibiotic_result.get("ab_name")):
                micro_susc_observation = generate_micro_susc_observation_resource(
                    microbiology_request,
                    antibiotic_result,
                    patient_id,
                    micro_org_observation.id,  # Reference to the parent organism observation
                    organization_id,
                )
                observations.append(micro_susc_observation)
                micro_org_observation_has_members.append(
                    Reference(reference=f"Observation/{micro_susc_observation.id}")  # type: ignore
                )

        # Add hasMember references to the organism observation
        if micro_org_observation_has_members:
            if (
                not hasattr(micro_org_observation, "hasMember")
                or micro_org_observation.hasMember is None
            ):
                micro_org_observation.hasMember = []
            micro_org_observation.hasMember.extend(micro_org_observation_has_members)  # type: ignore

    # Add hasMember references to the microbiology test observation
    if micro_test_observation_has_members:
        if (
            not hasattr(micro_test_observation, "hasMember")
            or micro_test_observation.hasMember is None
        ):
            micro_test_observation.hasMember = []
        micro_test_observation.hasMember.extend(micro_test_observation_has_members)  # type: ignore

    return observations


def generate_radiology_report_resource(
    radiology_request: RadiologyRequestFHIR,
    result: Union[pd.Series, dict, str, None],
    patient_id: str,
    service_request_id: str,
    organization_id: str,
) -> DiagnosticReport:
    """
    Generates a DiagnosticReport FHIR resource from a radiology report.
    """
    report_id = str(uuid.uuid4())

    if result is None:
        report_text = "Radiology Report:\n    Examination could not be performed."
        study_time = datetime.now()
        status = "unknown"
        conclusion_text = "Radiology report not available."
        conclusion_code = [
            CodeableConcept(
                coding=[
                    Coding(
                        system="http://terminology.hl7.org/CodeSystem/data-absent-reason",
                        code="unknown",
                        display="Unknown",
                    )
                ],
                text="Radiology report not available.",
            )
        ]
    else:
        report_text = result.get("extracted_rad_events", "Report data is unavailable.")
        study_time = pd.to_datetime(result.get("charttime", datetime.now()))

        status = "final"
        conclusion_text = None
        conclusion_code = None

    llm_input = f"Radiology Report ({radiology_request.modality.value}\n{radiology_request.region.value}):\n\n{report_text}"
    # FHIR Attachment.data must be base64-encoded.
    llm_input_b64 = base64.b64encode(llm_input.encode("utf-8")).decode("ascii")

    diagnostic_report = DiagnosticReport(
        resourceType="DiagnosticReport",
        id=report_id,
        status=status,
        code=CodeableConcept(
            coding=[
                Coding(
                    system="http://loinc.org",
                    code=radiology_request._procedure_loinc_code or "unknown",
                    display=f"{radiology_request.modality.value} {radiology_request.region.value}",
                ),
                Coding(
                    system="http://snomed.info/sct",
                    code=radiology_request._procedure_snomed_code or "unknown",
                    display=f"{radiology_request.modality.value} {radiology_request.region.value}",
                ),
            ],
            text=f"{radiology_request.modality.value} {radiology_request.region.value}",
        ),
        subject=Reference(
            reference=f"Patient/{patient_id}",
            display=f"Patient ID: {patient_id}",
        ),
        effectiveDateTime=DateTime.validate(study_time.isoformat()),
        issued=DateTime.validate(datetime.now().isoformat() + "Z"),
        performer=[
            Reference(
                reference=f"Organization/{organization_id}",
                display="LLM FHIR Hospital",
            )
        ],
        basedOn=[
            Reference(
                reference=f"ServiceRequest/{service_request_id}",
            )
        ],
        conclusion=conclusion_text,
        conclusionCode=conclusion_code,
        presentedForm=[Attachment(contentType="text/plain", data=llm_input_b64)],
        note=[Annotation(text=llm_input)],  # Include llm_input in the note field
    )

    return diagnostic_report


def generate_procedure_search_resource(
    procedure_request: ProcedureRequestFHIR,
    result: Optional[Any],
    patient_id: str,
    service_request_id: str,
    organization_id: str,
) -> Procedure:
    """
    Generates a Procedure FHIR resource from the procedure result.

    Args:
        procedure_request (ProcedureRequestFHIR): The procedure request object.
        result (Union[List[dict], None]): The procedure options from the vector database.
        patient_id (str): The patient ID.
        service_request_id (str): The ServiceRequest ID.
        organization_id (str): The organization ID.

    Returns:
        Procedure: The Procedure FHIR resource.
    """
    procedure_id = str(uuid.uuid4())

    print(result)
    print("_" * 100)

    if not result:
        procedure_code = CodeableConcept(text=procedure_request.procedure)
        notes_text = "Procedure:\n    Procedure could not be documented in the system."
    else:
        best_payload = _extract_procedure_payload(result)
        procedure_code = _build_procedure_code(
            procedure_request.procedure, best_payload
        )

        points = getattr(result, "points", None) or []
        formatted_options = [
            f"- `{opt.payload['long_title']}`"
            for opt in points
            if getattr(opt, "payload", None)
        ]
        notes_text = (
            "Here are the top ten procedure options for your search:\n"
            + "\n".join(formatted_options)
        )
        notes_text += "\n You can call the `ProcedureRequestFHIR` tool with one of the options above if you want to request one of the procedures for your patient."

    procedure_resource = Procedure(
        resourceType="Procedure",
        id=procedure_id,
        status="completed",
        code=procedure_code,
        subject=Reference(reference=f"Patient/{patient_id}"),
        performer=[
            ProcedurePerformer(
                actor=Reference(reference=f"Organization/{organization_id}"),
            )
        ],
        basedOn=[
            Reference(
                reference=f"ServiceRequest/{service_request_id}",
            )
        ],
        note=[
            Annotation(text=notes_text)
        ],  # Include procedure options in the note field
    )

    return procedure_resource


def generate_procedure_resource(
    procedure_request: ProcedureRequestFHIR,
    result: Optional[Any],
    patient_id: str,
    service_request_id: str,
    organization_id: str,
) -> Procedure:
    """
    Generates a Procedure FHIR resource from the procedure result.

    Args:
        procedure_request (ProcedureRequestFHIR): The procedure request object.
        result (Union[List[dict], None]): The procedure options from the vector database.
        patient_id (str): The patient ID.
        service_request_id (str): The ServiceRequest ID.
        organization_id (str): The organization ID.

    Returns:
        Procedure: The Procedure FHIR resource.
    """
    procedure_id = str(uuid.uuid4())

    print(result)
    print("_" * 100)

    if not result:
        procedure_code = CodeableConcept(text=procedure_request.procedure)
        notes_text = "Procedure:\n    Procedure could not be documented in the system."
    else:
        best_payload = _extract_procedure_payload(result)
        procedure_code = _build_procedure_code(
            procedure_request.procedure, best_payload
        )

        notes_text = f"Requested procedure for '{procedure_request.procedure}' on the system.\n\n"

    procedure_resource = Procedure(
        resourceType="Procedure",
        id=procedure_id,
        status="completed",
        code=procedure_code,
        subject=Reference(reference=f"Patient/{patient_id}"),
        performer=[
            ProcedurePerformer(
                actor=Reference(reference=f"Organization/{organization_id}"),
            )
        ],
        basedOn=[
            Reference(
                reference=f"ServiceRequest/{service_request_id}",
            )
        ],
        note=[
            Annotation(text=notes_text)
        ],  # Include procedure options in the note field
    )

    return procedure_resource


def generate_vital_sign_observation_resource(
    vital_sign_request: VitalSigns,
    result: Optional[dict[str, float]],
    patient_id: str,
    service_request_id: str,
    organization_id: str,
) -> Observation:
    observation_id = str(uuid.uuid4())

    note_lines, components = [], []

    if result:
        for key, value in result.items():
            meta = VS_METADATA.get(key)
            if not meta:
                continue

            note_lines.append(f"{meta['display']}: {value:g} {meta['unit']}")

            components.append(
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": meta["loinc"],
                                "display": meta["display"],
                            }
                        ],
                        "text": meta["display"],
                    },
                    "valueQuantity": Quantity(
                        value=value,
                        unit=meta["unit"],
                        system="http://unitsofmeasure.org",
                        code=meta["ucum"],
                    ),
                }
            )

    base_json = {
        "resourceType": "Observation",
        "id": observation_id,
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs",
                    }
                ],
                "text": "Vital Signs",
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "85353-1",  # https://loinc.org/85353-1
                    "display": "Vital signs panel",
                }
            ],
            "text": "Vital signs panel",
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": datetime.now().isoformat(),
        "issued": datetime.now().isoformat() + "Z",
        "performer": [
            {
                "reference": f"Organization/{organization_id}",
                "display": "LLM FHIR Hospital",
            }
        ],
        "basedOn": [{"reference": f"ServiceRequest/{service_request_id}"}],
    }

    if components:
        llm_input = "Vital Signs:\n    " + "\n    ".join(note_lines)
        base_json["component"] = components
    else:
        llm_input = "Vital Signs:\n    Vital-sign data not available."
        base_json["dataAbsentReason"] = {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/data-absent-reason",
                    "code": "unknown",
                    "display": "Unknown",
                }
            ],
            "text": "Vital-sign data not available.",
        }

    base_json["note"] = [{"text": llm_input}]

    return Observation(**base_json)  # type: ignore
