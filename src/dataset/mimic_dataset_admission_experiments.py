from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from paths import DIAGNOSIS_DATASETS_DIR
from pydantic import BaseModel, Field
from tqdm import tqdm


class MIMIC_Dataset_Admission_Experiments(BaseModel):
    """
    Class to hold data for a MIMIC dataset filtered for a specific diagnosis.

    This class represents a comprehensive dataset from the MIMIC database, filtered for a particular diagnosis.
    It contains various dataframes representing different aspects of patient care and hospital stays.

    Attributes:
        diagnosis (str): The specific diagnosis this dataset is filtered for.
        hadm_ids (set[int]): A set of unique hospital admission IDs ('hadm_id') for patients with the specified diagnosis.
        lab_events (pd.DataFrame): Laboratory test results for the filtered patients.
        microbiology (pd.DataFrame): Microbiology test results for the filtered patients.
        history_pe_admedication_diagnosis (pd.DataFrame): Patient history, physical examination, admission medication, and diagnosis extracted from discharge letters.
        radiology (pd.DataFrame): Radiology reports for the filtered patients.
        medication (pd.DataFrame): Medication prescriptions during hospital stays.
        procedures_icd (pd.DataFrame): ICD codes and descriptions for procedures performed during hospital stays.
        diagnosis_icd (pd.DataFrame): ICD diagnoses for the hospital stays.
        diagnosis_ed (pd.DataFrame): Emergency department diagnoses.
        ed_stays (pd.DataFrame): Information about emergency department stays.
        medrecon (pd.DataFrame): Medication reconciliation data from the emergency department.
        pyxis (pd.DataFrame): Medication administration data from the Pyxis system in the emergency department.
        triage (pd.DataFrame): Triage information from the emergency department.
        vitalsign (pd.DataFrame): Continuous vital sign measurements from the emergency department.
        admissions (pd.DataFrame): Admissions data for the filtered patients.
        patients (pd.DataFrame): Patients data for the filtered patients.

    The class is iterable, allowing iteration over individual hospital admissions (hadm_ids).
    Each iteration returns a Mimic_Hadm_Dataset object containing data for a single hospital admission.

    Methods:
        __iter__: Allows iteration over the dataset's hospital admissions.
        __next__: Returns the next Mimic_Hadm_Dataset in the iteration.

    Usage:
        mimic_dataset = Mimic_Dataset(diagnosis="appendicitis", ...)
        for single_admission in mimic_dataset:
            # Process each admission
    """

    diagnosis: str = Field(
        ..., description="The diagnosis this dataset is filtered for"
    )
    hadm_ids: set[int] = Field(
        ..., description="A set of 'hadm_id's of the patients filtered for a diagnosis"
    )
    lab_events: pd.DataFrame = Field(..., description="The lab events for the patients")
    history_pe_admedication_diagnosis: pd.DataFrame = Field(
        ...,
        description="The history, physical examination (pe), admission medication (admedication) and diagnosis for the patients, extracted from the discharge letters",
    )
    radiology: pd.DataFrame = Field(
        ..., description="The radiology reports for the patients"
    )
    medication: pd.DataFrame = Field(
        ...,
        description="The medication (prescriptions) for the patients during the hospital stay",
    )
    medrecon: pd.DataFrame = Field(
        ..., description="The medication for the patients in the emergency department"
    )
    pyxis: pd.DataFrame = Field(
        ..., description="The medication administration in the mergency departmen"
    )
    triage: pd.DataFrame = Field(
        ..., description="The triage for the patients in the emergency department"
    )
    patients: pd.DataFrame = Field(
        ..., description="The patients data for the patients"
    )

    class Config:
        arbitrary_types_allowed = True  # allow pd.DataFrames as types
        populate_by_name = True

    def list_tables(self):
        return [
            attr
            for attr in self.__dict__.keys()
            if isinstance(getattr(self, attr), pd.DataFrame)
        ]

    def __getitem__(self, idx):
        if idx not in self.hadm_ids:
            raise KeyError(f"'hadm_id' {idx} not found in the dataset.")

        df_kwargs = {}
        for attr in self.list_tables():
            df = getattr(self, attr)
            assert "hadm_id" in df.columns, f"Column 'hadm_id' not found in {attr}."
            assert df["hadm_id"].dtype in [
                int,
                float,
            ], (
                f"Column 'hadm_id' in {attr} is of type {df['hadm_id'].dtype} instead of int."
            )
            df_filtered = df[df["hadm_id"] == idx].copy()
            df_kwargs[attr] = df_filtered

        # Remove 'hadm_ids' from kwargs if it's accidentally included
        df_kwargs.pop("hadm_ids", None)

        return MIMIC_Hadm_Dataset_Admission_Experiments(
            diagnosis=self.diagnosis,
            hadm_ids=self.hadm_ids,
            hadm_id=idx,
            **df_kwargs,
        )

    def __len__(self):
        return len(self.hadm_ids)

    def __iter__(self):
        # make the class iterable over the hadm_ids
        self._iter_hadm_ids = iter(self.hadm_ids)
        return self

    def __next__(self):
        # get the next item until exhausted
        try:
            hadm_id = next(self._iter_hadm_ids)

        except StopIteration:
            raise StopIteration

        return MIMIC_Hadm_Dataset_Admission_Experiments(
            diagnosis=self.diagnosis,
            hadm_ids=self.hadm_ids,  # will be removed after passing to super().__init__
            hadm_id=hadm_id,
            lab_events=self.lab_events[self.lab_events.hadm_id == hadm_id],
            history_pe_admedication_diagnosis=self.history_pe_admedication_diagnosis[
                self.history_pe_admedication_diagnosis.hadm_id == hadm_id
            ],
            radiology=self.radiology[self.radiology.hadm_id == hadm_id],
            medication=self.medication[self.medication.hadm_id == hadm_id],
            medrecon=self.medrecon[self.medrecon.hadm_id == hadm_id],
            pyxis=self.pyxis[self.pyxis.hadm_id == hadm_id],
            triage=self.triage[self.triage.hadm_id == hadm_id],
            patients=self.patients[self.patients.hadm_id == hadm_id],
        )

    def save_dataset(self, name: str | None = None):
        """Save the dataset to a metadata.json and parquet (pd.DataFrame) files"""
        if name is None:
            name = self.diagnosis

        DATASET_DIR = DIAGNOSIS_DATASETS_DIR
        DATASET_DIR.mkdir(parents=True, exist_ok=True)
        path = DATASET_DIR / name

        if path.exists():
            user_input = input(
                f"The path {path} already exists. Do you want to force overwrite? (y/n): "
            )
            if user_input.lower() != "y":
                print("Operation cancelled by user.")
                return

        path.mkdir(parents=True, exist_ok=True)
        metadata = {"diagnosis": self.diagnosis, "hadm_ids": list(self.hadm_ids)}

        with open(path / "metadata.json", "w") as f:
            json.dump(metadata, f)

        for attr_name, attr_value in tqdm(self.__dict__.items()):
            if isinstance(attr_value, pd.DataFrame):
                # handle mixed types which break in .parquet files
                # if one column has more than 1 type, convert it to string
                for col in attr_value.select_dtypes(include=["object"]).columns:
                    if attr_value[col].apply(type).nunique() > 1:
                        print(
                            f"Column '{col}' in DataFrame '{attr_name}' has mixed types. Converting to string for .parquet storage."
                        )
                        attr_value[col] = (
                            attr_value[col].astype(str).replace("nan", pd.NA)
                        )

                attr_value.to_parquet(path / f"{attr_name}.parquet")

        print(f"Saved dataset for {name} to {path}.")

    def save_dataset_excel(self, name: str):
        """Save the dataset to a metadata.json and excel (pd.DataFrame) files"""

        DATASET_DIR = DIAGNOSIS_DATASETS_DIR
        DATASET_DIR.mkdir(parents=True, exist_ok=True)
        path = DATASET_DIR / name

        if path.exists():
            user_input = input(
                f"The path {path} already exists. Do you want to force overwrite? (y/n): "
            )
            if user_input.lower() != "y":
                print("Operation cancelled by user.")
                return

        path.mkdir(parents=True, exist_ok=True)
        metadata = {"diagnosis": self.diagnosis, "hadm_ids": list(self.hadm_ids)}

        with open(path / "metadata.json", "w") as f:
            json.dump(metadata, f)

        for attr_name, attr_value in tqdm(self.__dict__.items()):
            if isinstance(attr_value, pd.DataFrame):
                # handle mixed types which break in .csv files
                # if one column has more than 1 type, convert it to string
                for col in attr_value.select_dtypes(include=["object"]).columns:
                    if attr_value[col].apply(type).nunique() > 1:
                        print(
                            f"Column '{col}' in DataFrame '{attr_name}' has mixed types. Converting to string for .csv storage."
                        )
                        attr_value[col] = (
                            attr_value[col].astype(str).replace("nan", pd.NA)
                        )

                attr_value.to_excel(path / f"{attr_name}.xlsx", index=False)

        print(f"Saved dataset for {name} to {path}.")

    def save_dataset_csv(self, name: str):
        """Save the dataset to a metadata.json and csv (pd.DataFrame) files"""

        DATASET_DIR = DIAGNOSIS_DATASETS_DIR
        DATASET_DIR.mkdir(parents=True, exist_ok=True)
        path = DATASET_DIR / name

        if path.exists():
            user_input = input(
                f"The path {path} already exists. Do you want to force overwrite? (y/n): "
            )
            if user_input.lower() != "y":
                print("Operation cancelled by user.")
                return

        path.mkdir(parents=True, exist_ok=True)
        metadata = {"diagnosis": self.diagnosis, "hadm_ids": list(self.hadm_ids)}

        with open(path / "metadata.json", "w") as f:
            json.dump(metadata, f)

        for attr_name, attr_value in tqdm(self.__dict__.items()):
            if isinstance(attr_value, pd.DataFrame):
                # handle mixed types which break the files
                # if one column has more than 1 type, convert it to string
                for col in attr_value.select_dtypes(include=["object"]).columns:
                    if attr_value[col].apply(type).nunique() > 1:
                        print(
                            f"Column '{col}' in DataFrame '{attr_name}' has mixed types. Converting to string for .csv storage."
                        )
                        attr_value[col] = (
                            attr_value[col].astype(str).replace("nan", pd.NA)
                        )

                attr_value.to_csv(path / f"{attr_name}.csv", index=False)

        print(f"Saved dataset for {name} to {path}.")

    @classmethod
    def load_dataset(cls, name: str) -> MIMIC_Dataset_Admission_Experiments:
        """Load the dataset from a metadata.json and parquet (pd.DataFrame) files"""

        DATASET_DIR = DIAGNOSIS_DATASETS_DIR
        DATASET_DIR.mkdir(parents=True, exist_ok=True)
        path = DATASET_DIR / name

        with open(path / "metadata.json", "r") as f:
            metadata = json.load(f)

        diagnosis, hadm_ids = metadata["diagnosis"], set(metadata["hadm_ids"])

        dataframes = {}
        for filename in tqdm(path.glob("*.parquet")):
            df_name = filename.stem
            dataframes[df_name] = pd.read_parquet(filename)

        # print(f"Loaded dataset for {name} from {path}.")

        return cls(diagnosis=diagnosis, hadm_ids=hadm_ids, **dataframes)


