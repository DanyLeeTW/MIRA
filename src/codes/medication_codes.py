import csv
import os
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests
from backend.log import logger
from dataset.data import BASE_ED, BASE_HOSP, medrecon_path, prescriptions_path
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_fixed
from tqdm import tqdm

CURRENT_DIR = Path(__file__).resolve().parent


load_dotenv()
UMLS_API_KEY = os.getenv("UMLS_API_KEY")
UMLS_AUTH_ENDPOINT = "https://utslogin.nlm.nih.gov/cas/v1/api-key"
UMLS_BASE_URL = "https://uts-ws.nlm.nih.gov/rest"

# Initialize caches
rxnorm_code_cache = {}
snomed_code_cache = {}
atc_code_cache = {}


@retry(stop=stop_after_attempt(3), wait=wait_fixed(4))
def get_umls_tgt(api_key):
    """Obtain the Ticket Granting Ticket (TGT) for UMLS authentication."""
    params = {"apikey": api_key}
    response = requests.post(UMLS_AUTH_ENDPOINT, data=params)
    if response.status_code == 201:
        tgt = response.headers["location"]
        return tgt
    else:
        raise Exception("Failed to obtain TGT for UMLS API.")


@retry(stop=stop_after_attempt(3), wait=wait_fixed(24))
def get_umls_service_ticket(tgt):
    """Obtain a Service Ticket (ST) for each UMLS API call."""
    params = {"service": "http://umlsks.nlm.nih.gov"}
    response = requests.post(tgt, data=params)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception("Failed to obtain Service Ticket for UMLS API.")


@retry(stop=stop_after_attempt(3), wait=wait_fixed(4))
def get_rxnorm_code_from_name(drug_name):
    """Get RxNorm code for a medication name using RxNav API."""
    if drug_name in rxnorm_code_cache:
        return rxnorm_code_cache[drug_name]
    url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={drug_name}&search=1"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if "idGroup" in data and "rxnormId" in data["idGroup"]:
            rxnorm_code = data["idGroup"]["rxnormId"][0]
            rxnorm_code_cache[drug_name] = rxnorm_code
            return rxnorm_code
        else:
            rxnorm_code_cache[drug_name] = None
    else:
        raise Exception(f"Failed to get RxNorm code from name: {drug_name}")
    return None


@retry(stop=stop_after_attempt(3), wait=wait_fixed(4))
def get_rxnorm_code_from_ndc(ndc_code):
    """Get RxNorm code for an NDC code using RxNav API."""
    if ndc_code in rxnorm_code_cache:
        return rxnorm_code_cache[ndc_code]
    url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?idtype=ndc&id={ndc_code}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if "idGroup" in data and "rxnormId" in data["idGroup"]:
            rxnorm_code = data["idGroup"]["rxnormId"][0]
            rxnorm_code_cache[ndc_code] = rxnorm_code
            return rxnorm_code
        else:
            rxnorm_code_cache[ndc_code] = None
    else:
        raise Exception(f"Failed to get RxNorm code from NDC: {ndc_code}")
    return None


@retry(stop=stop_after_attempt(3), wait=wait_fixed(4))
def get_snomed_code_from_rxnorm(rxnorm_code):
    """Get SNOMED CT code from an RxNorm code using RxNav API."""
    warnings.warn(
        "get_snomed_code_from_rxnorm is deprecated and will be removed in a future version.",
        DeprecationWarning,
        stacklevel=2,
    )
    if rxnorm_code in snomed_code_cache:
        return snomed_code_cache[rxnorm_code]
    url = f"https://rxnav.nlm.nih.gov/REST/rxclass/class/byRxcui.json?rxcui={rxnorm_code}&relaSource=SNOMEDCT"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if "rxclassDrugInfoList" in data and data["rxclassDrugInfoList"].get(
            "rxclassDrugInfo"
        ):
            snomed_code = data["rxclassDrugInfoList"]["rxclassDrugInfo"][0][
                "rxclassMinConceptItem"
            ]["classId"]
            snomed_code_cache[rxnorm_code] = snomed_code
            return snomed_code
        else:
            snomed_code_cache[rxnorm_code] = None
    else:
        raise Exception(f"Failed to get SNOMED code from RxNorm code: {rxnorm_code}")
    return None


