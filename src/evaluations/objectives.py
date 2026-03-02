import json
from dataclasses import dataclass
from enum import Enum
from typing import List

from openai import OpenAI
from pydantic import BaseModel, Field


@dataclass
class Evaluation:
    """
    A class to store the evaluation results for each objective.
    """

    diagnosis: dict | None = None
    physical_examination: bool | None = None
    blood_requests: dict | None = None
    urine_requests: dict | None = None
    radiology_events: dict | None = None
    procedures: dict | None = None
    microbiology_events: dict | None = None
    hospital_medication: dict | None = None

    def __str__(self):
        return (
            f"Evaluation(\n"
            f"  diagnosis={self.diagnosis},\n"
            f"  physical_examination={self.physical_examination},\n"
            f"  blood_requests={json.dumps(self.blood_requests, indent=2)},\n"
            f"  urine_requests={json.dumps(self.urine_requests, indent=2)},\n"
            f"  radiology_events={json.dumps(self.radiology_events, indent=2)},\n"
            f"  procedures={json.dumps(self.procedures, indent=2)},\n"
            f"  microbiology_events={json.dumps(self.microbiology_events, indent=2)},\n"
            f"  hospital_medication={json.dumps(self.hospital_medication, indent=2)}\n"
            f")"
        )


def evalaute_diagnosis(client: OpenAI, matched_results: dict, diagnosis: str) -> dict:
    """
    Evaluates the diagnosis.
    """

    gt = matched_results.get("diagnosis", {}).get("ground_truth", None)
    assistant = matched_results.get("diagnosis", {}).get("assistant", None)

    if gt is None or assistant is None:
        return {"reasoning": "", "match": False}

    else:
        assistant = assistant[0]["diagnosis"]

    class DiagnosisMatch(BaseModel):
        reasoning: str = Field(description="The reasoning for the match decision.")
        match: bool = Field(
            description="True if the diagnosis matches, False otherwise."
        )

    user_prompt = f"""
    Ground Truth: {gt}
    Assistant: {assistant}
    Matching criterion: {diagnosis}
    """


    system_prompt = """You are a medical expert. You will be provided with a ground truth diagnosis and an assistant's diagnosis. These can be on different levels of specificity. Therefore you also receive a matching criterion. Your task is to determine if the assistant's diagnosis matches the ground truth diagnosis based on the matching criterion.
Respond with the given json schema, providing a reasoning for your answer and a boolean decision (True if they match, False otherwise).
Mostly consider the overall `Matching criterion`, not any specific details. Decide false if the ground truth and assistand diagnoses conflict each other.
    Example 1:
        Ground Truth: `Appendicitis`
        Assistant: `Complicated appendicitis with local peritonitis and perforation`
        Matching criterion: `appendicitis`
        Decision: `True`
    Example 2:
        Ground Truth: `Appendicitis`
        Assistant: `Appendicitis with local peritonitis`
        Matching criterion: `appendicitis`
        Decision: `True`
    Example 3:
        Ground Truth: `Acute appendicitis with appendicolith`
        Assistant: `Appendicitis without local peritonitis`
        Matching criterion: `appendicitis`
        Decision: `True`
    Example 4:
        Ground Truth: `Acute cholecystitis`
        Assistant: `Appendicitis with local peritonitis`
        Matching criterion: `cholecystitis`
        Decision: `False`
    Example 5:
        Ground Truth: `Acute cholecystitis`
        Assistant: `Choledocholithiasis with possible cholecystitis`
        Matching criterion: `cholecystitis`
        Decision: `True`
    Example 6:
        Ground Truth: `other pulmonary embolism and infarction`
        Assistant: `massive pulmonary embolism with right ventricular strain`
        Matching criterion: `Pulmonary Embolism`
        Decision: `True`
    """

    completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=DiagnosisMatch,
        temperature=0.1,
    )

    diagnosis_eval = {}
    diagnosis_eval["reasoning"] = completion.choices[0].message.parsed.reasoning  # type: ignore
    diagnosis_eval["match"] = completion.choices[0].message.parsed.match  # type: ignore

    return diagnosis_eval


def evaluate_pe_request(matched_results: dict):
    """
    Evaluates the physical examination request.
    Current implementation:
    - Check if the assistant requested a physical examination.
    """
    assistant = matched_results.get("pe_results", {}).get("assistant", None)
    # print("evaluate_pe_request", assistant)
    return assistant is not None


def evaluate_blood_requests(matched_results: dict):
    """
    Evaluates the lab requests.
    Current implementation:
    - Check the overlap in lab values between assistant and gt.
    """
    gt = matched_results.get("lab_events", {}).get("ground_truth", None)
    assistant = matched_results.get("lab_events", {}).get("assistant", None)
    gt = gt.get("Blood", None)

    if gt is None:
        # convert to an empty list so that we can take the set difference
        gt = []

    if assistant is None:
        assistant = []

    gt, assistant = set(gt), set(assistant)
    # print("evaluate_blood_requests assistant", assistant)
    # print("evaluate_blood_requests gt", gt)

    overlap_results = {}
    overlap_results["gt_and_assistant"] = list(gt & assistant)
    overlap_results["gt_only"] = list(gt - assistant)
    overlap_results["assistant_only"] = list(assistant - gt)

    return overlap_results


