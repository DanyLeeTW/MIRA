from typing import List

import pandas as pd
from tqdm import tqdm

tqdm.pandas()


def validate_lab_events(df):
    """Check if any of the final entries in the lab events dataframe are invalid.
    Invalid entries are:
    - NaN
    - Empty string
    - "___"

    Note: We do not drop invalid rows here, only collect the invalid hadm_ids, so that we can drop them
          later together with other invalid ids from other fields (microbiology, etc)

    """
    df["is_invalid"] = False
    # if lab_event_str is NaN, empty, or "___", then invalidate
    df.loc[
        (df["lab_event_str"].isna())
        | (df["lab_event_str"] == "")
        | (df["lab_event_str"] == "___"),
        "is_invalid",
    ] = True
    invalid_count = df["is_invalid"].sum()
    total_count = len(df)
    print(
        f"Number of invalid entries in lab_events: {invalid_count} out of {total_count}"
    )

    # Group by hadm_id and check if all entries are invalid
    # so that we only drop hadm_ids that are fully invalid (all entries are invalid)
    invalid_hadm_ids = df.groupby("hadm_id")["is_invalid"].all()
    invalid_hadm_ids = invalid_hadm_ids[invalid_hadm_ids].index.tolist()

    print(
        f"Number of hadm_ids with all invalid entries in lab_events: {len(invalid_hadm_ids)}"
    )

    return df, invalid_hadm_ids


def validate_discharge_text(df, valid_diagnosis_list: list[str]):
    """Check if any entry in the discharge_text dataframe is invalid.
    Invalid entries are:
    - NaN (Extracted History and Physical Examination)
    - Empty string (Extracted History and Physical Examination)
    - Less than 40 characters (Physical Examination only)

    Note: We do not drop invalid rows here, only collect the invalid hadm_ids, so that we can drop them
          later together with other invalid ids from other fields (microbiology, etc)

    `valid_diagnosis_list`: List of diagnoses that are valid for the discharge text.
    """
    # check that we do not have duplicate hadm_ids
    assert df.hadm_id.is_unique, "hadm_id is not unique"
    # Create a new column "is_invalid" initialized as False
    df["is_invalid"] = False

    # Check conditions and set "is_invalid" to True where applicable
    # if either extracted_history or pe is empty ("") or NaN or pe is less than 40 characters, then invalidate
    df.loc[
        (df["extracted_history"].isna())
        | (  # Empty List or List with only [0]
            df["extracted_history"].apply(
                lambda x: (
                    isinstance(x, list) and (len(x) == 0 or (len(x) == 1 and x[0] == 0))
                )
            )
        )
        | (df["extracted_history"] == "")
        | (df["pe"].isna())
        | (df["pe"] == "")
        | (
            df["pe"].str.len() < 40
        ),  # hardcoded from: https://github.com/paulhager/MIMIC-Clinical-Decision-Making-Dataset/blob/main/dataset/dataset.py#L128
        "is_invalid",
    ] = True

    # remove the invalid ones that are NOT in the valid_diagnosis_list
    df.loc[
        (
            ~df["discharge_diagnosis_from_text"]
            .str.lower()
            .isin([diagnosis.lower() for diagnosis in valid_diagnosis_list])
        )
        & (~df["is_invalid"]),
        "is_invalid",
    ] = True

    hadm_invalid_groups = df.groupby("hadm_id")["is_invalid"].all()
    invalid_hadm_ids = hadm_invalid_groups[hadm_invalid_groups].index.tolist()

    # Count and print the number of invalid entries
    invalid_count = df["is_invalid"].sum()
    total_count = len(df)
    print(
        f"Number of invalid entries in discharge_text: {invalid_count} out of {total_count}"
    )

    return df, invalid_hadm_ids
    # return df, []


