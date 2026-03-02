# in parts from: https://github.com/paulhager/MIMIC-Clinical-Decision-Making-Dataset/blob/main/dataset/procedures.py

import re


def _extract_procedure_from_discharge_summary(row):
    # Extracts everything after the "Major Surgical or Invasive Procedure:" line until the next empty line
    # Returns a list of procedures

    # from the discharge_text dataframe rows get the text columns
    discharge_summary = row["text"]

    procedure_substrings = [
        "Major Surgical or Invasive Procedure:",
        "PROCEDURES:",
        "PROCEDURE:",
        "Major Surgical ___ Invasive Procedure:",
        "___ Surgical or Invasive Procedure:",
        "INVASIVE PROCEDURE ON THIS ADMISSION:",
        "Major ___ or Invasive Procedure:",
        "MAJOR SURGICAL AND INVASIVE PROCEDURES PERFORMED THIS DURING\nADMISSION:",
    ]
    for substring in procedure_substrings:
        pattern = rf"{re.escape(substring)}.*?\n\s*\n"
        match = re.search(pattern, discharge_summary, re.DOTALL)
        if match:
            procedures_string = match.group(0)

            # Remove section title
            procedures_string = procedures_string.replace(substring, "")

            # Replace newline with space to make one sentence
            procedures_string = procedures_string.replace("\n", " ")

            # Split on delimiters
            procedures = re.split(r"\: |, |\. | - ", procedures_string)

            # Clean
            procedures = [proc.strip() for proc in procedures if proc.strip() != ""]
            return procedures
    print("No procedures found for {}".format(row.hadm_id))
    return []


def extract_procedures(discharge):
    discharge["procedures_from_discharge_letter"] = discharge.progress_apply(
        _extract_procedure_from_discharge_summary, axis=1
    )
    return discharge
