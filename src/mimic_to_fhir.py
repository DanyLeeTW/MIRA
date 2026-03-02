# mypy: ignore-errors
import json
from datetime import datetime
from typing import Any, List, Optional

import pandas as pd
from backend.log import logger
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.servicerequest import ServiceRequest
from qdrant_collection import Qdrant_Collection
from termcolor import colored
from tools import ProcedureRequestFHIR, ProcedureSearch

_PROCEDURE_CATALOG: Optional[pd.DataFrame] = None


def _load_procedure_catalog() -> Optional[pd.DataFrame]:
    global _PROCEDURE_CATALOG
    if _PROCEDURE_CATALOG is not None:
        return _PROCEDURE_CATALOG

    try:
        from dataset.data import BASE_HOSP, d_icd_procedures_path

        catalog = pd.read_csv(BASE_HOSP.joinpath(d_icd_procedures_path))
        catalog = catalog[["icd_code", "icd_version", "long_title"]].dropna(
            subset=["long_title"]
        )
        catalog["long_title_norm"] = (
            catalog["long_title"].astype(str).str.strip().str.casefold()
        )
        _PROCEDURE_CATALOG = catalog
    except Exception:
        _PROCEDURE_CATALOG = None

    return _PROCEDURE_CATALOG


def fetch_lab_results(
    lab_value_service_request: ServiceRequest,
    patient_data: pd.DataFrame,
    patient_id: str,
    patient_hadm_id: str | int,
) -> pd.Series:
    """
    Fetches the latest lab result for a specific patient and lab value.

    Args:
        patient_id (str): The ID of the patient.
        lab_value (BloodValue): The blood value to retrieve.
        mimic_dataset (pd.DataFrame): The dataset containing lab results.

    Returns:
        pd.Series: The latest lab result matching the criteria.

    Raises:
        ValueError: If no matching lab results are found.
    """
    # get the lab value LOINC / OMOP code concept from the service request
    # Retrieve the LOINC code for the requested lab value

    # try:
    #     lab_value_service_request_loinc_code = int(
    #         lab_value_service_request._lab_value_loinc_code
    #     )
    #     logger.info(
    #         f"Fetching lab results for LOINC code: {lab_value_service_request_loinc_code}"
    #     )
    # except ValueError as ve:
    #     raise ValueError(f"Error retrieving LOINC code: {ve}")

    # Filter the dataset for the patient and lab value
    # filtered = patient_data[
    #     patient_data["itemid"]
    #     == lab_value_service_request_loinc_code  # item_id == loinc_code
    # ]

    filtered = patient_data[
        (patient_data["label"] == lab_value_service_request.lab_value)
        & (patient_data["fluid"] == "Blood")
    ]

    if filtered.empty:
        logger.info(
            f"No lab results found for patient_id: {patient_id} and lab_value: {lab_value_service_request.lab_value}.\n"
            "Returning 'None' that will be returned to the LLM as a missing lab result."
        )
        return None

    # Ensure "charttime" is a datetime column
    filtered.loc[:, "charttime"] = pd.to_datetime(filtered["charttime"])

    filtered = filtered[
        filtered["charttime"] < (filtered["charttime"].min() + pd.Timedelta(days=1))
    ]

    # We just return the earliest lab value result that is available for this hospital admission
    result = filtered.sort_values(by="charttime", ascending=True).iloc[0]
    return result


