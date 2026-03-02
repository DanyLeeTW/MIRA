import pandas as pd
from dataset.consort_tracker import tracker
from dataset.formats import format_lab_value, format_microbiology_value
from paths import MIMIC_ED_DIR, MIMIC_HOSP_DIR, MIMIC_NOTE_DIR

###### ----- MIMIC-IV Paths ----- ######
BASE_HOSP = MIMIC_HOSP_DIR
BASE_NOTE = MIMIC_NOTE_DIR
BASE_ED = MIMIC_ED_DIR

#######################################

admissions_path = "admissions.csv"
patients_path = "patients.csv"  # https://mimic.mit.edu/docs/iv/modules/hosp/patients/
transfers_path = "transfers.csv"
patients_path = "patients.csv"

labevents_path = (
    "labevents.csv"  # https://mimic.mit.edu/docs/iv/modules/hosp/labevents/
)
d_labitems_path = "d_labitems.csv"
microbiologyevents_path = "microbiologyevents.csv"  # https://mimic.mit.edu/docs/iv/modules/hosp/microbiologyevents/

d_icd_diagnoses_path = "d_icd_diagnoses.csv"
diagnoses_icd_path = "diagnoses_icd.csv"

d_icd_procedures_path = "d_icd_procedures.csv"
procedures_path = "procedures_icd.csv"

prescriptions_path = "prescriptions.csv"
pharmacy_path = "pharmacy.csv"


discharge_detail_path = "discharge_detail.csv"
discharge_path = "discharge.csv"

radiology_path = "radiology.csv"
radiologydetail_path = "radiology_detail.csv"

# for FHIR mapping later
d_labitems_to_loinc_path = "dataset/labitems_map/d_labitems_to_loinc.csv"


### ED medication
### https://mimic.mit.edu/docs/iv/modules/ed/medrecon/

diagnosis_ed_path = "diagnosis.csv"
ed_stays_path = "edstays.csv"
medrecon_path = "medrecon.csv"
pyxis_path = "pyxis.csv"
triage_path = "triage.csv"
vitalsign_path = "vitalsign.csv"
###### ----- MIMIC-IV Paths ----- ######


def read_data(base_hosp, base_note):
    patients = pd.read_csv(base_hosp.joinpath(patients_path))
    admissions = pd.read_csv(base_hosp.joinpath(admissions_path))
    transfers = pd.read_csv(base_hosp.joinpath(transfers_path))
    d_icd_diagnoses = pd.read_csv(base_hosp.joinpath(d_icd_diagnoses_path))
    diagnoses_icd = pd.read_csv(base_hosp.joinpath(diagnoses_icd_path))

    # combine diagnoses with the long_text description from the diagnoses_icd table
    diagnoses_icd_annot = diagnoses_icd.merge(
        d_icd_diagnoses[["icd_code", "icd_version", "long_title"]],
        on=["icd_version", "icd_code"],
        how="left",
    )

    d_icd_procedures = pd.read_csv(base_hosp.joinpath(d_icd_procedures_path))
    procedures = pd.read_csv(base_hosp.joinpath(procedures_path))

    # combine procedures with the long_text description from the diagnoses_icd table
    procedures_annot = procedures.merge(
        d_icd_procedures[["icd_code", "icd_version", "long_title"]],
        on=["icd_version", "icd_code"],
        how="left",
    )

    lab_events = pd.read_csv(base_hosp.joinpath(labevents_path))
    d_labitems = pd.read_csv(base_hosp.joinpath(d_labitems_path))
    prescriptions = pd.read_csv(base_hosp.joinpath(prescriptions_path))

    # merge the lab_events and d_labitems on the "itemid" column
    lab_events_annot = lab_events.merge(d_labitems, on="itemid", how="left")

    microbiology = pd.read_csv(base_hosp.joinpath(microbiologyevents_path))
    discharge = pd.read_csv(base_note.joinpath(discharge_path))
    radiology = pd.read_csv(base_note.joinpath(radiology_path))
    radiology_detail = pd.read_csv(base_note.joinpath(radiologydetail_path))

    lab_events_annot = format_lab_value(lab_events_annot)
    microbiology = format_microbiology_value(microbiology)

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
    )