def evaluate_urine_requests(matched_results: dict):
    """
    Evaluates the urine requests.
    Current implementation:
    - Check the overlap in lab values between assistant and gt.
    """
    gt = matched_results.get("urine_events", {}).get("ground_truth", None)
    assistant = matched_results.get("urine_events", {}).get("assistant", None)
    gt = gt.get("Urine", None)

    if gt is None:
        # convert to an empty list so that we can take the set difference
        gt = []

    if assistant is None:
        assistant = []

    gt, assistant = set(gt), set(assistant)

    # print("evaluate_urine_requests assistant", assistant)
    # print("evaluate_urine_requests gt", gt)

    overlap_results = {}
    overlap_results["gt_and_assistant"] = list(gt & assistant)
    overlap_results["gt_only"] = list(gt - assistant)
    overlap_results["assistant_only"] = list(assistant - gt)

    return overlap_results


def measure_overlap(gt_data, assistant_data):
    """
    Measures the overlap between the ground truth and the assistant's data.
    """
    overlap_results = {
        "gt_and_assistant": [],  # requested by both gt and assistant
        "gt_only": [],  # requested by gt but not assistant
        "assistant_only": [],  # requested by assistant but not gt
    }

    for gt_item in gt_data:
        if gt_item in assistant_data:
            overlap_results["gt_and_assistant"].append(gt_item)
        else:
            overlap_results["gt_only"].append(gt_item)

    for assistant_item in assistant_data:
        if assistant_item not in gt_data:
            overlap_results["assistant_only"].append(assistant_item)

    return overlap_results


def evaluate_radiology_requests(matched_results: dict):
    """
    Evaluates the radiology requests.
    Current implementation:
    - Check the overlap in radiology requests between assistant and gt.
    """
    gt = matched_results.get("radiology_events", {}).get("ground_truth", None)
    assistant = matched_results.get("radiology_events", {}).get("assistant", None)

    # print("evaluate_radiology_requests assistant", assistant)
    # print("evaluate_radiology_requests gt", gt)

    if gt is None:
        gt = []

    if assistant is None:
        assistant = []

    overlap_results = measure_overlap(gt, assistant)
    return overlap_results


def evaluate_procedure_requests(matched_results: dict):
    """
    Evaluates the procedure requests.
    Current implementation:
    - Check the overlap in procedure requests between assistant and gt.
    """
    gt = matched_results.get("procedures", {}).get("ground_truth", None)
    assistant = matched_results.get("procedures", {}).get("assistant", None)

    # print("evaluate_procedure_requests assistant", assistant)
    # print("evaluate_procedure_requests gt", gt)

    if gt is None:
        gt = []

    if assistant is None:
        assistant = []

    overlap_results = measure_overlap(gt, assistant)
    return overlap_results


def evaluate_microbiology_requests(matched_results: dict):
    """
    Evaluates the microbiology requests.
    Current implementation:
    - Check the overlap in microbiology requests between assistant and gt.
    """
    gt = matched_results.get("microbiology_events", {}).get("ground_truth", None)
    assistant = matched_results.get("microbiology_events", {}).get("assistant", None)

    # print("evaluate_microbiology_requests assistant", assistant)
    # print("evaluate_microbiology_requests gt", gt)

    if gt is None:
        gt = []

    if assistant is None:
        assistant = []

    overlap_results = measure_overlap(gt, assistant)
    return overlap_results


