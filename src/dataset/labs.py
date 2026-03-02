import pandas as pd
from paths import D_LABITEMS_TO_LOINC_PATH


def match_lab_events_to_loinc(lab_events_hadm_ids):
    # read in the d_labitems to loinc omop mappings dataframe
    # download from here: https://github.com/MIT-LCP/mimic-code/blob/e39825259beaa9d6bc9b99160049a5d251852aae/mimic-iv/mapping/d_labitems_to_loinc.csv
    d_labitems_to_loinc = pd.read_csv(D_LABITEMS_TO_LOINC_PATH)
    d_labitems_to_loinc.rename(
        columns={"itemid (omop_source_code)": "itemid"}, inplace=True
    )

    lab_events_h_loinc_omop = lab_events_hadm_ids.merge(
        d_labitems_to_loinc.iloc[:, :-1],  # remove some unnecessary columns
        left_on=["itemid", "label", "fluid", "category"],
        right_on=["itemid", "label", "fluid", "category"],
        how="left",
    )
    return lab_events_h_loinc_omop
