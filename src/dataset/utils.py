import re
import warnings

import pandas as pd
from tqdm import tqdm

tqdm.pandas()
warnings.filterwarnings("default", category=UserWarning)


def map_note_id_to_name(note_id, note_id_to_parent_note_id, exam_name_map):
    # Radiology Util
    name = exam_name_map.get(note_id)
    if name is None:
        parent_note_id = note_id_to_parent_note_id.get(note_id)
        if parent_note_id:
            name = exam_name_map.get(parent_note_id, "")
        else:
            warnings.warn(f"Note ID {note_id} has no exam name and no parent_note_id")
            name = ""
    return name


def sanitize_hadm_texts(df, disease_names):
    invalid_visits = 0
    # pe_remove_diagnosis = 0

    def _sanitize_row(row):
        nonlocal invalid_visits

        # invalidate any extracted_history column where the patient report anamnesis already mentions the diagnosis...
        # ... already mentions the potential diagnosis
        if any(
            re.search(re.compile(disease_name, re.IGNORECASE), row["extracted_history"])
            for disease_name in disease_names
        ):
            row["extracted_history"] = ""
            invalid_visits += 1

        # Sanitize physical examination
        for disease_name in disease_names:
            row["pe"] = re.sub(
                re.compile(disease_name, re.IGNORECASE), "____", row["pe"]
            )

        return row

    df = df.progress_apply(_sanitize_row, axis=1)
    print(
        "Invalidated {} visits due to pathology reference in patient history".format(
            invalid_visits
        )
    )
    return df


def add_days(df: pd.DataFrame, start_col: pd.Series) -> pd.Series:
    """Calculate the number of days since first event (medication admission, lab, radiology, ...)"""
    days = (
        df.groupby("hadm_id")
        .progress_apply(
            lambda group: (
                (
                    pd.to_datetime(group[start_col])
                    - pd.to_datetime(group[start_col].min())
                ).dt.total_seconds()
                / (24 * 60 * 60)
            )  # days * minutes * seconds
        )
        .reset_index(level=0, drop=True)
    )
    # add 1 to the days column to make it 1-indexed
    return days.apply(lambda x: int(x) + 1)