def fetch_urine_results(
    urine_value_service_request: ServiceRequest,
    patient_data: pd.DataFrame,
    patient_id: str,
    patient_hadm_id: str | int,
) -> pd.Series:
    """
    Fetches the latest lab result for a specific patient and lab value.

    Args:
        patient_id (str): The ID of the patient.
        lab_value (BloodValue): The blood value to retrieve.
        mimic_dataset (pd.DataFrame): The dataset containing lab results.

    Returns:
        pd.Series: The latest lab result matching the criteria.

    Raises:
        ValueError: If no matching lab results are found.
    """
    # get the lab value LOINC / OMOP code concept from the service request
    # Retrieve the LOINC code for the requested lab value

    # try:
    #     lab_value_service_request_loinc_code = int(
    #         lab_value_service_request._lab_value_loinc_code
    #     )
    #     logger.info(
    #         f"Fetching lab results for LOINC code: {lab_value_service_request_loinc_code}"
    #     )
    # except ValueError as ve:
    #     raise ValueError(f"Error retrieving LOINC code: {ve}")

    # Filter the dataset for the patient and lab value
    # filtered = patient_data[
    #     patient_data["itemid"]
    #     == lab_value_service_request_loinc_code  # item_id == loinc_code
    # ]

    filtered = patient_data[
        (patient_data["label"] == urine_value_service_request.urine_value)
        & (patient_data["fluid"] == "Urine")
    ]

    if filtered.empty:
        logger.info(
            f"No lab results found for patient_id: {patient_id} and lab_value: {urine_value_service_request.urine_value}.\n"
            "Returning 'None' that will be returned to the LLM as a missing lab result."
        )
        return None

    # Ensure "charttime" is a datetime column
    filtered.loc[:, "charttime"] = pd.to_datetime(filtered["charttime"])

    filtered = filtered[
        filtered["charttime"] < (filtered["charttime"].min() + pd.Timedelta(days=1))
    ]

    # We just return the earliest lab value result that is available for this hospital admission
    result = filtered.sort_values(by="charttime", ascending=True).iloc[0]

    return result


def fetch_medication_results(
    medication_request: MedicationRequest,
    patient_data: pd.DataFrame,
    patient_id: str,
    patient_hadm_id: str | int,
) -> Optional[pd.Series]:
    """
    Simulates fetching medication results for a specific patient and medication.

    Args:
        medication_request (MedicationRequestFHIR): The medication request object.
        patient_data (pd.DataFrame): The DataFrame containing patient medication events (not used here).
        patient_id (str): The ID of the patient.

    Returns:
        Optional[pd.Series]: Simulated confirmation data or None if simulation fails.
    """
    _, _ = patient_data, patient_id

    logger.info(
        "Calling `fetch_medication_results` is a placeholder for returning the requested medications, not any ground truth from the MIMIC dataset."
    )

    simulated_result = pd.Series(
        {
            "drug_name": medication_request.drug_name,
            "dosage_text": medication_request.dosage_text,
            "dosage_value": medication_request.dosage_value,
            "dosage_unit": medication_request.dosage_unit,
            "period": medication_request.period,
            "period_unit": medication_request.period_unit,
            "frequency": medication_request.frequency,
            "route": medication_request.route,
            "issued": datetime.now(),
        }
    )

    return simulated_result


def fetch_pe_results(
    pe_request: ServiceRequest,
    patient_data: pd.DataFrame,
    patient_id: str,
    patient_hadm_id: str | int,
) -> Optional[str]:
    """
    Fetches the physical examination data for a specific patient.

    Args:
        pe_request (PhysicalExamRequestFHIR): The physical examination request object.
        patient_data (pd.DataFrame): The DataFrame containing patient data.
        patient_id (str): The ID of the patient.

    Returns:
        Optional[str]: The physical examination data or None if not available.
    """
    _ = pe_request

    if patient_data.empty:
        logger.info(
            f"Physical examination data is missing for patient_id: {patient_id}"
        )
        return None

    pe_data = patient_data.iloc[0].get("pe", None).strip()

    if pe_data is None or pd.isna(pe_data):
        logger.info(
            f"Physical examination data is missing for patient_id: {patient_id}"
        )
        return None

    return pe_data


