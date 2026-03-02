import os
import threading
import time
from pathlib import Path
from typing import Any, List

import pandas as pd
from alive_progress import alive_bar
from dataset.config import DIAGNOSES
from dataset.consort_tracker import tracker
from dataset.data import (
    BASE_ED,
    BASE_HOSP,
    BASE_NOTE,
    fill_missing_hadm_ids,
    read_data,
    read_ed_data,
)
from dataset.discharge import extract_diagnosis_from_discharge
from dataset.extracters import (
    extract_admisson_medication,
    extract_history,
    extract_physical_examination,
)
from dataset.labs import match_lab_events_to_loinc
from dataset.medication import filter_medication
from dataset.microbiology import parse_microbiology
from dataset.mimic_dataset import MIMIC_Dataset
from dataset.procedures import extract_procedures
from dataset.radiology import process_radiology, sanitize_radiology_entries
from dataset.utils import sanitize_hadm_texts
from dataset.validators import (
    validate_diagnoses_ed,
    validate_diagnoses_icd,
    validate_discharge_text,
    validate_lab_events,
    validate_radiology_events,
)
from paths import DIAGNOSIS_DATASETS_DIR, PREPROCESSED_DATA_DIR
from tqdm import tqdm

tqdm.pandas()

import warnings

warnings.filterwarnings("ignore")


def _get_env_int(name: str) -> int | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None

    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got: {value!r}") from exc

    if parsed <= 0:
        raise ValueError(f"{name} must be > 0, got: {parsed}")

    return parsed


def _resolve_diagnosis_subset() -> list[dict[str, Any]]:
    diagnosis_subset = DIAGNOSES
    only_diagnoses = os.getenv("MIRA_DATASET_DIAGNOSES")
    if only_diagnoses:
        selected_names = {
            name.strip() for name in only_diagnoses.split(",") if name.strip()
        }
        diagnosis_subset = [
            pathology
            for pathology in DIAGNOSES
            if pathology["diagnosis"] in selected_names
        ]
        missing = sorted(
            selected_names - {pathology["diagnosis"] for pathology in diagnosis_subset}
        )
        if missing:
            raise ValueError(
                f"MIRA_DATASET_DIAGNOSES contains unknown diagnosis names: {missing}"
            )

    max_diagnoses = _get_env_int("MIRA_MAX_DIAGNOSES")
    if max_diagnoses is not None:
        diagnosis_subset = diagnosis_subset[:max_diagnoses]

    return diagnosis_subset


def _resolve_overwrite_mode() -> str:
    mode = os.getenv("MIRA_OVERWRITE_DATASETS", "ask").strip().lower()
    valid_modes = {"ask", "yes", "no"}
    if mode not in valid_modes:
        raise ValueError(
            f"MIRA_OVERWRITE_DATASETS must be one of: ask, yes, no (got {mode!r})"
        )
    return mode


def _resolve_effective_overwrite_mode(diagnosis: str, mode: str) -> str | None:
    dataset_path = DIAGNOSIS_DATASETS_DIR / diagnosis
    if not dataset_path.exists():
        return "ask"

    if mode == "yes":
        print(
            f"Dataset exists at {dataset_path}. "
            "Overwriting (MIRA_OVERWRITE_DATASETS=yes)."
        )
        return "yes"

    if mode == "no":
        print(
            f"Dataset exists at {dataset_path}. Skipping (MIRA_OVERWRITE_DATASETS=no)."
        )
        return None

    # mode == "ask" and dataset already exists
    while True:
        user_input = input(f"Dataset exists at {dataset_path}. Overwrite? (y/n): ")
        user_input = user_input.strip().lower()
        if user_input in {"y", "yes"}:
            return "yes"
        if user_input in {"n", "no", ""}:
            print(f"Skipping {diagnosis}.")
            return None
        print("Please enter 'y' or 'n'.")