class MIMIC_Hadm_Dataset_Admission_Experiments(MIMIC_Dataset_Admission_Experiments):
    """
    Class to hold data for a single MIMIC hospital admission.

    This class represents a dataset for an individual hospital admission in the MIMIC database.
    It inherits from Mimic_Dataset and contains specific data related to a single hospital
    admission identified by a unique 'hadm_id'.

    Attributes:
        hadm_id (int): The unique identifier for the hospital admission.
        lab_events (pd.DataFrame): Laboratory test results for this admission.
        discharge_text (pd.DataFrame): Discharge summary text for this admission.
        radiology (pd.DataFrame): Radiology reports for this admission.
        medication (pd.DataFrame): Medication prescriptions for this admission.
        microbiology (pd.DataFrame): Microbiology test results for this admission.
        procedures_icd (pd.DataFrame): ICD procedure codes for this admission.
        diagnosis_icd (pd.DataFrame): ICD diagnoses for this admission.
        diagnosis_ed (pd.DataFrame): Emergency department diagnoses for this admission.
        ed_stays (pd.DataFrame): Emergency department stay information for this admission.
        medrecon (pd.DataFrame): Medication reconciliation data for this admission.
        pyxis (pd.DataFrame): Medication administration data from Pyxis for this admission.
        triage (pd.DataFrame): Triage information for this admission.
        vitalsign (pd.DataFrame): Vital sign measurements for this admission.

    The class provides methods to access and manipulate data specific to a single
    hospital admission, facilitating analysis and processing of individual patient stays.
    """

    hadm_id: int = Field(
        ..., description="The 'hadm_id' of the specific hospital admission"
    )

    class Config:
        arbitrary_types_allowed = True  # to allow pd.DataFrame's

    def __init__(self, **data):
        """Remove the hadm_ids attribute from the dataset"""
        super().__init__(**data)
        # if hasattr(self, "hadm_ids"):
        #     del self.hadm_ids

    def __repr__(self):
        return f"MIMIC_Hadm_Dataset_Admission_Experiments(hadm_id={self.hadm_id})"

    def __str__(self):
        dataframes = [
            (name, field.description)
            for name, field in self.model_fields.items()
            if isinstance(field.annotation, type(pd.DataFrame))
        ]

        output = [f"MIMIC Hospital Admission Dataset (hadm_id: {self.hadm_id})"]
        output.append("Dataframes:")
        for name, description in dataframes:
            output.append(f"  - {name}: {description}")

        return "\n".join(output)