def fetch_microbiology_results(
    microbiology_request: ServiceRequest,
    microbiology_data: pd.DataFrame,
    patient_id: str,
    patient_hadm_id: str,
) -> Optional[pd.DataFrame]:
    """
    Fetches the microbiology results for a specific patient and a requested microbiology test.
    Returns the first (in time order) test and result that was conducted.

    Args:
        microbiology_request (ServiceRequest): The microbiology request object.
        microbiology_data (pd.DataFrame): The DataFrame containing patient data.
        patient_id (str): The ID of the patient.

    Returns:
        Optional[pd.DataFrame]: The microbiology results or None if not available.
    """
    _ = microbiology_request

    if microbiology_data.empty:
        logger.info(f"Microbiology data is missing for patient_id: {patient_id}")
        return None

    test_name = microbiology_request.microbiology_value
    microbiology_data = microbiology_data.loc[
        microbiology_data["test_name"] == test_name
    ]

    if microbiology_data.empty:
        logger.info(
            f"No microbiology results found for patient_id: {patient_id} and microbiology_value: {test_name}.\n"
            "Returning 'None' that will be returned to the LLM as a missing microbiology result."
        )
        return None

    # Convert 'charttime' to datetime and sort
    microbiology_data = microbiology_data.copy()  # to prevent SettingWithCopyWarning
    microbiology_data.loc[:, "charttime"] = pd.to_datetime(
        microbiology_data["charttime"], errors="coerce"
    )
    microbiology_data.sort_values(by="charttime", ascending=True, inplace=True)

    # Get the first 'micro_specimen_id' after sorting
    micro_specimen_id = microbiology_data.iloc[0]["micro_specimen_id"]
    if micro_specimen_id is None:
        logger.info(f"Micro specimen ID is missing for patient_id: {patient_id}")
        return None

    # Create 'microbio_subset' based on 'micro_specimen_id'
    microbio_subset = microbiology_data.loc[
        microbiology_data["micro_specimen_id"] == micro_specimen_id
    ].copy()

    if microbio_subset.empty:
        logger.info(
            f"No microbiology subset found for patient_id: {patient_id} and micro_specimen_id: {micro_specimen_id}"
        )
        return None

    # Convert 'storetime' to datetime and sort
    microbio_subset["storetime"] = pd.to_datetime(
        microbio_subset["storetime"], errors="coerce"
    )
    microbio_subset.sort_values(by="storetime", ascending=True, inplace=True)

    return microbio_subset


def fetch_radiology_results(
    radiology_request: ServiceRequest,
    patient_data: pd.DataFrame,
    patient_id: str,
    patient_hadm_id: str | int,
) -> Optional[pd.Series]:
    """
    Fetches the radiology report for a specific patient and a requested modality and region.
    Returns the first (in time order) report that matches the modality and region.

    Args:
        radiology_request (ServiceRequest): The radiology request object.
        patient_data (pd.DataFrame): The DataFrame containing patient data.
        patient_id (str): The ID of the patient.
        patient_hadm_id (str | int): The hadm id of the patient.

    Returns:
        Optional[pd.Series]: The radiology report or None if not available.
    """
    # Note: we dont need to apply 24h filtering here in code, because
    # there is some variation in the exact timing in the data (order-time vs. charttime = when the note was written (https://mimic.mit.edu/docs/iv/modules/note/radiology/), both of which not necessarily mean the time the image was done... Also, not every diagnosis necessarily requires imaging (i.e. UTI), so the topic is much more nuanced and we have done this while manual case selection of patient cases after our initial dataset generation already which covers this ...
    # During eval, we should not apply the 24h filtering, because writing the notes can happen long after the image was done...

    # Assuming that patient_data has a DataFrame with radiology reports
    # Let's assume it's in patient_data.radiology_reports
    radiology_data = patient_data.radiology

    if radiology_data.empty:
        logger.info(f"Radiology data is missing for patient_id: {patient_id}")
        return None

    # Filter by modality and region
    modality = radiology_request.modality.value
    region = radiology_request.region.value

    if modality == "CT" and region == "Venous":
        region = "Chest"
        print(
            colored(
                f"Manually fixing modality for patient_hadm_id: {patient_hadm_id}",
                "red",
            )
        )

    # this patients Chest CT is registered with the Abdomen and can thus not be requested via "Chest"
    if patient_hadm_id == 23427406:
        if modality == "CT" and region == "Chest":
            region = "Abdomen"
            logger.info(
                colored(
                    f"Manually fixing modality for patient_hadm_id: {patient_hadm_id}",
                    "red",
                )
            )
    # manually fix the modality for these two patients
    if patient_hadm_id in [
        23794159,
        25868499,
    ]:  # both of them have CTU but their reports match that of CT Abdomen
        if modality == "CT" and region == "Abdomen":
            logger.info(
                colored(
                    f"Manually fixing modality for patient_hadm_id: {patient_hadm_id}",
                    "red",
                )
            )
            modality = "CTU"

    if modality == "ERCP":
        with open("resources/pancreatic_cancer_info.json", "r") as f:
            try:
                ercp_data = json.load(f)[patient_hadm_id][
                    "ercp"
                ]  # fail if ID not found
                if ercp_data["has_ercp"]:
                    result = {
                        "extracted_rad_events": f"Biopsy result from the ERCP:\n{ercp_data['biopsy_result']}"
                    }
                    return result
                else:
                    result = None
            except Exception:
                result = None

    # Filter the radiology_data DataFrame
    filtered_data = radiology_data[
        (radiology_data["modality"] == modality) & (radiology_data["region"] == region)
    ]

    if filtered_data.empty:
        logger.info(
            f"No radiology reports found for patient_id: {patient_id}, modality: {modality}, and region: {region}.\n"
            "Returning 'None' that will be returned to the LLM as a missing radiology report."
        )

        return None

    # Sort by date and get the first report
    filtered_data = filtered_data.sort_values(by="charttime", ascending=True)
    result = filtered_data.iloc[0]

    return result