def run_with_progress(func, *args, **kwargs):
    """
    Runs a function with a live progress indicator and returns its result.

    Parameters:
    - func: The function to execute.
    - *args: Positional arguments for the function.
    - **kwargs: Keyword arguments for the function.

    Returns:
    - The return value of func.

    Raises:
    - Exception: Re-raises any exception raised by the target function.
    """
    # Event to signal function completion
    done = threading.Event()
    result = {}

    def target():
        try:
            result["value"] = func(*args, **kwargs)
        except Exception as e:
            result["exception"] = e
        finally:
            done.set()

    thread = threading.Thread(target=target)
    thread.start()

    diagnosis_label = kwargs.get("diagnosis", "all")
    with alive_bar(
        title=f"Running {func.__name__} ... for diagnosis {diagnosis_label}",
        spinner="loving",
        total=None,
    ) as bar:
        while not done.is_set():
            bar()
            time.sleep(1)

    thread.join()

    if "exception" in result:
        raise result["exception"]

    return result.get("value")


def main():
    """Main function to run the dataset creation process."""
    diagnosis_subset = _resolve_diagnosis_subset()
    max_hadm_ids_per_diagnosis = _get_env_int("MIRA_MAX_HADM_IDS_PER_DIAGNOSIS")
    overwrite_mode = _resolve_overwrite_mode()

    (
        patients,
        admissions,
        transfers,
        diagnoses_icd_annot,
        procedures_annot,
        lab_events_annot,
        microbiology,
        discharge,
        radiology,
        radiology_detail,
        prescriptions,
    ) = run_with_progress(read_data, BASE_HOSP, BASE_NOTE)

    diagnosis_ed, stays_ed, medrecon_ed, pyxis_ed, triage_ed, vitalsign_ed = (
        run_with_progress(read_ed_data, BASE_ED, BASE_HOSP)
    )

    print(f"Creating datasets for {len(diagnosis_subset)} diagnoses...")
    if max_hadm_ids_per_diagnosis is not None:
        print(
            "Subset mode enabled:"
            f" max {max_hadm_ids_per_diagnosis} admissions per diagnosis"
        )
    if overwrite_mode == "ask":
        print(
            "Overwrite mode: ask "
            "(you will be prompted before each existing diagnosis dataset)."
        )
    elif overwrite_mode == "yes":
        print("Overwrite mode: yes (existing diagnosis datasets will be overwritten).")
    else:
        print("Overwrite mode: no (existing diagnosis datasets will be skipped).")

    for pathology in diagnosis_subset:
        diagnosis_name = pathology["diagnosis"]
        effective_overwrite_mode = _resolve_effective_overwrite_mode(
            diagnosis_name, overwrite_mode
        )
        if effective_overwrite_mode is None:
            continue

        print(f"Creating dataset for {diagnosis_name}...")
        _ = run_with_progress(
            extract_data,
            diagnosis_for_hadm_filtering=pathology["diagnosis_for_hadm_filtering"],
            diagnosis=diagnosis_name,
            sanitize_list=pathology["sanitize_list"],
            valid_diagnosis_list_from_discharge_letter=pathology[
                "valid_diagnosis_list_from_discharge_letter"
            ],
            valid_diagnosis_list_from_ed=pathology["valid_diagnosis_list_from_ed"],
            rad_region_filter_list=pathology["rad_region_filter_list"],
            diagnoses_icd_annot=diagnoses_icd_annot,
            admissions=admissions,
            discharge=discharge,
            transfers=transfers,
            lab_events_annot=lab_events_annot,
            microbiology=microbiology,
            radiology=radiology,
            radiology_detail=radiology_detail,
            prescriptions=prescriptions,
            procedures_annot=procedures_annot,
            diagnosis_ed=diagnosis_ed,
            stays_ed=stays_ed,
            medrecon_ed=medrecon_ed,
            pyxis_ed=pyxis_ed,
            triage_ed=triage_ed,
            vitalsign_ed=vitalsign_ed,
            patients=patients,
            max_hadm_ids=max_hadm_ids_per_diagnosis,
            overwrite_mode=effective_overwrite_mode,
        )

        print(f"Dataset for {diagnosis_name} created.")


