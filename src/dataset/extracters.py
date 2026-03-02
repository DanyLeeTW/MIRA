import re

import pandas as pd


def regex_extracter(text, regex):
    # from: https://github.com/paulhager/MIMIC-Clinical-Decision-Making-Dataset/blob/main/dataset/utils.py
    """
    Extract text using regex. If no match, return original text.

    Args:
        text (str): Text to extract from
        regex (str): Regex to use for extraction

    Returns:
        text (str): Extracted text which matches entire regex or original text if no match
        success (bool): True if match found, False otherwise
    """
    try:
        return re.search(regex, text).group(0), True
    except Exception:
        return text, False


def extract_history(text):
    # from: https://github.com/paulhager/MIMIC-Clinical-Decision-Making-Dataset/blob/main/dataset/discharge.py
    """
    Extract initial complaint (Patient History) from discharge summary text. Extract from "history of present illness:" field to "physical exam" field using regex. Case insensitive.

    Args:
        text (str): Discharge summary text

    Returns:
        text (str): Extracted patient history
    """
    text = text.replace("\n", " ")

    success = False
    i = 0
    pe_strings = [
        "physical exam:",
        "physical examination:",
        "physical ___:",
        "pe:",
        "pe ___:",
        "(?:pertinent|___) results:",
        "hospital course:",
    ]
    while not success and i < len(pe_strings):
        regex = re.compile(
            f"(?:history|___) of present(?:ing)? illness:.*?{pe_strings[i]}",
            re.IGNORECASE | re.DOTALL,
        )
        text, success = regex_extracter(text, regex)
        i += 1
    if not success:
        # print(f"No history match found for: {str(text)[:50]}")
        return ""
        # raise Warning("No history match found")

    # remove header
    text = re.sub(
        re.compile("history of present(?:ing)? illness:", re.IGNORECASE), "", text
    )

    # remove terminal string
    for pe_str in pe_strings:
        text = re.sub(re.compile(pe_str, re.IGNORECASE), "", text)

    return text


def extract_physical_examination(text):
    # from: https://github.com/paulhager/MIMIC-Clinical-Decision-Making-Dataset/blob/main/dataset/discharge.py
    # extract from "physical exam:" to "pertinent results:" using regex. Case insensitive
    text = text.replace("\n", " ")
    success = False
    i = 0
    pe_strings = [
        "physical exam:",
        "physical examination:",
        "physical ___:",
        "pe:",
        "pe ___:",
        "pertinent results:",
    ]
    while not success and i < len(pe_strings):
        terminal_str = "pertinent results:"
        if terminal_str not in text.lower():
            terminal_str = "brief hospital course:"
        regex = re.compile(
            f"{pe_strings[i]}.*?{terminal_str}", re.IGNORECASE | re.DOTALL
        )
        text, success = regex_extracter(text, regex)
        i += 1
    if not success:
        return ""

    # remove header
    for pe_str in pe_strings:
        text = re.sub(re.compile(pe_str, re.IGNORECASE), "", text)

    # remove terminal string
    text = re.sub(re.compile("pertinent results:", re.IGNORECASE), "", text)
    text = re.sub(re.compile("brief hospital course:", re.IGNORECASE), "", text)

    # remove everything after discharge pe
    text = re.sub(re.compile("at discharge.*", re.IGNORECASE), "", text)
    text = re.sub(re.compile("upon discharge.*", re.IGNORECASE), "", text)
    text = re.sub(re.compile("on discharge.*", re.IGNORECASE), "", text)
    text = re.sub(re.compile("discharge.*", re.IGNORECASE), "", text)

    return text


def parse_report(report):
    # Split the report into lines
    lines = report.strip().split("\n")

    # Initialize the dictionary
    report_dict = {}

    # Check if the first line ends with a colon and if not, add it (typically imaging modality)
    if lines[0].isupper() and lines[0].strip()[-1] != ":":
        lines[0] = lines[0].strip() + ":"

    # Check if theres a line of only capital letters to be included (typically imaging modality)
    for i, line in enumerate(lines):
        if line.isupper() and ":" not in line:
            lines[i] = line.strip() + ":"

    # Rejoin the remaining lines and parse the report as before
    report = "\n".join(lines)
    pattern = r"(?m)^([A-Z \t,._-]+):((?:(?!^[A-Z \t,._-]+:).)*)"
    sections = re.findall(pattern, report, re.DOTALL)

    # Add the sections to the dictionary
    for section in sections:
        report_dict[section[0].strip()] = section[1].strip()

    return report_dict