@retry(stop=stop_after_attempt(3), wait=wait_fixed(4))
def get_snomed_code_from_umls(rxnorm_code, tgt):
    """Get SNOMED CT codes from an RxNorm code using UMLS API."""
    if rxnorm_code in snomed_code_cache:
        return snomed_code_cache[rxnorm_code]
    st = get_umls_service_ticket(tgt)
    params = {
        "ticket": st,
        "version": "current",
        "targetSource": "SNOMEDCT_US",  # or "SNOMEDCT" depending on availability
    }
    url = f"{UMLS_BASE_URL}/crosswalk/current/source/RXNORM/{rxnorm_code}"
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        snomed_codes = []
        for item in data.get("result", []):
            if item["rootSource"] in ["SNOMEDCT_US", "SNOMEDCT"]:
                snomed_codes.append(item["ui"])
        if snomed_codes:
            snomed_code_cache[rxnorm_code] = snomed_codes
            return snomed_codes
        else:
            snomed_code_cache[rxnorm_code] = None
    else:
        raise Exception(f"Failed to get SNOMED CT code from RxNorm code: {rxnorm_code}")
    return None


@retry(stop=stop_after_attempt(3), wait=wait_fixed(4))
def get_atc_code_from_umls(rxnorm_code, tgt):
    """Get specific ATC code from RxNorm code using UMLS API."""
    if rxnorm_code in atc_code_cache:
        return atc_code_cache[rxnorm_code]
    st = get_umls_service_ticket(tgt)
    params = {"ticket": st, "version": "current", "targetSource": "ATC"}
    url = f"{UMLS_BASE_URL}/crosswalk/current/source/RXNORM/{rxnorm_code}"
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        atc_codes = []
        for item in data.get("result", []):
            if item["rootSource"] == "ATC":
                atc_codes.append(item["ui"])
        if atc_codes:
            atc_code_cache[rxnorm_code] = atc_codes
            return atc_codes
        else:
            atc_code_cache[rxnorm_code] = None
    else:
        raise Exception(f"Failed to get ATC code from RxNorm code: {rxnorm_code}")
    return None


def process_row(row, tgt):
    drug_name = row.get("drug_name")
    ndc_code = row.get("ndc")
    rxnorm_code = None
    snomed_ct_codes = None
    atc_codes = None
    if pd.notna(ndc_code):
        # Some NDC codes are NA / None in the prescriptions.csv
        rxnorm_code = get_rxnorm_code_from_ndc(ndc_code)
    if not rxnorm_code and pd.notna(drug_name):
        # Fallback if NDC code was NA or we couldn"t get a RxNorm code via NDC code, then use drug_name
        rxnorm_code = get_rxnorm_code_from_name(drug_name)
    if rxnorm_code:
        snomed_ct_codes = get_snomed_code_from_umls(rxnorm_code, tgt)
        atc_codes = get_atc_code_from_umls(rxnorm_code, tgt)
        if snomed_ct_codes:
            snomed_ct_codes = ";".join(snomed_ct_codes)
        if atc_codes:
            atc_codes = ";".join(atc_codes)
    row["rxnorm_code"] = rxnorm_code
    row["snomed_ct_code"] = snomed_ct_codes
    row["atc_codes"] = atc_codes
    return row


def load_medication_data(base_hosp, base_ed):
    """Load the prescriptions.csv and medrecon.csv files and generate unique combinations of medication names and NDC codes.
    For whatever reason, NDC codes get loaded as floating point values, need to case to integer to allow mapping.
    """
    prescriptions = pd.read_csv(base_hosp / prescriptions_path)
    medrecon = pd.read_csv(base_ed / medrecon_path)

    # Convert the "ndc" columns in prescriptions and medrecon to integer but leave NA if NA
    prescriptions["ndc"] = (
        prescriptions["ndc"]
        .apply(lambda x: int(x) if pd.notna(x) else pd.NA)
        .astype("Int64")
    )
    medrecon["ndc"] = (
        medrecon["ndc"]
        .apply(lambda x: int(x) if pd.notna(x) else pd.NA)
        .astype("Int64")
    )

    # Get unique combinations of drug names and NDC codes
    prescriptions_unique = prescriptions[["drug", "ndc"]].drop_duplicates()
    medrecon_unique = medrecon[["name", "ndc"]].drop_duplicates()

    # Standardize column names
    prescriptions_unique.rename(columns={"drug": "drug_name"}, inplace=True)
    medrecon_unique.rename(columns={"name": "drug_name"}, inplace=True)

    # Combine datasets
    combined_unique = pd.concat([prescriptions_unique, medrecon_unique])
    combined_unique = combined_unique.drop_duplicates()

    # Reset index
    combined_unique.reset_index(drop=True, inplace=True)
    return combined_unique


