import pandas as pd


def parse_microbiology(microbiology_df):
    """
    Parse the microbiology dataframe by grouping the microbiology strings for each hadm_id, test_itemid, micro_specimen_id, and org_name.

    Args:
        microbiology_df (pd.DataFrame): The input dataframe containing microbiology data.

    Returns:
        pd.DataFrame: A dataframe with the grouped microbiology strings.
    """

    def _group_microbio_str(group):
        org_name = group["org_name"].iloc[0]
        assert all(group["org_name"] == org_name), (
            "org_name values are not the same within the group"
        )
        microbiology_str = ",\n".join(
            group["microbiology_str"].dropna().str.strip().unique()
        )
        microbiology_str = (
            f"{org_name}\n\nAntibiotic Susceptibility:\n{microbiology_str}"
        )
        return microbiology_str

    microbiology_df = microbiology_df.copy()
    group_cols = ["hadm_id", "test_itemid", "micro_specimen_id", "org_name"]
    microbiology_df["org_name"] = microbiology_df["org_name"].fillna("Unknown Organism")

    grouped_microbio_str = (
        microbiology_df.groupby(group_cols)
        .apply(_group_microbio_str)
        .reset_index(name="grouped_microbio_str")
    )
    microbiology_df = microbiology_df.merge(
        grouped_microbio_str, on=group_cols, how="left"
    )

    return microbiology_df