def read_ed_data(base_ed, base_hosp):
    # Read all the data from the ICU department
    # add hadm_ids where available

    def _add_hadm_ids_to_ed_tables(ed_tables):
        hadm_id_to_stay_id = (
            ed_stays[["hadm_id", "stay_id"]].set_index("stay_id").to_dict()["hadm_id"]
        )

        for table in ed_tables:
            table["hadm_id"] = table["stay_id"].map(hadm_id_to_stay_id)

        return ed_tables

    diagnosis_ed = pd.read_csv(base_ed.joinpath(diagnosis_ed_path))
    ed_stays = pd.read_csv(base_ed.joinpath(ed_stays_path))
    medrecon = pd.read_csv(base_ed.joinpath(medrecon_path))
    pyxis = pd.read_csv(base_ed.joinpath(pyxis_path))
    triage = pd.read_csv(base_ed.joinpath(triage_path))
    vitalsign = pd.read_csv(base_ed.joinpath(vitalsign_path))

    ed_tables = [diagnosis_ed, ed_stays, medrecon, pyxis, triage, vitalsign]
    diagnosis_ed, ed_stays, medrecon, pyxis, triage, vitalsign = (
        _add_hadm_ids_to_ed_tables(ed_tables)
    )

    # add the long_title for diagnoses from icd also to diagnoses_ed
    d_icd_diagnoses = pd.read_csv(base_hosp.joinpath(d_icd_diagnoses_path))
    diagnosis_ed = diagnosis_ed.merge(
        d_icd_diagnoses[["icd_code", "icd_version", "long_title"]],
        on=["icd_version", "icd_code"],
        how="left",
    )

    return diagnosis_ed, ed_stays, medrecon, pyxis, triage, vitalsign


def fill_missing_hadm_ids(transfers, lab_events, radiology, microbiology):
    """Add missing hadm_ids if the charttime of lab_events, microbiology, and radiology occured within hospital stay or briefly (day=1) before.
    # Check: https://www.nature.com/articles/s41591-024-03097-1
    # Use a vectorized version of the function
    """
    # Initialize dictionaries to track imputation counts
    imputed_counts = {"lab": 0, "radiology": 0, "microbiology": 0}

    # Calculate the minimum start_time and maximum disc_time per hadm_id in a single operation
    transfers_summary = (
        transfers.groupby(["subject_id", "hadm_id"])["intime"]
        .agg(["min", "max"])
        .reset_index()
    )
    transfers_summary["start_time"] = transfers_summary["min"] - pd.Timedelta(days=1)

    # Merge the summary data back to the main events dataframes to vectorize the operations
    # will create n=cartesian product of possible combinations for subject_id
    lab_events = lab_events.merge(
        transfers_summary, on="subject_id", how="left", suffixes=("", "_transfers")
    )
    radiology = radiology.merge(
        transfers_summary, on="subject_id", how="left", suffixes=("", "_transfers")
    )
    microbiology = microbiology.merge(
        transfers_summary, on="subject_id", how="left", suffixes=("", "_transfers")
    )

    # Apply masks in a vectorized manner and assign hadm_id
    for df, df_name in [
        (lab_events, "lab"),
        (radiology, "radiology"),
        (microbiology, "microbiology"),
    ]:
        # Create the mask for missing hadm_ids
        mask = (
            (df["hadm_id"].isna())
            & (df["charttime"] >= df["start_time"])
            & (df["charttime"] <= df["max"])
        )

        # Impute hadm_ids using vectorized operations
        imputed_counts[df_name] = mask.sum()
        # where the mask is True, fill the hadm_id with the hadm_id from the transfers table
        df.loc[mask, "hadm_id"] = df.loc[mask, "hadm_id_transfers"]

        if imputed_counts[df_name] > 0:
            print(f"Imputed hadm_id for {imputed_counts[df_name]} {df_name} events.")

    # Cleanup unnecessary columns
    lab_events.drop(
        columns=["start_time", "min", "max", "hadm_id_transfers"], inplace=True
    )
    radiology.drop(
        columns=["start_time", "min", "max", "hadm_id_transfers"], inplace=True
    )
    microbiology.drop(
        columns=["start_time", "min", "max", "hadm_id_transfers"], inplace=True
    )

    return (lab_events, radiology, microbiology)
