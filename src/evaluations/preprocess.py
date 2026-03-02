# imports
import sys

sys.path.append("..")
import copy
import json

import pandas as pd
from dataset.mimic_dataset import MIMIC_Dataset, MIMIC_Hadm_Dataset
from termcolor import colored

pd.set_option("display.max_columns", None)

from collections import defaultdict

from evaluations.objectives import *


def valid(item):
    # check if item is not NaN and not "___"
    return pd.notna(item) and item != "___"


def read_single_jsonl(file_path):
    """
    Reads a single jsonl file and returns the first (and only) entry.
    """
    with open(file_path, "r") as file:
        return [json.loads(line) for line in file][0]


def load_one_result(outputs_path, dataset: MIMIC_Dataset):
    """
    Loads a single result from a jsonl file and returns the medical assistant outputs and patient data.
    """
    evaluable_outputs = read_single_jsonl(outputs_path)
    med_assistant_outputs = evaluable_outputs["med_assistant"]
    dataset_idx = evaluable_outputs["metadata"]["hadm_id"]

    patient_data = dataset[dataset_idx]

    assert (
        patient_data.hadm_id == evaluable_outputs["metadata"]["hadm_id"]
    ), "Patient data and evaluable outputs do not match"

    return med_assistant_outputs, patient_data, evaluable_outputs["metadata"]


