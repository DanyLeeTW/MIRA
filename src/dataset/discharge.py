# adapted in parts from: https://github.com/paulhager/MIMIC-Clinical-Decision-Making-Dataset/blob/main/dataset/discharge.py

import pandas as pd

def extract_diagnosis_from_discharge(discharge: pd.DataFrame) -> pd.DataFrame:
    # extract the diagnosis from the discharge text or return an empty string if not possible

    failed_to_extract_diagnosis: int = 0

    def _last_substring_index(larger_string: str, substring: str) -> int:
        return larger_string.rfind(substring)

    def _extract_from_row(row):
        nonlocal failed_to_extract_diagnosis
        try:
            # get the discharge text column from the row
            text = row["text"]
            start_headers = ["discharge diagnosis:", "___ diagnosis:"]
            end_headers = [
                "discharge condition:",
                "___ condition:",
                "condition:",
                "procedure:",
                "procedures:",
                "invasive procedure on this admission:",
            ]
            start = 0
            for start_header in start_headers:
                if start_header in text.lower():
                    pos_start = _last_substring_index(text.lower(), start_header)
                    if pos_start != -1:
                        start = max(start, pos_start + len(start_header))
            if not start:
                # As last resort match against empty string which sometimes has diagnosis for some reason
                start_header = "\n___:"
                if start_header in text.lower():
                    pos_start = _last_substring_index(text.lower(), start_header)
                    if pos_start != -1:
                        start = pos_start
                else:
                    raise Exception("No start header found")
            end = 0
            for end_header in end_headers:
                if end_header in text.lower():
                    pos_end = _last_substring_index(text.lower(), end_header)
                    if pos_end != -1:
                        end = max(end, pos_end)
                    break
            if not end:
                raise Exception("No end header found")
            
            discharge_diagnosis = text[start:end]
            return discharge_diagnosis.strip()
        
        except Exception as e:
            # if cannot extract diagnosis from text, return empty string
            failed_to_extract_diagnosis += 1
            return ""
    
    discharge["discharge_diagnosis_from_text"] = discharge.progress_apply(
        _extract_from_row, axis=1
    )

    print(f"Failed to extract diagnosis from {failed_to_extract_diagnosis} rows")
    return discharge
