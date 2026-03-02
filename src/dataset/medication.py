import pandas as pd
from dataset.utils import add_days


def filter_medication(prescriptions_hadm_ids):
    """Filter medication by days in a 24hr interval for each patient, also removing duplicate prescriptions."""

    prescriptions_hadm_ids.sort_values(
        by=["hadm_id", "starttime"], ascending=True, inplace=True
    )
    # get a days column so we can filter medication by days in a 24hr interval from starttime of the first drug
    prescriptions_hadm_ids.loc[:, "days"] = add_days(
        prescriptions_hadm_ids, "starttime"
    )

    # Create a new dataframe with only the first occurrence of each drug within each hadm_id and day group
    prescriptions_hadm_ids_copy = prescriptions_hadm_ids.copy()

    # Sort the copy by starttime
    prescriptions_hadm_ids_copy.sort_values("starttime", inplace=True)

    # drop duplicates in medication entries per hadm_id and days, keeping the first occurrence
    prescriptions_hadm_ids_no_dups = prescriptions_hadm_ids_copy.drop_duplicates(
        subset=["hadm_id", "days", "drug"], keep="first"
    )

    # Sort the resulting dataframe to maintain the desired order
    prescriptions_hadm_ids_no_dups.sort_values(
        ["hadm_id", "days", "starttime"], inplace=True
    )

    # Reset the index if needed
    prescriptions_hadm_ids_no_dups.reset_index(drop=True, inplace=True)

    return (
        prescriptions_hadm_ids_no_dups,
        prescriptions_hadm_ids,
    )  # return the second dataframe with days appended in case we want to use it