class PatientGroundTruth:
    """
    A class that contains the ground truth for a patient.
    """

    def __init__(self, patient_data: MIMIC_Hadm_Dataset):
        self.patient_data = patient_data
        self.diagnosis = self.fetch_diagnosis_gt()
        self.lab_results, self.lab_events = (
            self.fetch_lab_results_gt()
        )  # Blood and Urine
        self.urine_results, self.urine_events = self.fetch_lab_results_gt()
        self.radiology_results, self.radiology_events = (
            self.fetch_radiology_results_gt()
        )
        self.procedures = self.fetch_procedure_results_gt()
        self.microbiology_results, self.microbiology_events = (
            self.fetch_microbiology_results_gt()
        )
        self.pe_results = self.fetch_pe_results_gt()
        self.admission_medication = self.fetch_admission_medication_results_gt()
        self.hospital_medication = self.fetch_hospital_admission_medication_results_gt()

    def __str__(self):
        lines = []
        lines.append(
            colored(f"Patient `hadm_id`: {self.patient_data.hadm_id}", "green")
        )
        lines.append(colored("=== Patient Ground Truth ===", "cyan", attrs=["bold"]))
        lines.append("")

        lines.append(colored("Diagnosis:", "blue", attrs=["bold"]))
        lines.append(f"  {self.diagnosis}\n")

        lines.append(colored("Lab Results:", "blue", attrs=["bold"]))
        if self.lab_results:
            lines.append(f"{self.lab_results}\n")

        lines.append(colored("Radiology:", "blue", attrs=["bold"]))
        if self.radiology_events:
            lines.append(colored("Radiology Events:", "magenta", attrs=["bold"]))
            lines.append(f"{self.radiology_events}\n")
        if self.radiology_results:
            lines.append(colored("Radiology Results:", "magenta", attrs=["bold"]))
            lines.append(f"{self.radiology_results}\n")

        lines.append(colored("Procedures:", "blue", attrs=["bold"]))
        for p in self.procedures:
            icd_code = p["icd_code"] if p["icd_code"] else "N/A"
            icd_version = p["icd_version"] if p["icd_version"] else "N/A"
            lines.append(
                f"  • {p['long_title']} (ICD Code: {icd_code}, Version: {icd_version})"
            )
        lines.append("")

        lines.append(colored("Microbiology Results:", "blue", attrs=["bold"]))
        if self.microbiology_results:
            lines.append(f"{self.microbiology_results}\n")

        lines.append(colored("Physical Examination Results:", "blue", attrs=["bold"]))
        lines.append(f"  {self.pe_results}\n")

        lines.append(colored("Admission Medication:", "blue", attrs=["bold"]))
        lines.append(f"  {self.admission_medication}\n")

        lines.append(colored("Hospital Medication:", "blue", attrs=["bold"]))
        for m in self.hospital_medication:
            drug_str = (
                f"  • {m['drug_name']}: {m['dosage_value']}{m['dosage_unit']} "
                f"every {m['period']}{m['period_unit']} (Frequency: {m['frequency']}) via {m['route']}"
            )
            lines.append(drug_str)
        lines.append("")

        lines.append(colored("Anamnesis Summary:", "blue", attrs=["bold"]))
        extracted_history = (
            self.patient_data.history_pe_admedication_diagnosis["extracted_history"]
            .values[0]
            .strip()
        )
        if len(extracted_history) > 80:
            extracted_history = "\n".join(
                extracted_history[i : i + 80]
                for i in range(0, len(extracted_history), 80)
            )
        lines.append(extracted_history)

        lines.append(colored("Complete Discharge Letter Text:", "red", attrs=["bold"]))
        lines.append(
            self.patient_data.history_pe_admedication_diagnosis["text"]
            .values[0]
            .strip()
        )

        return "\n".join(lines)

    def fetch_diagnosis_gt(self):
        """
        Returns the diagnosis for the patient.
        """
        return self.patient_data.diagnosis_icd.long_title.values[0]

    def fetch_lab_results_gt(self):
        """
        Returns the results for all unique (by itemid) lab events performed within the first 24hrs of the first lab event in ascending order.
        """
        self.patient_data.lab_events["charttime"] = pd.to_datetime(
            self.patient_data.lab_events["charttime"]
        )
        filtered_lab_events = self.patient_data.lab_events[
            self.patient_data.lab_events["charttime"]
            < (self.patient_data.lab_events["charttime"].min() + pd.Timedelta(days=1))
        ]
        unique_earliest_lab_events = filtered_lab_events.loc[
            filtered_lab_events.groupby("itemid")["charttime"].idxmin()
        ]

        reconstructed_lab_events = []
        requested_lab_events = defaultdict(set)
        for _, result in unique_earliest_lab_events.iterrows():
            if valid(result["valuenum"]):
                value = result["valuenum"]
            elif valid(result["value"]):
                value = result["value"]
            elif valid(result["flag"]):
                value = result["flag"]
            else:
                value = pd.NA  # Fallback to pd.NA if all fields are invalid

            llm_like_input = f"{result['label']}: {value} {result['valueuom_x']} ({result['ref_range_lower']} - {result['ref_range_upper']})"
            reconstructed_lab_events.append(llm_like_input)

            requested_lab_events[result["fluid"]].add(result["label"])

        reconstructed_lab_events = "\n".join(reconstructed_lab_events)
        return reconstructed_lab_events, requested_lab_events

    def fetch_radiology_results_gt(self):
        self.patient_data.radiology["charttime"] = pd.to_datetime(
            self.patient_data.radiology["charttime"]
        )
        filtered_radiology = self.patient_data.radiology

        filtered_radiology = filtered_radiology.sort_values(
            by="charttime", ascending=True
        )
        if filtered_radiology.empty:
            reconstructed_radiology_events = "Radiology report not available."
            requested_radiology_events = []
        else:
            requested_radiology_events = []
            reconstructed_radiology_events = []
            for _, result in filtered_radiology.iterrows():
                res = f"Radiology Report ({result['modality']} {result['region']}):\n{result['extracted_rad_events']}"
                reconstructed_radiology_events.append(res)
                requested_radiology_events.append(
                    {"modality": result["modality"], "region": result["region"]}
                )

        reconstructed_radiology_events = "\n".join(reconstructed_radiology_events)
        return reconstructed_radiology_events, requested_radiology_events

    def fetch_procedure_results_gt(self):
        """
        Returns a list of dictionaries containing the procedure information,
        from both the discharge letter and the icd code mapping.
        """
        # get procedures from discharge letter that are free text without code mapping
        procedures_list_from_discharge = [
            procedure
            for procedure in self.patient_data.history_pe_admedication_diagnosis[
                "procedures_from_discharge_letter"
            ].values[0]
            if procedure != "___"
        ]
        procedures_list_from_discharge = [
            {"icd_code": None, "icd_version": None, "long_title": procedure}
            for procedure in procedures_list_from_discharge
        ]

        # get procedures from icd code mapping
        icd_procedures_list = self.patient_data.procedures_icd.apply(
            lambda row: {
                "icd_code": row["icd_code"],
                "icd_version": row["icd_version"],
                "long_title": row["long_title"],
            },
            axis=1,
        ).tolist()

        procedures = procedures_list_from_discharge + icd_procedures_list
        return procedures

    def fetch_microbiology_results_gt(self):
        """
        Returns the microbiology results for all unique (by test_name) microbiology tests performed within the first 24hrs of the first test in ascending order.
        """
        self.patient_data.microbiology["charttime"] = pd.to_datetime(
            self.patient_data.microbiology["charttime"]
        )
        filtered_microbiology = self.patient_data.microbiology[
            self.patient_data.microbiology["charttime"]
            < (self.patient_data.microbiology["charttime"].min() + pd.Timedelta(days=1))
        ]
        filtered_microbiology = filtered_microbiology.sort_values(
            by="charttime", ascending=True
        )
        filtered_microbiology_list = (
            filtered_microbiology["test_name"]
            + ":\n"
            + filtered_microbiology["grouped_microbio_str"]
        ).tolist()
        return (
            "\n".join(filtered_microbiology_list),
            filtered_microbiology["test_name"].tolist(),
        )

    def fetch_pe_results_gt(self):
        """
        Return physical examination results from the discharge letter.
        """
        return self.patient_data.history_pe_admedication_diagnosis.pe.values[0].strip()

    def fetch_admission_medication_results_gt(self):
        """
        Return medication that the patient was taking when coming to the hospital.
        """
        return self.patient_data.history_pe_admedication_diagnosis.admission_medication.values[
            0
        ].strip()

    def fetch_hospital_admission_medication_results_gt(self):
        """
        Return medication results from the medication table, that were prescribed
        to the patient during their hospital admission within the first 24hrs.
        """
        filtered_medication = self.patient_data.medication[
            self.patient_data.medication["days"] == 1
        ]

        medication_list = []
        for _, row in filtered_medication.iterrows():
            medication_dict = {
                "drug_name": row["drug"],
                "dosage_text": row["prod_strength"],
                "dosage_value": row["dose_val_rx"],
                "dosage_unit": row["dose_unit_rx"],
                "period": 1,
                "period_unit": "d",
                "frequency": row["doses_per_24_hrs"],  # x times from doses_per_24_hrs
                "route": row["route"],
            }
            medication_list.append(medication_dict)
        return medication_list