def validate_diagnoses_icd(df: pd.DataFrame, diagnosis: str):
    """If the diagnosis is not in the long_title or it is but the seq_num is not 1, then it is invalid.
    Has some issues with billing data etc (Sepsis must always be second) ...

    Note: We do not drop invalid rows here, only collect the invalid hadm_ids, so that we can drop them
          later together with other invalid ids from other fields (microbiology, etc)
    """

    # assert we do not have duplicate hadm_ids for same icd code version
    assert (
        df.groupby(["hadm_id", "seq_num", "icd_version"]).size().max() == 1
    ), "combination of hadm_id and seq_num is not unique"

    df.loc[:, "is_invalid"] = df.apply(
        # if the diagnosis is not in the long_title or the seq_num is not 1, then it is invalid
        lambda row: (
            not (diagnosis.lower() in row["long_title"].lower()) or row["seq_num"] != 1
        ),
        axis=1,
    )

    # Count the number of invalid entries
    invalid_count = df["is_invalid"].sum()

    # Print the number of invalid entries
    print(
        f"Number of invalid entries in diagnoses_icd: {invalid_count} out of {len(df)} ... \
          This doesn't mean anything because we have all other billed diagnoses in the dataset ... "
    )

    invalid_hadm_ids = (
        df[(df["is_invalid"]) & (df["seq_num"] == 1)].hadm_id.unique().tolist()
    )

    return df, invalid_hadm_ids


def validate_diagnoses_ed(df, valid_diagnosis_list_from_ed):
    """
    Validates the ED diagnosis dataframe.
    An invalid hadm_id is one where the diagnosis is not in the valid_diagnosis_list_from_ed.
    Args:
        df: The ED diagnosis dataframe.
        valid_diagnosis_list_from_ed: A list of valid diagnoses.
    Returns:
        df: The validated ED diagnosis dataframe.
        invalid_hadm_ids: A set of invalid hadm_ids.
    """
    df = df.copy()
    df["long_title"] = (
        df["long_title"].astype(str).fillna("")
    )  # fix before NaN crashes in lamdba below
    valid_ids = (
        df.groupby("hadm_id")
        .filter(lambda x: (x["seq_num"] == 1).sum() <= 1)["hadm_id"]
        .unique()
    )
    df["is_invalid"] = False
    s = df[(df["seq_num"] == 1) & (df["hadm_id"].isin(valid_ids))]
    correct_ids = set(
        s[
            s["long_title"]
            .str.lower()
            .apply(
                lambda x: any(
                    valid_diagnosis.lower() in x
                    for valid_diagnosis in valid_diagnosis_list_from_ed
                )
            )
        ]["hadm_id"]
    )
    invalid_hadm_ids = [int(i) for i in s["hadm_id"].unique() if i not in correct_ids]

    df.loc[
        (df["hadm_id"].isin(invalid_hadm_ids)) & (df["seq_num"] == 1), "is_invalid"
    ] = True

    return df, invalid_hadm_ids
    # return df, []


def validate_radiology_events(df, region_filter_list: List[str]):
    """Check if any of the final entries in the radiology events dataframe are invalid.
    Args:
        df: The radiology events dataframe.
        region_filter_list: A list of valid radiology regions.
    Returns:
        df: The validated radiology events dataframe.
        invalid_hadm_ids: A set of invalid hadm_ids.

    Note: This does not remove other imaging from patients, only flags those invalid that do not
          have the relevant imaging needed for the diagnosis. If the patient has it, other imaging data will be retrained.
    Note: We do not drop invalid rows here, only collect the invalid hadm_ids, so that we can drop them
          later together with other invalid ids from other fields (microbiology, etc)
    """

    df["is_invalid"] = False
    # only invalidate those, that are so far not invalid (is_invalid==False), leave is_invalid==True as True
    if region_filter_list:
        condition = (
            ~df["region"].str.lower().isin([r.lower() for r in region_filter_list])
            | (df["modality"].isna())
            | (df["extracted_rad_events"] == "")
        ) & (~df["is_invalid"])
    else:
        # If region_filter_list is empty, skip the isin check and only consider modality
        condition = (df["modality"].isna()) | (df["extracted_rad_events"] == "") & (
            ~df["is_invalid"]
        )

    df.loc[condition, "is_invalid"] = True

    hadm_invalid_groups = df.groupby("hadm_id")["is_invalid"].all()
    invalid_hadm_ids = hadm_invalid_groups[hadm_invalid_groups].index.tolist()

    invalid_count = df["is_invalid"].sum()
    total_count = len(df)
    print(
        f"Number of invalid entries in radiology_events: {invalid_count} out of {total_count}"
    )

    print(
        f"Number of hadm_ids fully invalid in radiology_events: {len(invalid_hadm_ids)}"
    )

    return df, invalid_hadm_ids