def evaluate_medication_requests(client: OpenAI, matched_results: dict):
    """
    Use an LLM call to evaluate the medication requests.
    """

    gt = matched_results.get("hospital_medication", {}).get("ground_truth", None)
    assistant = matched_results.get("hospital_medication", {}).get("assistant", None)

    # print("evaluate_medication_requests assistant", assistant)
    # print("evaluate_medication_requests gt", gt)

    if not gt or not assistant:
        overlap_results: dict[str, list] = {
            "gt_and_assistant": [],  # requested by both gt and assistant
            "gt_only": [],  # requested by gt but not assistant
            "assistant_only": [],  # requested by assistant but not gt
        }
        return {
            "standardized_drug_names": overlap_results,
            "drug_classes": overlap_results,
        }

    ground_truth_drug_names = [drug["drug_name"] for drug in gt]
    ai_output_drug_names = [drug["drug_name"] for drug in assistant]

    all_drug_names = list(set(ground_truth_drug_names + ai_output_drug_names))

    def _create_drug_model(all_drug_names: List[str]):

        class DrugName(str, Enum):
            _ignore_ = "i drug_name"
            for i, drug_name in enumerate(all_drug_names, start=1):
                locals()[f"_{i}"] = drug_name

        class Drug(BaseModel):
            original_drug_name: DrugName
            standardized_drug_name: str
            drug_class: str

        return Drug

    Drug = _create_drug_model(all_drug_names)

    class StandardizationResponse(BaseModel):
        drugs: List[Drug]  # type: ignore

    def standardize_drug_names(
        drug_names_gt: List[str], drug_names_assistant: List[str]
    ) -> tuple[str, str]:  # type: ignore
        system_prompt = """You are a medical expert specializing in pharmacology. You will be provided with two lists of drug names: one set is from a ground truth reference and the other is generated by an assistant. Your task is to match and standardize these drug names to facilitate comparison. You will need to:
    1. Assign a standardized version of each drug name.
    2. Attempt to determine if the ground truth and assistant lists refer to the same drug.
    3. Assign a drug class to each standardized drug name.
    4. Ensure that, wherever possible, the same standardized drug name and drug class are assigned to matches across both lists, even if the names differ slightly (e.g., "Piptaz" and "Piperacillin-Tazobactam").
    
    The output should be in JSON format, representing a list of drugs, where each entry should include the following fields:
    - `"original_drug_name"`: The original drug name as listed.
    - `"standardized_drug_name"`: The name to which similar drugs should be standardized.
    - `"drug_class"`: The class of the drug, such as "antibiotic" or "analgesic".
    
    # Steps:
    
    1. Compare drug names across both lists, analyzing if they refer to the same drug even if they are represented differently.
    2. Assign the same `"standardized_drug_name"` if the drugs match in meaning.
    3. Determine and assign `"drug_class"` for each drug, ensuring matches across the reference and assistant lists whenever possible.
    4. Present results in a structured JSON format, enabling an easy check of whether the reference and assistant lists propose the same drug or at least the same drug class.
    
    # Notes
    - The goal is to facilitate matching between the ground truth and assistant's entries, making it easier to determine if the recommendations align fully or at least by drug class.
    - Examples include variations in brand names vs. generic names, abbreviations, or simple misspellings.
    - If assigning a `"standardized_drug_name"` or `"drug_class"` is ambiguous, make an educated, evidence-based guess where possible.
        """

        user_prompt = f"""
            Drug names Ground Truth:
            {json.dumps(drug_names_gt)}


            Drug names Assistant:
            {json.dumps(drug_names_assistant)}
        """
        return system_prompt, user_prompt

    system_prompt, user_prompt = standardize_drug_names(
        drug_names_gt=ground_truth_drug_names, drug_names_assistant=ai_output_drug_names
    )

    completion = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=StandardizationResponse,
    )

    standardized_drugs = completion.choices[0].message.parsed.drugs  # type: ignore

    drug_mapping = {
        drug.original_drug_name: {
            "standardized_drug_name": drug.standardized_drug_name,
            "drug_class": drug.drug_class,
        }
        for drug in standardized_drugs
    }

    for drug in gt:
        if drug["drug_name"] in drug_mapping:
            drug.update(drug_mapping[drug["drug_name"]])

    for drug in assistant:
        if drug["drug_name"] in drug_mapping:
            drug.update(drug_mapping[drug["drug_name"]])

    gt_names = [drug.get("standardized_drug_name") for drug in gt]
    assistant_names = [drug.get("standardized_drug_name") for drug in assistant]

    gt_classes = set([drug.get("drug_class") for drug in gt])
    assistant_classes = set([drug.get("drug_class") for drug in assistant])

    overlap_results_names = measure_overlap(gt_names, assistant_names)
    overlap_results_classes = measure_overlap(gt_classes, assistant_classes)

    return {
        "standardized_drug_names": overlap_results_names,
        "drug_classes": overlap_results_classes,
    }


def evaluate_all_objectives(
    client: OpenAI, matched_results: dict, diagnosis: str
) -> Evaluation:
    """
    Evaluates all objectives.
    Args:
        client: The OpenAI client.
        diagnosis: The diagnosis to evaluate.
        matched_results: The matched results from the ground truth and assistant.
    Returns:
        An Evaluation object containing the results of the evaluation for each objective.
    """
    evaluation = Evaluation(
        diagnosis=evalaute_diagnosis(client, matched_results, diagnosis),
        physical_examination=evaluate_pe_request(matched_results),
        blood_requests=evaluate_blood_requests(matched_results),
        urine_requests=evaluate_urine_requests(matched_results),
        radiology_events=evaluate_radiology_requests(matched_results),
        procedures=evaluate_procedure_requests(matched_results),
        microbiology_events=evaluate_microbiology_requests(matched_results),
        hospital_medication=evaluate_medication_requests(client, matched_results),
    )

    return evaluation


def evaluate_diagnosis_objective(
    client: OpenAI, matched_results: dict, diagnosis: str
) -> Evaluation:
    """
    Evaluates the diagnosis objective.
    Args:
        client: The OpenAI client.
        matched_results: The matched results from the ground truth and assistant.
        diagnosis: The diagnosis to evaluate.
    Returns:
        An Evaluation object containing the results of the evaluation for each objective.
    """
    evaluation = Evaluation(
        diagnosis=evalaute_diagnosis(client, matched_results, diagnosis),
    )

    return evaluation


def evaluate_medication_objective(client: OpenAI, matched_results: dict, diagnosi: str):
    evaluation = Evaluation(
        hospital_medication=evaluate_medication_requests(client, matched_results),
    )

    return evaluation