def extract_tool_use(med_assistant_outputs):
    """
    Extracts the tool use from the medical assistant outputs into structured format for comparison
    to the MIMIC IV ground truth.
    """
    tools_used = []
    for idx1, turn in enumerate(med_assistant_outputs):
        if turn["role"] == "assistant" and "tool_calls" in turn.keys():
            for _, tool_call in enumerate(
                turn["tool_calls"]
            ):  # CAVE: useless because parallel function calling = False (for now)
                called = tool_call["function"]["name"]
                # try:
                called_args = json.loads(tool_call["function"]["arguments"])
                returned = med_assistant_outputs[idx1 + 1]
                assert (
                    "tool_call_id" in returned.keys() and returned["name"] == called
                ), "Tool call and tool return do not align."
                returned = returned["content"]
                flattened_called_args = _flatten_tool_args(called_args)
                tool_info = dict(
                    called=called_args,
                    called_args=flattened_called_args,
                    returned=returned,
                )
                tools_used.append({tool_call["function"]["name"]: tool_info})
                # except:
                #     tools_used.append(
                #         {tool_call["function"]["name"]: "Tool was not used correctly."}
                #     )
    return tools_used


def _flatten_tool_args(called_args):
    """
    Flattens the tool arguments with edge case handling for different tools.
    """
    # handle blood values for now
    lab_val_args = called_args.get("lab_values", None)
    if lab_val_args is not None:
        requested_lab_values = []
        for lab_val_arg in lab_val_args:
            requested_lab_values.append(lab_val_arg["lab_value"])
        return requested_lab_values

    # handle urine values for now
    urine_val_args = called_args.get("urine_values", None)
    if urine_val_args is not None:
        requested_urine_values = []
        for urine_val_arg in urine_val_args:
            requested_urine_values.append(urine_val_arg["urine_value"])
        return requested_urine_values

    # handle microbiology tests
    microbiology_val_args = called_args.get("microbiology_tests", None)
    if microbiology_val_args is not None:
        requested_microbiology_tests = []
        for microbiology_val_arg in microbiology_val_args:
            requested_microbiology_tests.append(
                microbiology_val_arg["microbiology_value"]
            )
        return requested_microbiology_tests

    # handle radiology
    if "modality" in called_args.keys() and "region" in called_args.keys():
        called_args2 = copy.deepcopy(called_args)
        called_args2.pop("info", None)
        return called_args2

    # handle medications
    if "medications" in called_args.keys():
        return called_args["medications"]

    # base case
    else:
        return called_args  # for those that are empty like PE, plan


def merge_called_args(med_assistant_tools_used):
    """
    Merge the requests if tools were called multiple times,
    to facilitate evaluation.
    """
    called_args_dict = defaultdict(list)
    for item in med_assistant_tools_used:
        examination_name = list(item.keys())[0]
        called_args = list(item.values())[0]["called_args"]
        called_args_dict[examination_name].append(called_args)

    # if its a nested list, flatten it, ignore if its list of dicts or so
    for key, value in called_args_dict.items():
        if isinstance(value[0], list):
            called_args_dict[key] = sum(value, [])
    return called_args_dict


_GROUND_TRUTH_TO_ASSISTANT_ALIGNS = {
    # Mapping from the ground truth to the assistant's tool calls.
    "diagnosis": "Finish",
    "pe_results": "PhysicalExamination",
    "lab_events": "LabRequestList",
    "urine_events": "UrineRequestList",
    "microbiology_events": "MicrobiologyRequestList",
    "hospital_medication": "MedicationRequestList",
    "radiology_events": "RadiologyRequestFHIR",
    "procedures": "ProcedureRequestFHIR",
}


def match_ground_truth_and_assistant(med_called_args, patient_gt):
    """
    Matches the ground truth to the assistant's tool calls.
    """
    MatchedResults = lambda ground_truth, assistant: {  # noqa: E731
        "ground_truth": ground_truth,
        "assistant": assistant,
    }

    results = {}

    for ground_truth_key, tool_name in _GROUND_TRUTH_TO_ASSISTANT_ALIGNS.items():
        ground_truth_value = getattr(patient_gt, ground_truth_key)
        assistant_output = med_called_args.get(tool_name, None)
        result = MatchedResults(ground_truth_value, assistant_output)
        results[ground_truth_key] = result

    return results