def fetch_procedure_search_results(
    procedure_request: ProcedureSearch,
    collection: Qdrant_Collection,
    patient_id: str,
    patient_hadm_id: str | int,
) -> Optional[List[dict]]:
    """
    Fetches the top_k matching procedure codes using vector database search.

    Args:
        procedure_request (ProcedureRequestFHIR): The procedure request object.
        collection (Qdrant_Collection): The vector database collection.

    Returns:
        Optional[List[dict]]: The top_k matching procedure codes and metadata, or None if not found.
    """
    query = procedure_request.procedure
    top_k = 10
    procedure_options = collection.search(query, query_filter=None, top_k=top_k)

    if not procedure_options:
        logger.info(f"No procedure codes found for query: {query}")
        return None

    # print(colored(procedure_options, "cyan"))
    return procedure_options


def fetch_procedure_request_results(
    procedure_request: ProcedureRequestFHIR,
    collection: Optional[Qdrant_Collection],
    patient_id: str,
    patient_hadm_id: str | int,
) -> Optional[Any]:
    """
    Resolve a concrete procedure code for a requested procedure when possible.
    """
    _ = patient_id, patient_hadm_id

    # 1) Prefer exact local code lookup for selected procedure title.
    try:
        catalog = _load_procedure_catalog()
        if catalog is not None:
            query = str(procedure_request.procedure).strip().casefold()
            exact = catalog.loc[catalog["long_title_norm"] == query]
            if not exact.empty:
                best = exact.iloc[0]
                return {
                    "icd_code": str(best["icd_code"]),
                    "icd_version": str(best["icd_version"]),
                    "long_title": str(best["long_title"]),
                }
    except Exception:
        pass

    # 2) Optional vector-search fallback.
    if collection is not None:
        try:
            result = collection.search(
                procedure_request.procedure, query_filter=None, top_k=1
            )
            if result and getattr(result, "points", None):
                return result
        except Exception:
            pass

    # 3) Final fallback: text-only procedure response.
    return {"procedure": procedure_request.procedure}


# build from: https://loinc.org/85353-1
VS_METADATA: dict[str, dict[str, Any]] = {
    "temperature": {
        "loinc": "8310-5",
        "display": "Body temperature",
        "unit": "Fahrenheit",
        "ucum": "degF",
    },
    "heartrate": {
        "loinc": "8867-4",
        "display": "Heart rate",
        "unit": "/min",
        "ucum": "{beats}/min",
    },
    "resprate": {
        "loinc": "9279-1",
        "display": "Respiratory rate",
        "unit": "/min",
        "ucum": "{breaths}/min",
    },
    "o2sat": {
        "loinc": "59408-5",
        "display": "Oxygen saturation by Pulse oximetry",
        "unit": "%",
        "ucum": "%",
    },
    "sbp": {
        "loinc": "8480-6",
        "display": "Systolic blood pressure",
        "unit": "mmHg",
        "ucum": "mm[Hg]",
    },
    "dbp": {
        "loinc": "8462-4",
        "display": "Diastolic blood pressure",
        "unit": "mmHg",
        "ucum": "mm[Hg]",
    },
}


def fetch_vital_sign_results(
    vital_sign_request: ServiceRequest,
    patient_data: pd.DataFrame,
    patient_id: str,
    patient_hadm_id: str | int,
) -> Optional[dict[str, float]]:
    """
    Return a dict of vital-sign values keyed by the short names in VS_METADATA.
    Missing values (NaNs) are skipped.
    """
    _ = (vital_sign_request, patient_hadm_id)

    if patient_data.empty:
        logger.info(f"Vital-sign data is missing for patient_id: {patient_id}")
        return None

    assert patient_data.shape[0] == 1, f"More than 1 record for {patient_id}"
    row = patient_data.iloc[0]

    vs_dict: dict[str, float] = {}
    for key in VS_METADATA:
        if key in row and pd.notna(row[key]):
            vs_dict[key] = float(row[key])

    return vs_dict or None