def extract_data(
    diagnosis_for_hadm_filtering: str,
    diagnosis: str,
    sanitize_list: List[str],
    valid_diagnosis_list_from_discharge_letter: List[str],
    valid_diagnosis_list_from_ed: List[str],
    rad_region_filter_list: List[str],
    diagnoses_icd_annot: pd.DataFrame,
    admissions: pd.DataFrame,
    discharge: pd.DataFrame,
    transfers: pd.DataFrame,
    lab_events_annot: pd.DataFrame,
    microbiology: pd.DataFrame,
    radiology: pd.DataFrame,
    radiology_detail: pd.DataFrame,
    prescriptions: pd.DataFrame,
    procedures_annot: pd.DataFrame,
    diagnosis_ed: pd.DataFrame,
    stays_ed: pd.DataFrame,
    medrecon_ed: pd.DataFrame,
    pyxis_ed: pd.DataFrame,
    triage_ed: pd.DataFrame,
    vitalsign_ed: pd.DataFrame,
    patients: pd.DataFrame,
    max_hadm_ids: int | None = None,
    overwrite_mode: str = "ask",
) -> tuple[Any, ...]:
    """
    Extract and process data for a specific diagnosis from various MIMIC-IV dataframes.

    This function filters and processes data from multiple MIMIC-IV tables based on a given diagnosis.
    It performs data cleaning, validation, and transformation steps to create a cohesive dataset
    for the specified diagnosis.

    Args:
        diagnosis_for_hadm_filtering (str): The diagnosis to filter the data for.
        diagnosis (str): The overall diagnosis to save and clean.
        sanitize_list (List[str]): A list of terms to use for sanitizing text data.
        valid_diagnosis_list_from_discharge_letter (List[str]): A list of diagnoses that are valid for the discharge text.
        valid_diagnosis_list_from_ed (List[str]): A list of diagnoses that are valid for the emergency department data.
        rad_region_filter_list (List[str]): A list of radiology regions that are valid.
            This ensures that we only have patients in the list where the relevant imaging is available.
        diagnoses_icd_annot (pd.DataFrame): Annotated ICD diagnoses.
        admissions (pd.DataFrame): Hospital admissions data.
        discharge (pd.DataFrame): Discharge summaries.
        transfers (pd.DataFrame): Patient transfers data.
        lab_events_annot (pd.DataFrame): Annotated laboratory events.
        microbiology (pd.DataFrame): Microbiology test results.
        radiology (pd.DataFrame): Radiology reports.
        radiology_detail (pd.DataFrame): Detailed radiology information.
        prescriptions (pd.DataFrame): Medication prescriptions.
        procedures_annot (pd.DataFrame): Annotated procedures.
        diagnosis_ed (pd.DataFrame): Emergency department diagnoses.
        stays_ed (pd.DataFrame): Emergency department stays.
        medrecon_ed (pd.DataFrame): Medication reconciliation in ED.
        pyxis_ed (pd.DataFrame): Pyxis medication data from ED.
        triage_ed (pd.DataFrame): ED triage information.
        vitalsign_ed (pd.DataFrame): Vital signs recorded in ED.
        patients (pd.DataFrame): Patient information.

    Returns:
        Mimic_Dataset: An instance of the Mimic_Dataset class containing the processed data.

    Note:
        This function performs various data processing steps including:
        - Filtering data based on the specified diagnosis_for_hadm_filtering
        - Cleaning and sanitizing text data
        - Mapping lab events to LOINC codes
        - Validating and removing invalid entries
        - Extracting relevant information from discharge summaries
        - Processing medication data
        The resulting dataset is saved to disk and can be reloaded using Mimic_Dataset.load_dataset().
    """
    # if the dataset already exists, load it from disk ...
    # dataset_path = Path(f"diagnosis_datasets/{diagnosis}")
    # if dataset_path.exists():
    #     print(f"Dataset for {diagnosis} already exists. Loading from disk.")
    #     return MIMIC_Dataset.load_dataset(diagnosis)

    # ... if not, create it
    # map each patient subject_id to their hadm_id

    # for tracking
    tracker.reset()
    tracker.node("Hospital admissions")

    diag_tag = diagnosis
    label = lambda txt: txt  # noqa: E731

    subject_hadm_mapping = (
        diagnoses_icd_annot[
            (
                diagnoses_icd_annot.long_title.str.contains(
                    diagnosis_for_hadm_filtering, case=False
                )
            )
            & (diagnoses_icd_annot.seq_num == 1)
        ]
        .merge(
            admissions[["hadm_id", "subject_id"]],
            on=["hadm_id", "subject_id"],
            how="left",
        )
        .drop_duplicates()
        .set_index("subject_id")["hadm_id"]
        .to_dict()
    )

    # Add hadm_id column to patients dataframe
    patients["hadm_id"] = patients["subject_id"].map(subject_hadm_mapping)

    # get all subject ids; get all hadm_ids for the diagnosis
    subject_hadm_items = list(subject_hadm_mapping.items())
    if max_hadm_ids is not None:
        subject_hadm_items = subject_hadm_items[:max_hadm_ids]
        print(
            f"Subset mode for {diagnosis}: "
            f"processing {len(subject_hadm_items)} admissions."
        )

    subject_ids = [s_id for s_id, _ in subject_hadm_items]
    hadm_ids = [hadm_id for _, hadm_id in subject_hadm_items]

    ############################################################################################
    hadm_ids_ours_set = set(hadm_ids)
    tracker.node(label("ICD-positive admissions"), len(hadm_ids_ours_set))
    tracker.edge("Hospital admissions", label("ICD-positive admissions"))
    print("@ First step:")
    print(f"Number of IDs: {len(hadm_ids_ours_set)}")
    ############################################################################################

    # set timings for comparisons in "fill_missing_hadm_ids"
    admissions["admittime"] = pd.to_datetime(admissions["admittime"])
    admissions["dischtime"] = pd.to_datetime(admissions["dischtime"])
    transfers["intime"] = pd.to_datetime(transfers["intime"])
    lab_events_annot["charttime"] = pd.to_datetime(lab_events_annot["charttime"])
    radiology["charttime"] = pd.to_datetime(radiology["charttime"])
    microbiology["charttime"] = pd.to_datetime(microbiology["charttime"])

    # Filter the dataframes based on subject_ids_filtered (hadm_ids can be missing up until now and will be imputed later)
    lab_events_sid = lab_events_annot[
        lab_events_annot["subject_id"].isin(subject_ids)
    ].copy()
    radiology_sid = radiology[radiology["subject_id"].isin(subject_ids)].copy()
    microbiology_sid = microbiology[microbiology["subject_id"].isin(subject_ids)].copy()
    radiology_detail_sid = radiology_detail[
        radiology_detail["subject_id"].isin(subject_ids)
    ].copy()

    # remove NaNs and "___" in case even our fallback columns where empty or anonymized by "___"
    # lab events
    # dropped_count_lab = lab_events_sid["lab_event_str"].isna().sum()
    # underscore_count_lab = lab_events_sid["lab_event_str"].eq("___").sum()

    lab_events_sid = lab_events_sid.dropna(subset=["lab_event_str"])
    lab_events_sid = lab_events_sid[lab_events_sid["lab_event_str"] != "___"]

    # print(f"Dropped {dropped_count_lab} rows due to NaN values in 'lab_event_str'")
    # print(f"Dropped {underscore_count_lab} rows due to '___' values in 'lab_event_str'")

    # remove NaNs and "___" in case even our fallback columns where empty or anonymized by "___"
    # microbiology
    # dropped_count_micro = microbiology_sid["microbiology_str"].isna().sum()
    # underscore_count_micro = microbiology_sid["microbiology_str"].eq("___").sum()

    microbiology_sid = microbiology_sid.dropna(subset=["microbiology_str"])
    microbiology_sid = microbiology_sid[microbiology_sid["microbiology_str"] != "___"]

    # print(f"Dropped {dropped_count_micro} rows due to NaN values in 'microbiology_str'")
    # print(
    #     f"Dropped {underscore_count_micro} rows due to '___' values in 'microbiology_str'"
    # )

    transfers_hadm_ids = transfers[
        transfers["hadm_id"].isin(hadm_ids)
    ]  # filter for those we are interested in (diagnosis)
    # fill in the missing hadm_ids in case lab values or microbiolgoy or images were made before the patient was admitted to hospital (ICU)
    lab_events_sid, radiology_sid, microbiology_sid = fill_missing_hadm_ids(
        transfers_hadm_ids, lab_events_sid, radiology_sid, microbiology_sid
    )

    tracker.count_unique(label("Lab events w/ Hadm ID"), lab_events_sid, ["hadm_id"])
    tracker.count_unique(
        label("Radiology events w/ Hadm ID"), radiology_sid, ["hadm_id"]
    )
    tracker.count_unique(
        label("Microbiology events w/ Hadm ID"), microbiology_sid, ["hadm_id"]
    )

    # provenance
    tracker.edge(label("ICD-positive admissions"), label("Lab events w/ Hadm ID"))
    tracker.edge(label("ICD-positive admissions"), label("Radiology events w/ Hadm ID"))
    tracker.edge(
        label("ICD-positive admissions"), label("Microbiology events w/ Hadm ID")
    )

    # subset dataframes by hadm_ids (remove those that were not filled by "fill_missing_hadm_ids") and are thus unrelated)
    lab_events_hadm_ids = lab_events_sid[lab_events_sid.hadm_id.isin(hadm_ids)]
    radiology_hadm_ids = radiology_sid[radiology_sid.hadm_id.isin(hadm_ids)]
    microbiology_hadm_ids = microbiology_sid[microbiology_sid.hadm_id.isin(hadm_ids)]
    diagnoses_icd_annot_hadm_ids = diagnoses_icd_annot[
        diagnoses_icd_annot.hadm_id.isin(hadm_ids)
    ]
    procedures_annot_hadm_ids = procedures_annot[
        procedures_annot.hadm_id.isin(hadm_ids)
    ]
    prescriptions_hadm_ids = prescriptions[prescriptions.hadm_id.isin(hadm_ids)].copy()
    # same fore emergency department (ed) data
    diagnosis_ed_hadm_ids = diagnosis_ed[diagnosis_ed.hadm_id.isin(hadm_ids)]
    ed_stays_hadm_ids = stays_ed[stays_ed.hadm_id.isin(hadm_ids)]
    medrecon_hadm_ids = medrecon_ed[medrecon_ed.hadm_id.isin(hadm_ids)]
    pyxis_hadm_ids = pyxis_ed[pyxis_ed.hadm_id.isin(hadm_ids)]
    triage_hadm_ids = triage_ed[triage_ed.hadm_id.isin(hadm_ids)]
    vitalsign_hadm_ids = vitalsign_ed[vitalsign_ed.hadm_id.isin(hadm_ids)]

    ### ----- process discharge data ----- ###
    discharge_hadm_ids = discharge[discharge.hadm_id.isin(hadm_ids)]
    discharge_text = discharge_hadm_ids[["hadm_id", "text"]].copy()

    # Apply the extract_history function to the 'text' column of the dataframe
    # get: patient history, physical examination, admission medication
    discharge_text["extracted_history"] = discharge_text["text"].progress_apply(
        extract_history
    )
    discharge_text["pe"] = discharge_text["text"].progress_apply(
        extract_physical_examination
    )
    # get the admission medication from the discharge letters or if cannot be found from the medrecon (ICU) table
    counter = {"extract_from_discharge_letter": 0, "extract_from_medrecon": 0}
    discharge_text["admission_medication"] = discharge_text.progress_apply(
        extract_admisson_medication,
        ed_stays=ed_stays_hadm_ids,
        medrecon=medrecon_hadm_ids,
        counter=counter,
        axis=1,
    )
    # print("Counter values for admission medication extraction:")
    # for key, value in counter.items():
    #     print(f"{key}: {value}")

    # read in the d_labitems to loinc omop mappings dataframe
    # download from here: https://github.com/MIT-LCP/mimic-code/blob/e39825259beaa9d6bc9b99160049a5d251852aae/mimic-iv/mapping/d_labitems_to_loinc.csv
    # map MIMIC labitems to FHIR compatible LOINC OMOP terminology
    # d_labitems: itemid -> (fluid, category, label)
    lab_events_hadm_ids_loinc_omop = match_lab_events_to_loinc(lab_events_hadm_ids)
    microbiology_hadm_ids = parse_microbiology(microbiology_hadm_ids)

    ### ----- sanitize radiology data ----- ###
    radiology_hadm_ids = process_radiology(
        radiology_hadm_ids, radiology_detail_sid, hadm_ids
    )
    radiology_hadm_ids = sanitize_radiology_entries(radiology_hadm_ids, sanitize_list)

    ### ----- sanitize discharge data ----- ###
    discharge_text = sanitize_hadm_texts(discharge_text, sanitize_list)
    discharge_text = extract_diagnosis_from_discharge(discharge_text)
    discharge_text = extract_procedures(discharge_text)

    ### ---------- validate data ---------- ###
    ### dfs to use afterwards:
    # lab_events_hadm_ids_loinc_omop
    # discharge_text
    # diagnoses_icd_annot_hadm_ids
    lab_events_hadm_ids_loinc_omop, invalid_lab_events_hadmids = validate_lab_events(
        lab_events_hadm_ids_loinc_omop
    )
    discharge_text, invalid_discharge_hadmids = validate_discharge_text(
        discharge_text, valid_diagnosis_list_from_discharge_letter
    )
    diagnoses_icd_annot_hadm_ids, invalid_diagnoses_hadmids_discharge_letter = (
        validate_diagnoses_icd(
            diagnoses_icd_annot_hadm_ids, diagnosis_for_hadm_filtering
        )
    )

    diagnosis_ed_hadm_ids, invalid_diagnoses_hadmids_ed = validate_diagnoses_ed(
        diagnosis_ed_hadm_ids, valid_diagnosis_list_from_ed
    )

    radiology_hadm_ids, invalid_radiology_hadmids = validate_radiology_events(
        radiology_hadm_ids, rad_region_filter_list
    )

    # get all invalid hadm_ids
    invalid_hadm_ids = set(
        invalid_lab_events_hadmids
        + invalid_discharge_hadmids
        + invalid_diagnoses_hadmids_discharge_letter
        + invalid_diagnoses_hadmids_ed
        + invalid_radiology_hadmids
    )
    # print(f"Number of invalid hadm_ids after validation: {len(invalid_hadm_ids)}")

    ### ---------- medication ---------- ###
    prescriptions_hadm_ids.loc[:, "starttime"] = pd.to_datetime(
        prescriptions_hadm_ids["starttime"], errors="coerce"
    )
    prescriptions_hadm_ids.dropna(subset=["starttime"], inplace=True)
    prescriptions_hadm_ids_no_dups, _ = filter_medication(prescriptions_hadm_ids)

    hadm_ids = set(discharge_text.hadm_id.unique())  # type: ignore

    print("@ Second step:")
    invalid_subsets = {
        "invalid_lab_events_hadmids": invalid_lab_events_hadmids,
        "invalid_discharge_hadmids": invalid_discharge_hadmids,
        "invalid_diagnoses_hadmids_discharge_letter": invalid_diagnoses_hadmids_discharge_letter,
        "invalid_diagnoses_hadmids_ed": invalid_diagnoses_hadmids_ed,
        "invalid_radiology_hadmids": invalid_radiology_hadmids,
    }
    for subset_name, invalid_hadm_ids_subset in invalid_subsets.items():
        invalid_hadm_ids_subset = set(invalid_hadm_ids_subset)
        print(f"{subset_name}: {len(invalid_hadm_ids_subset)}")
        print(
            f"After remvofing {subset_name}: {len(hadm_ids - invalid_hadm_ids_subset)}"
        )

    tracker.node(
        label("Excluded – invalid lab events"), len(set(invalid_lab_events_hadmids))
    )
    tracker.edge(label("Lab events w/ Hadm ID"), label("Excluded – invalid lab events"))

    # 2) Discharge letters with no usable narrative / diagnosis
    tracker.node(
        label("Excluded – invalid discharge text"), len(set(invalid_discharge_hadmids))
    )
    tracker.edge(
        label("ICD-positive admissions"), label("Excluded – invalid discharge text")
    )

    # 3) ICD diagnosis in discharge letter does *not* match target
    tracker.node(
        label("Excluded – diagnosis mismatch (discharge)"),
        len(set(invalid_diagnoses_hadmids_discharge_letter)),
    )
    tracker.edge(
        label("ICD-positive admissions"),
        label("Excluded – diagnosis mismatch (discharge)"),
    )

    # 4) ICD diagnosis in ED record does *not* match target
    tracker.node(
        label("Excluded – diagnosis mismatch (ED)"),
        len(set(invalid_diagnoses_hadmids_ed)),
    )
    tracker.edge(
        label("ICD-positive admissions"), label("Excluded – diagnosis mismatch (ED)")
    )

    # 5) Radiology reports outside target region / modality
    tracker.node(
        label("Excluded – invalid radiology"), len(set(invalid_radiology_hadmids))
    )
    tracker.edge(
        label("Radiology events w/ Hadm ID"), label("Excluded – invalid radiology")
    )

    new_hadm_ids = set(hadm_ids) - invalid_hadm_ids
    tracker.node(label("Validated cohort"), len(new_hadm_ids))

    tracker.edge(label("Lab events w/ Hadm ID"), label("Validated cohort"))
    tracker.edge(label("Radiology events w/ Hadm ID"), label("Validated cohort"))
    tracker.edge(label("Microbiology events w/ Hadm ID"), label("Validated cohort"))

    print("@ Last step:")
    print(f"Number of valid hadm_ids final: {len(new_hadm_ids)}")

    lab_events_hadm_ids_loinc_omop = lab_events_hadm_ids_loinc_omop[
        lab_events_hadm_ids_loinc_omop.hadm_id.isin(new_hadm_ids)
    ]
    microbiology_hadm_ids = microbiology_hadm_ids[
        microbiology_hadm_ids.hadm_id.isin(new_hadm_ids)
    ]
    discharge_text = discharge_text[discharge_text.hadm_id.isin(new_hadm_ids)]
    radiology_hadm_ids = radiology_hadm_ids[
        radiology_hadm_ids.hadm_id.isin(new_hadm_ids)
    ]
    prescriptions_hadm_ids_no_dups = prescriptions_hadm_ids_no_dups[
        prescriptions_hadm_ids_no_dups.hadm_id.isin(new_hadm_ids)
    ]
    diagnoses_icd_annot_hadm_ids = diagnoses_icd_annot_hadm_ids[
        diagnoses_icd_annot_hadm_ids.hadm_id.isin(new_hadm_ids)
    ]
    diagnosis_ed_hadm_ids = diagnosis_ed_hadm_ids[
        diagnosis_ed_hadm_ids.hadm_id.isin(new_hadm_ids)
    ]

    ed_stays_hadm_ids = ed_stays_hadm_ids[ed_stays_hadm_ids.hadm_id.isin(new_hadm_ids)]
    medrecon_hadm_ids = medrecon_hadm_ids[medrecon_hadm_ids.hadm_id.isin(new_hadm_ids)]
    pyxis_hadm_ids = pyxis_hadm_ids[pyxis_hadm_ids.hadm_id.isin(new_hadm_ids)]
    triage_hadm_ids = triage_hadm_ids[triage_hadm_ids.hadm_id.isin(new_hadm_ids)]
    vitalsign_hadm_ids = vitalsign_hadm_ids[
        vitalsign_hadm_ids.hadm_id.isin(new_hadm_ids)
    ]
    admissions_hadm_ids = admissions[admissions.hadm_id.isin(new_hadm_ids)]
    patients_hadm_ids = patients[patients.hadm_id.isin(new_hadm_ids)]

    # generate the dataset
    mimic_ds = MIMIC_Dataset(
        diagnosis=diagnosis,
        hadm_ids=new_hadm_ids,
        lab_events=lab_events_hadm_ids_loinc_omop,
        microbiology=microbiology_hadm_ids,
        history_pe_admedication_diagnosis=discharge_text,
        radiology=radiology_hadm_ids,
        medication=prescriptions_hadm_ids_no_dups,
        procedures_icd=procedures_annot_hadm_ids,
        diagnosis_icd=diagnoses_icd_annot_hadm_ids,
        diagnosis_ed=diagnosis_ed_hadm_ids,
        ed_stays=ed_stays_hadm_ids,
        medrecon=medrecon_hadm_ids,
        pyxis=pyxis_hadm_ids,
        triage=triage_hadm_ids,
        vitalsign=vitalsign_hadm_ids,
        admissions=admissions_hadm_ids,
        patients=patients_hadm_ids,
    )

    mimic_ds.save_dataset(diagnosis, overwrite=overwrite_mode)
    # check if the dataset was saved correctly
    mimic_ds = MIMIC_Dataset.load_dataset(diagnosis)

    # return mimic_ds

    return (
        diagnosis,
        new_hadm_ids,
        lab_events_hadm_ids_loinc_omop,
        microbiology_hadm_ids,
        discharge_text,
        radiology_hadm_ids,
        prescriptions_hadm_ids_no_dups,
        procedures_annot_hadm_ids,
        diagnoses_icd_annot_hadm_ids,
        diagnosis_ed_hadm_ids,
        ed_stays_hadm_ids,
        medrecon_hadm_ids,
        pyxis_hadm_ids,
        triage_hadm_ids,
        vitalsign_hadm_ids,
        admissions_hadm_ids,
        patients_hadm_ids,
    )