def extract_rad_events(text):
    # adapted from https://github.com/paulhager/MIMIC-Clinical-Decision-Making-Framework/blob/main/dataset/radiology.py
    # as we apply this to a datraframe row-wise, only one text and no list
    bad_rad_fields = [
        "CLINICAL HISTORY",
        "MEDICAL HISTORY",
        "CLINICAL INFORMATION",
        "COMMENT",
        "CONCLUSION",
        "HISTORY",
        "CLINICAL INDICATION",
        "INDICATION",
        "OPERATORS",
        "REFERENCE",
        "DATE",
    ]
    # Convert report to dictionary of sections. Also recieve special lines to be added to beginning
    sections = parse_report(text)
    text_clean = ""
    info_added = False
    for field in sections:
        # only add field if it does not start with any bad field
        if not any([field.startswith(bad_field) for bad_field in bad_rad_fields]):
            if sections[field]:
                info_added = True
            text_clean += "{}:\n{}\n\n".format(field, sections[field])
        else:
            # print('Removed: {}'.format(field))
            pass
    # Could be that the only usable string was a headline field without any info. Want to remove these
    if not info_added:
        text_clean = ""
    return text_clean


def extract_admisson_medication(
    row: pd.Series, ed_stays: pd.DataFrame, medrecon: pd.DataFrame, counter: dict
) -> str:
    """Extracts the admission medication information from the discharge letter text.
    If the information is not found in the discharge letter, it falls back to using the medrecon table.

    Parameters:
    row (pd.Series): A row from the discharge DataFrame containing the discharge letter text and hadm_id.
    counter (dict): A dictionary to keep track of the extraction method used.

    Returns:
    str: A string containing the medication information on admission."""

    def _extract_medication_from_ed(hadm_id: int) -> str:
        # This is a fallback in case the discharge letter does not contain the medication information
        # We use the medrecon table to get the medication information
        # We return the medication names without duplicates
        try:
            stay_id = ed_stays[ed_stays.hadm_id == hadm_id].stay_id.values[0]
            medication = medrecon[medrecon.stay_id == stay_id].name.to_list()
            medication = set(medication)  # not really sure how to handle this but ...
            # ... as we do not have dosage instructions etc. we just return the medication names without duplicates
            return "\n".join([med.capitalize() for med in medication])
        except:  # noqa: E722
            return pd.NA

    starter_headers = ["Medications on Admission:", "___ on Admission:"]
    end_headers = ["Discharge Medications:", "___ Medications:"]

    text = row["text"]
    hadm_id = row[
        "hadm_id"
    ]  # in case the text is not found in the discharge letter and we need to use the medrecon table

    # Combine start headers and end headers into a single regex pattern
    start_pattern = re.compile(
        "|".join([re.escape(header) for header in starter_headers]), re.IGNORECASE
    )
    end_pattern = re.compile(
        r"(\n\s*\n\s*)|" + "|".join([re.escape(header) for header in end_headers]),
        re.IGNORECASE,
    )

    # Search for the start header
    start_match = start_pattern.search(text)
    # fallback to using the documentation from the medrecon ICU table
    if not start_match:
        counter["extract_from_medrecon"] += 1
        return _extract_medication_from_ed(hadm_id)

    # Extract text starting from the end of the start header
    start_index = start_match.end()
    medication_text = text[start_index:]

    # Search for the end header or two empty lines in the remaining text
    end_match = end_pattern.search(medication_text)
    if end_match:
        end_index = end_match.start()
        counter["extract_from_discharge_letter"] += 1
        return medication_text[:end_index].strip()
    else:
        # fallback to using the documentation from the medrecon ICU table
        counter["extract_from_medrecon"] += 1
        return _extract_medication_from_ed(hadm_id)
