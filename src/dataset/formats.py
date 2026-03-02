from pathlib import Path

import pandas as pd
from tqdm import tqdm

tqdm.pandas()


def valid(item):
    # check if item is not NaN and not "___"
    return pd.notna(item) and item != "___"


def format_lab_value(df: pd.DataFrame, new_col_name: str = "lab_event_str"):
    """Format Laboratory values into string represntation: value unit or flag"""

    def _format_row(value_num, value_uom, value, flag):
        if valid(value_num):
            return f"{value_num} {value_uom}" if valid(value_uom) else str(value_num)
        elif valid(value):
            return f"{value} {value_uom}" if valid(value_uom) else str(value)
        elif valid(flag):
            return str(flag)
        return pd.NA

    df[new_col_name] = df.progress_apply(
        lambda row: _format_row(
            row["valuenum"], row["valueuom"], row["value"], row["flag"]
        ),
        axis=1,
    )
    return df


def format_microbiology_value(df: pd.DataFrame, new_col_name: str = "microbiology_str"):
    "Format microbiology values into a string represntation: bacteria antibiotics R/S/... comment"

    def _join_components(row):
        components = [
            # row["org_name"] if valid(row["org_name"]) else "",
            row["ab_name"] if valid(row["ab_name"]) else "",
            row["interpretation"] if valid(row["interpretation"]) else "",
            row["comments"] if valid(row["comments"]) else "",
        ]
        return ", ".join(filter(None, components)) if any(components) else pd.NA

    df[new_col_name] = df.progress_apply(_join_components, axis=1)
    return df
