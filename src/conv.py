import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from assistants import MedAssistant, PatientAssistant, call_chat
from config import SAVE_DIR
from paths import (
    EVALUABLE_OUTPUTS_BASELINE_DIR,
    EVALUABLE_OUTPUTS_BIAS_DIR,
    EVALUABLE_OUTPUTS_HUMAN_BC_DIR,
    EVALUABLE_OUTPUTS_OPTIONAL_ADMISSION_DIR,
)
from paths import RESULTS_BACKUP_DIR as RESULTS_BACKUP_ROOT_DIR

RESULTS_BACKUP_DIR = str(RESULTS_BACKUP_ROOT_DIR)


def _backup_scope_from_save_dir(save_dir: str) -> str:
    """Map a save directory to a stable backup namespace."""
    save_path = Path(save_dir).expanduser().resolve()
    namespace_roots = [
        ("baseline", EVALUABLE_OUTPUTS_BASELINE_DIR.resolve()),
        ("bias", EVALUABLE_OUTPUTS_BIAS_DIR.resolve()),
        ("optional_admission", EVALUABLE_OUTPUTS_OPTIONAL_ADMISSION_DIR.resolve()),
        ("human_bc", EVALUABLE_OUTPUTS_HUMAN_BC_DIR.resolve()),
    ]

    for namespace, root in namespace_roots:
        if save_path == root or root in save_path.parents:
            rel = save_path.relative_to(root)
            return str(Path(namespace) / rel) if rel != Path(".") else namespace

    return "misc"


async def run_simulation(
    physician: MedAssistant,
    patient: PatientAssistant,
    primary_symptom: str,
    age: int | None = None,
    gender: str | None = None,
):
    """
    Simulates a medical conversation between a physician and a patient.

    This function initializes the conversation with the patient's primary symptoms,
    and then alternates between the medical assistant (physician) and patient assistant
    for a back-and-forth dialogue until the physician decides to perform some tests or start treatments.
    The conversation ends when the physician closes the patient case or a maximum number of steps has been
    exceeded upon which the physician is forced to finish the patient case.

    Args:
        physician: MedAssistant class from assistants.py
        patient: PatientAssistant class from assistants.py
        primary_symptom: str

    Returns:
        None
    """

    starter = (
        f"The patient you are now seeing has primary symptoms: {primary_symptom}"
        if primary_symptom
        else "The patient you are now seeing has not yet mentioned a specific chief complaint. Please ask the patient about their chief complaint."
    )
    if age and gender:
        starter += f" The patient is {age} years old and {gender}."

    print("Examining patient with info: ", starter)

    speaker, listener = physician, patient

    # Medical assistant starts the conversation

    message = await call_chat(speaker, starter)
    # in case the assistant completes a patient case in one step (didn't happen)
    if message.type == "terminated" or physician.completed_called:
        return

    speaker, listener = listener, speaker

    # Continue the conversation turnwise
    while True:
        message = await call_chat(speaker, message.messages)
        if message.type == "terminated" or physician.completed_called:
            break
        speaker, listener = listener, speaker  # change roles

    # in the conversation loop, the physician is always the last speaker
    # if the message.type is not "terminated", then we are in a situation where we forced the agent to finish, ...
    # ... allowing to return a single message to the patient, that the patient can finally respond to
    if not message.type == "terminated":
        message = await call_chat(patient, message.messages)


def save_conversation(
    medical_assistant,
    patient_assistant,
    patient_ctx,
    patient_data,
    ds_idx,
    dataset_name,
    total_time_elapsed,
    save_dir,
):
    """Save the conversation to a JSONL file - for EVALUATION.
    Args:
        medical_assistant: MedAssistant class from assistants.py
        patient_assistant: PatientAssistant class from assistants.py
        patient_ctx: PatientContext class from assistants.py
        patient_data: Patient class from dataset.py
        ds_idx: np.int64 type
        dataset_name: str

    Returns:
        None
    """

    med_assistant_data = medical_assistant.message_history
    patient_assistant_data = patient_assistant.message_history
    patient_ctx_dict = patient_ctx.to_dict()

    # Convert the session object to a string representation
    patient_ctx_dict["session"] = str(patient_ctx_dict["session"])
    patient_ctx_dict["patient_data"] = str(patient_ctx_dict["patient_data"])

    ds_idx = int(ds_idx)  # Convert ds_idx from np.int64 to int for serialization
    try:
        # first round on hospitalized patients
        hadm_id = int(patient_data.admissions.hadm_id.values[0])
    except:
        # second round for optional hospitalization experiments
        hadm_id = int(patient_data.patients.hadm_id.values[0])
    metadata = {
        "timestamp": str(datetime.now()),
        "hadm_id": hadm_id,
        "patient_context": patient_ctx_dict,
        "dataset_idx": ds_idx,
        "diagnosis/dataset_name": dataset_name,
        "elapsed_time": total_time_elapsed,
    }
    data = {
        "med_assistant": med_assistant_data,
        "patient_assistant": patient_assistant_data,
        "metadata": metadata,
    }

    directory = os.path.join(save_dir, dataset_name)
    backup_scope = _backup_scope_from_save_dir(save_dir)
    backup_directory = os.path.join(RESULTS_BACKUP_DIR, backup_scope, dataset_name)

    if not os.path.exists(directory):
        os.makedirs(directory)
    if not os.path.exists(backup_directory):
        os.makedirs(backup_directory)

    base_filename = (
        f"{dataset_name}_{hadm_id}_conversation"  # "diagnosis_hadm_id_conversation"
    )
    extension = ".jsonl"
    counter = 1
    file_path = os.path.join(directory, f"{base_filename}_{counter}{extension}")

    while os.path.exists(file_path):
        counter += 1
        file_path = os.path.join(directory, f"{base_filename}_{counter}{extension}")

    with open(file_path, "a") as f:
        f.write(json.dumps(data) + "\n")

    backup_path = os.path.join(backup_directory, os.path.basename(file_path))
    shutil.copy(file_path, backup_path)

    # freeze
    os.chmod(file_path, 0o444)
    os.chmod(backup_path, 0o444)

    print(f"Saved conversation to {file_path}")