def reload_preprocessed_data():
    from tqdm import tqdm

    data_files = [
        "patients",
        "admissions",
        "transfers",
        "diagnoses_icd_annot",
        "procedures_annot",
        "lab_events_annot",
        "microbiology",
        "discharge",
        "radiology",
        "radiology_detail",
        "prescriptions",
        "diagnosis_ed",
        "stays_ed",
        "medrecon_ed",
        "pyxis_ed",
        "triage_ed",
        "vitalsign_ed",
    ]

    preprocessed_data_dir = Path(
        os.getenv("MIRA_PREPROCESSED_DATA_DIR", str(PREPROCESSED_DATA_DIR))
    )
    dataframes = {}
    for file_name in tqdm(data_files, desc="Loading preprocessed data"):
        dataframes[file_name] = pd.read_parquet(
            preprocessed_data_dir / f"{file_name}.parquet"
        )

    patients = dataframes["patients"]
    admissions = dataframes["admissions"]
    transfers = dataframes["transfers"]
    diagnoses_icd_annot = dataframes["diagnoses_icd_annot"]
    procedures_annot = dataframes["procedures_annot"]
    lab_events_annot = dataframes["lab_events_annot"]
    microbiology = dataframes["microbiology"]
    discharge = dataframes["discharge"]
    radiology = dataframes["radiology"]
    radiology_detail = dataframes["radiology_detail"]
    prescriptions = dataframes["prescriptions"]
    diagnosis_ed = dataframes["diagnosis_ed"]
    stays_ed = dataframes["stays_ed"]
    medrecon_ed = dataframes["medrecon_ed"]
    pyxis_ed = dataframes["pyxis_ed"]
    triage_ed = dataframes["triage_ed"]
    vitalsign_ed = dataframes["vitalsign_ed"]

    return (
        patients,
        admissions,
        transfers,
        diagnoses_icd_annot,
        procedures_annot,
        lab_events_annot,
        microbiology,
        discharge,
        radiology,
        radiology_detail,
        prescriptions,
        diagnosis_ed,
        stays_ed,
        medrecon_ed,
        pyxis_ed,
        triage_ed,
        vitalsign_ed,
    )


if __name__ == "__main__":
    main()
