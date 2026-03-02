import argparse
import json

# Configure logging
import logging
import os
from dataclasses import asdict
from pathlib import Path
from typing import List

from dataset.mimic_dataset import MIMIC_Dataset
from dotenv import load_dotenv
from eval_config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR
from fastapi.encoders import jsonable_encoder
from objectives import evaluate_all_objectives
from openai import OpenAI
from preprocess import (
    PatientGroundTruth,
    extract_tool_use,
    load_one_result,
    match_ground_truth_and_assistant,
    merge_called_args,
)
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ignore warnings
import warnings

warnings.filterwarnings("ignore")


def get_file_paths(base_path: str) -> List[Path]:
    """
    Recursively get all .jsonl file paths under the given base path.

    Args:
        base_path (str): The base directory to search for files.

    Returns:
        List[Path]: A list of file paths.
    """
    return list(Path(base_path).rglob("*.jsonl"))


def evaluate_one_file(
    client: OpenAI,
    file_path: Path,
    dataset: MIMIC_Dataset,
    out_dir: str,
    diagnosis: str,
) -> None:
    """
    Evaluate a single assistant output file against the ground truth and write the evaluation to the output directory.

    Args:
        file_path (Path): The path to the assistant output file.
        dataset (MIMIC_Dataset): The dataset object containing patient data.
        out_dir (str): The base output directory.
        diagnosis (str): The diagnosis subdirectory name.
    """
    try:
        # Load assistant outputs and patient data
        med_assistant_outputs, patient_data, metadata = load_one_result(
            file_path, dataset
        )

        # Process ground truth and assistant outputs
        patient_gt = PatientGroundTruth(patient_data)
        med_assistant_tools_used = extract_tool_use(med_assistant_outputs)
        med_called_args = merge_called_args(med_assistant_tools_used)
        matched_results = match_ground_truth_and_assistant(med_called_args, patient_gt)

        # Evaluate objectives
        evaluation = evaluate_all_objectives(client, matched_results)

        # Prepare output directory
        output_dir = Path(out_dir) / diagnosis
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write evaluation results to JSON
        evaluation_dict = asdict(evaluation)

        evaluation_result = {
            "evaluation": evaluation_dict,
            "matched_results": jsonable_encoder(matched_results),
            "metadata": metadata,
        }

        evaluation_json = json.dumps(evaluation_result, indent=2)

        output_file_path = output_dir / f"{Path(file_path).stem}.json"

        try:
            with open(output_file_path, "w") as output_file:
                output_file.write(evaluation_json)

        except PermissionError:
            logger.info(
                f"File {output_file_path} already exists. Do you want to force overwrite?"
            )
            overwrite = input("Enter 'y' to overwrite, 'n' to skip: ")
            if overwrite.lower() != "y":
                logger.info(f"Skipping file {output_file_path}")
                return
            else:
                os.chmod(
                    output_file_path, 0o666
                )  # Change file permissions to allow overwriting
                with open(output_file_path, "w") as output_file:
                    output_file.write(evaluation_json)

        os.chmod(output_file_path, 0o444)

        logger.info(
            f"Successfully evaluated and saved results for {Path(output_file_path).name}"
        )

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}", exc_info=True)


def main() -> None:
    """
    Main function to evaluate assistant outputs for a given diagnosis.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the assistant outputs for a given diagnosis by comparing to the ground truth."
        )
    )

    parser.add_argument(
        "diagnosis",
        type=str,
        help="The specific diagnosis to process within evaluable_outputs",
    )
    parser.add_argument(
        "--input_dir",
        type=str,
        default=DEFAULT_INPUT_DIR,
        help="The base input directory containing evaluable_outputs",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help="The base output directory for evaluable_outputs",
    )

    args = parser.parse_args()

    in_dir = args.input_dir
    out_dir = args.output_dir
    diagnosis = args.diagnosis

    full_input_path = Path(in_dir) / diagnosis
    file_paths = get_file_paths(full_input_path)

    if not file_paths:
        logger.warning(f"No `.jsonl` files found in {full_input_path}")
        return

    dataset = MIMIC_Dataset.load_dataset(diagnosis)

    load_dotenv()
    client = OpenAI()

    for file_path in tqdm(file_paths, desc=f"Evaluating output files for {diagnosis}"):
        evaluate_one_file(client, file_path, dataset, out_dir, diagnosis)


if __name__ == "__main__":
    main()