def get_medication_codes(
    path: str, max_workers: int = 4, base_hosp=BASE_HOSP, base_ed=BASE_ED, batch_size=50
):
    medication_data = load_medication_data(base_hosp, base_ed)

    # Initialize UMLS TGT
    tgt = get_umls_tgt(UMLS_API_KEY)

    # Convert DataFrame to list of dictionaries
    rows = medication_data.to_dict("records")

    # Prepare CSV file
    output_file_path = CURRENT_DIR / "mappings" / path
    output_file_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(medication_data.columns) + [
        "rxnorm_code",
        "snomed_ct_code",
        "atc_codes",
    ]

    # Open the CSV file and write the header
    with open(output_file_path, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

    # Process rows in parallel
    buffer = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_row = {executor.submit(process_row, row, tgt): row for row in rows}
        for future in tqdm(
            as_completed(future_to_row),
            total=len(future_to_row),
            desc="Processing rows",
        ):
            try:
                result = future.result()
                buffer.append(result)
                # If buffer is full, write to CSV and clear buffer
                if len(buffer) >= batch_size:
                    with open(
                        output_file_path, "a", newline="", encoding="utf-8"
                    ) as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writerows(buffer)
                    buffer.clear()
            except Exception as exc:
                logger.info(f"Row generated an exception: {exc}")

    # Write any remaining results in buffer
    if buffer:
        with open(output_file_path, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writerows(buffer)


if __name__ == "__main__":
    # Construct the "mappings" directory path relative to the script"s directory
    mappings_dir = CURRENT_DIR / "mappings"

    # Ensure the "mappings" directory exists
    mappings_dir.mkdir(parents=True, exist_ok=True)

    path = "medication_ndc_rxnorm_snomedct_atc.csv"

    get_medication_codes(path, max_workers=6)


# ==== INFERENCE FUNCTIONS === #


@retry(stop=stop_after_attempt(3), wait=wait_fixed(4))
def get_ndc_codes_from_name(drug_name):
    """Get NDC codes for a medication name using openFDA API."""

    url = "https://api.fda.gov/drug/ndc.json"
    params = {
        "search": f'generic_name:"{drug_name}"',
        "limit": 100,
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        ndc_codes = []
        results = data.get("results", [])
        for item in results:
            ndc_code = item.get("product_ndc")
            if ndc_code:
                ndc_codes.append(ndc_code)
        if ndc_codes:
            return ndc_codes
        else:
            return None
    else:
        # as a fallback, we will catch None and try to get RxNorm in other ways
        return None


@retry(stop=stop_after_attempt(3), wait=wait_fixed(4))
def get_drug_codes_from_name(drug_name):
    """
    Inference call for getting medication codes for FHIR drug requests.
    Retrieve all relevant drug codes (NDC, RxNorm, SNOMED CT, ATC) for a given medication name.

    This function first attempts to fetch the codes from an existing local dataset. If the codes are not found locally,
    it uses various APIs (RxNav and UMLS) to retrieve the codes from the web.

    Args:
        drug_name (str): The name of the medication for which to retrieve the codes.

    Returns:
        dict: A dictionary containing the drug name and its corresponding codes (NDC, RxNorm, SNOMED CT, ATC).
              If the codes are not found, raises a ValueError.

    Raises:
        ValueError: If unable to retrieve the RxNorm code for the given drug name.
    """

    try:
        mapping_path = (
            Path(__file__).resolve().parent
            / "mappings"
            / "medication_ndc_rxnorm_snomedct_atc.csv"
        )
        if mapping_path.exists():
            codes = pd.read_csv(mapping_path, dtype=str).fillna("")
            matched = codes.loc[
                codes["drug_name"].str.casefold() == str(drug_name).casefold()
            ]
            if not matched.empty:
                row = matched.iloc[0].to_dict()
                return {
                    "drug_name": drug_name,
                    "ndc": row.get("ndc") or None,
                    "rxnorm_code": row.get("rxnorm_code") or None,
                    "snomed_ct_code": row.get("snomed_ct_code") or None,
                    "atc_codes": row.get("atc_codes") or None,
                }
    except Exception:
        logger.info(
            f"Codes for medication {drug_name} not in local database. Fetching from web ..."
        )

    load_dotenv()
    UMLS_API_KEY = os.getenv("UMLS_API_KEY")
    tgt = get_umls_tgt(UMLS_API_KEY)

    ndc_codes = None
    rxnorm_code = None
    snomed_ct_codes = None
    atc_codes = None

    # try to get RxNorm code from drug name
    rxnorm_code = get_rxnorm_code_from_name(drug_name)

    if rxnorm_code is None:
        # Get NDC codes from drug name
        ndc_codes = get_ndc_codes_from_name(drug_name)

        if ndc_codes:
            # Use NDC codes to get RxNorm code
            for ndc_code in ndc_codes:
                # Normalize NDC code (remove hyphens)
                normalized_ndc_code = ndc_code.replace("-", "")
                rxnorm_code = get_rxnorm_code_from_ndc(normalized_ndc_code)
                if rxnorm_code:
                    break  # Stop at the first RxNorm code found

        else:
            logger.info(f"Unable to retrieve RxNorm code for drug: {drug_name}")

    else:
        ndc_codes = get_ndc_codes_from_name(drug_name)

    if rxnorm_code:
        # Get SNOMED CT codes from RxNorm code using UMLS API
        snomed_ct_codes = get_snomed_code_from_umls(rxnorm_code, tgt)
        if snomed_ct_codes:
            snomed_ct_codes = ";".join(snomed_ct_codes)

        # Get ATC codes from RxNorm code using UMLS API
        atc_codes = get_atc_code_from_umls(rxnorm_code, tgt)
        if atc_codes:
            atc_codes = ";".join(atc_codes)

    # Join multiple NDC codes into a semicolon-separated string
    if ndc_codes:
        ndc_codes_str = ";".join(ndc_codes)
    else:
        ndc_codes_str = None

    result = {
        "drug_name": drug_name,
        "ndc": ndc_codes_str,
        "rxnorm_code": rxnorm_code,
        "snomed_ct_code": snomed_ct_codes,
        "atc_codes": atc_codes,
    }
    return result


@retry(stop=stop_after_attempt(3), wait=wait_fixed(4))
def get_snomed_code_from_modality_region(modality, region, tgt):
    """
    Get SNOMED CT code for a given imaging modality and body region using UMLS API.

    Args:
        modality (str): The imaging modality (e.g., 'CT', 'MRI').
        region (str): The body region (e.g., 'Chest', 'Head').
        tgt (str): The Ticket Granting Ticket (TGT) for UMLS authentication.

    Returns:
        str or None: The SNOMED CT code if found, else None.
    """
    st = get_umls_service_ticket(tgt)
    search_string = f"{modality} {region}"
    params = {
        "string": search_string,
        "ticket": st,
        "pageSize": 10,
        "sabs": "SNOMEDCT_US",  # Limit to SNOMED CT US Edition
        "returnIdType": "code",
        "searchType": "words",
    }
    url = f"{UMLS_BASE_URL}/search/current"
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        results = data.get("result", {}).get("results", [])
        for item in results:
            if item.get("ui") != "NONE":
                code = item.get("ui")
                name = item.get("name")
                return code  # Return the first matching code
    else:
        raise Exception(f"Failed to get SNOMED CT code for {modality} {region}")
    return None


@retry(stop=stop_after_attempt(3), wait=wait_fixed(4))
def get_loinc_code_from_modality_region(modality, region, tgt):
    """
    Get LOINC code for a given imaging modality and body region using UMLS API.

    Args:
        modality (str): The imaging modality (e.g., 'CT', 'MRI').
        region (str): The body region (e.g., 'Chest', 'Head').
        tgt (str): The Ticket Granting Ticket (TGT) for UMLS authentication.

    Returns:
        str or None: The LOINC code if found, else None.
    """
    st = get_umls_service_ticket(tgt)
    search_string = f"{modality} {region}"
    params = {
        "string": search_string,
        "ticket": st,
        "pageSize": 10,
        "sabs": "LNC",  # Limit to LOINC
        "returnIdType": "code",
        "searchType": "words",
    }
    url = f"{UMLS_BASE_URL}/search/current"
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        results = data.get("result", {}).get("results", [])
        for item in results:
            if item.get("ui") != "NONE":
                code = item.get("ui")
                name = item.get("name")
                return code  # Return the first matching code
    else:
        raise Exception(f"Failed to get LOINC code for {modality} {region}")
    return None
