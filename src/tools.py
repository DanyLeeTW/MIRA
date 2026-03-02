# mypy: ignore-errors
import datetime
from enum import Enum
from importlib import import_module
from typing import Any, List, Literal, Optional, Union
from uuid import uuid4

import pandas as pd
from fhir.resources.annotation import Annotation
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.codeablereference import CodeableReference
from fhir.resources.coding import Coding
from fhir.resources.dosage import Dosage
from fhir.resources.fhirtypes import DateTime
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.quantity import Quantity
from fhir.resources.reference import Reference
from fhir.resources.servicerequest import ServiceRequest
from fhir.resources.timing import Timing
from pydantic import BaseModel, Field, PrivateAttr
from termcolor import colored


# Support both package imports (e.g., `src.tools`) and direct module imports
# (e.g., `tools`) from run scripts/notebooks.
def _import_local_module(module_name: str):
    if __package__:
        try:
            return import_module(f".{module_name}", package=__package__)
        except ModuleNotFoundError:
            pass
    return import_module(module_name)


_code_maps = _import_local_module("code_maps")
radiology_modality_and_region_to_loinc_concept = (
    _code_maps.radiology_modality_and_region_to_loinc_concept
)
radiology_modality_and_region_to_snomed_concept = (
    _code_maps.radiology_modality_and_region_to_snomed_concept
)
lab_itemid_to_omop_concept = _code_maps.lab_itemid_to_omop_concept

_medication_codes = _import_local_module("codes.medication_codes")
get_drug_codes_from_name = _medication_codes.get_drug_codes_from_name

_mimic_enums = _import_local_module("MimicEnums")
BloodValue = _mimic_enums.BloodValue
MicroBiologyValue = _mimic_enums.MicroBiologyValue
PeriodUnit = _mimic_enums.PeriodUnit
RadiologyModalityValue = _mimic_enums.RadiologyModalityValue
RadiologyRegionValue = _mimic_enums.RadiologyRegionValue
RouteUnit = _mimic_enums.RouteUnit
UrineValue = _mimic_enums.UrineValue

registered_resources = []


def _normalize_code(code: Any) -> Optional[str]:
    if code is None:
        return None
    try:
        if pd.isna(code):
            return None
    except Exception:
        pass
    normalized = str(code).strip()
    if not normalized:
        return None
    return normalized


def _split_codes(raw_codes: Any) -> List[str]:
    normalized = _normalize_code(raw_codes)
    if not normalized:
        return []
    return [c for c in (_normalize_code(part) for part in normalized.split(";")) if c]


def _resolve_medication_codes_safe(drug_name: str) -> dict[str, Optional[str]]:
    fallback = {
        "drug_name": drug_name,
        "ndc": None,
        "rxnorm_code": None,
        "snomed_ct_code": None,
        "atc_codes": None,
    }
    try:
        resolved = get_drug_codes_from_name(drug_name)
    except Exception:
        return fallback

    if not isinstance(resolved, dict):
        return fallback

    return {
        "drug_name": drug_name,
        "ndc": _normalize_code(resolved.get("ndc")),
        "rxnorm_code": _normalize_code(resolved.get("rxnorm_code")),
        "snomed_ct_code": _normalize_code(resolved.get("snomed_ct_code")),
        "atc_codes": _normalize_code(resolved.get("atc_codes")),
    }


def register_class(klass):
    global registered_resources
    registered_resources.append(klass)
    return klass


def get_patient_reference(patient_id: str) -> str:
    """Constructs a FHIR reference for a Patient."""
    if not patient_id or not isinstance(patient_id, str):
        raise ValueError("Invalid patient_id provided.")
    return f"Patient/{patient_id}"


def get_practitioner_reference(practitioner_id: str) -> str:
    """Constructs a FHIR reference for a Practitioner."""
    if not practitioner_id or not isinstance(practitioner_id, str):
        raise ValueError("Invalid practitioner_id provided.")
    return f"Practitioner/{practitioner_id}"


def get_performer_reference(organization_id: str) -> str:
    """Constructs a FHIR reference for an Organization."""
    if not organization_id or not isinstance(organization_id, str):
        raise ValueError("Invalid organization_id provided.")
    return f"Organization/{organization_id}"


@register_class
class LabRequestFHIR(BaseModel):
    """Request for a single Lab Value"""

    lab_value: BloodValue = Field(
        description="The blood value to request, selected from the BloodValue Enum.",
        example=BloodValue._50803,
    )

    # not shown to the LLM via ".model_schema()"
    _patient_reference: str = PrivateAttr()
    _requester_reference: str = PrivateAttr()
    _performer_reference: str = PrivateAttr()
    _authored_on: datetime.datetime = PrivateAttr()
    _lab_value_loinc_code: str = PrivateAttr()

    def __init__(
        self,
        *,
        lab_value: BloodValue,
        patient_id: str,
        practitioner_id: str,
        organization_id: str,
        **data,
    ):
        """
        Initializes the LabRequestFHIR instance with necessary references.

        Args:
            lab_value (BloodValue): The blood value to request.
            patient_id (str): The ID of the Patient.
            practitioner_id (str): The ID of the Practitioner making the request.
            organization_id (str): The ID of the Organization performing the request.
        """
        super().__init__(lab_value=lab_value, **data)

        # Validate and set references
        self._patient_reference = get_patient_reference(patient_id)
        self._requester_reference = get_practitioner_reference(practitioner_id)
        self._performer_reference = get_performer_reference(organization_id)
        self._authored_on = datetime.datetime.now()
        self._lab_value_loinc_code = BloodValue(self.lab_value).name[
            1:
        ]  # remove "_"-prefix

        self._lab_value_omop_concept_code = lab_itemid_to_omop_concept.get(
            self.lab_value
        )

    def to_fhir(self):
        labvalue_request = ServiceRequest(
            resourceType="ServiceRequest",
            id=str(uuid4()),
            status="active",
            intent="order",
            category=[
                CodeableConcept(
                    coding=[
                        Coding(
                            system="http://terminology.hl7.org/CodeSystem/service-category",
                            code="laboratory",
                            display="Laboratory",
                        )
                    ],
                    text="Laboratory",
                )
            ],
            code=CodeableReference(
                concept=CodeableConcept(
                    coding=[
                        Coding(
                            # mapping from here: https://github.com/MIT-LCP/mimic-code/blob/e39825259beaa9d6bc9b99160049a5d251852aae/mimic-iv/mapping/d_labitems_to_loinc.csv
                            system="http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems",
                            code=self._lab_value_loinc_code,  # LOINC code
                            display=self.lab_value,
                        ),
                        Coding(
                            # mapping from here: https://github.com/MIT-LCP/mimic-code/blob/e39825259beaa9d6bc9b99160049a5d251852aae/mimic-iv/mapping/d_labitems_to_loinc.csv
                            system="https://fhir-terminology.ohdsi.org",
                            code=self._lab_value_omop_concept_code,  # OMOP Concept Code
                            display=self.lab_value,
                        ),
                    ]
                )
            ),
            subject=Reference(
                reference=self._patient_reference,
                display=f"Patient Name: {self._patient_reference}",
            ),
            authoredOn=DateTime.validate(self._authored_on.isoformat()),
            requester=Reference(
                reference=self._requester_reference,
                display=f"Practitioner Name: {self._requester_reference}",
            ),
            performer=[
                Reference(
                    reference=self._performer_reference,
                    display=f"Requesting Organization: {self._performer_reference}",
                )
            ],
        )
        return labvalue_request


@register_class
class MedicationRequestFHIR(BaseModel):
    """Request for a single medication"""

    # replace by Enums
    drug_name: str = Field(description="The name of the drug", example="Amoxicillin")
    dosage_text: str = Field(  # prod_strength
        description="The dosage, strength or concentration a single medication as text",
        example="10mEq ER Tablet once a day",  # prod strength
    )
    dosage_value: Union[int, float] = Field(  # dose_val_rx
        # dosage_value: Union[int, float, str] = Field(  # dose_val_rx
        description="The prescribed dosage for the patient in one intake",
        example=500,  # improve
    )
    dosage_unit: str = Field(
        description="The unit of the dosage value", example="mg"
    )  # dose_unit_rx
    period: int = Field(description="The period of the dosage", example=1)
    period_unit: PeriodUnit = Field(description="The unit of the period", example="d")
    frequency: int = Field(
        description="The frequency of the dosage per period", example=3
    )  # doses_per_24_hrs
    route: RouteUnit = Field(description="The route of the dosage", example="Oral")

    _patient_reference: str = PrivateAttr()
    _requester_reference: str = PrivateAttr()
    _performer_reference: str = PrivateAttr()
    _authored_on: datetime.datetime = PrivateAttr()
    _route_code_snomed: str = PrivateAttr()
    _medication_codes: dict[str, Optional[str]] = PrivateAttr()

    def __init__(
        self,
        *,
        drug_name: str,
        dosage_text: str,
        dosage_value: Union[int, float, str],
        dosage_unit: str,
        period: int,
        period_unit: PeriodUnit,
        frequency: int,
        route: RouteUnit,
        patient_id: str,
        practitioner_id: str,
        organization_id: str,
        **data,
    ):
        super().__init__(
            drug_name=drug_name,
            dosage_text=dosage_text,
            dosage_value=dosage_value,
            dosage_unit=dosage_unit,
            period=period,
            period_unit=period_unit,
            frequency=frequency,
            route=route,
            **data,
        )

        self._route_code_snomed = RouteUnit(self.route).name[
            1:
        ]  # cut off the "_{code}" prefix that is necessary for the Enum
        self._patient_reference = get_patient_reference(patient_id)
        self._requester_reference = get_practitioner_reference(practitioner_id)
        self._performer_reference = get_performer_reference(organization_id)
        self._authored_on = datetime.datetime.now()
        self._medication_codes = _resolve_medication_codes_safe(self.drug_name)

    def to_fhir(self):
        dosage_instruction = Dosage.construct(
            # https://build.fhir.org/dosage.html#Dosage
            text=self.dosage_text,  # medication.prod_strength
            doseAndRate=[
                {
                    "doseQuantity": Quantity.construct(
                        value=self.dosage_value,  # medication.prod_strength
                        unit=self.dosage_unit,  # medication.dose_unit_rx
                        system="http://unitsofmeasure.org",
                        code=self.dosage_unit,  # medication.dose_unit_rx
                    )
                }
            ],
            timing=Timing.construct(
                # https://build.fhir.org/datatypes.html#Timing
                repeat={
                    "frequency": self.frequency,  # medication.doses_per_24_hrs
                    "period": self.period,  # period_hours
                    "periodUnit": self.period_unit,  # # s | min | h | d | wk | mo | a - unit of time (UCUM)
                }
            ),
            route=CodeableConcept(
                coding=[
                    Coding(
                        system="http://snomed.info/sct",
                        code=self._route_code_snomed,  # restrain to # https://build.fhir.org/dosage.html#Dosage
                    )
                ],
                text=self.route,
            ),
        )

        medication_codings = []
        for ndc_code in _split_codes(self._medication_codes.get("ndc")):
            medication_codings.append(
                {
                    "system": "http://hl7.org/fhir/sid/ndc",
                    "code": ndc_code,
                    "display": self.drug_name,
                }
            )
        for rxnorm_code in _split_codes(self._medication_codes.get("rxnorm_code")):
            medication_codings.append(
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": rxnorm_code,
                    "display": self.drug_name,
                }
            )
        for snomed_code in _split_codes(self._medication_codes.get("snomed_ct_code")):
            medication_codings.append(
                {
                    "system": "http://snomed.info/sct",
                    "code": snomed_code,
                    "display": self.drug_name,
                }
            )
        for atc_code in _split_codes(self._medication_codes.get("atc_codes")):
            medication_codings.append(
                {
                    "system": "http://www.whocc.no/atc",
                    "code": atc_code,
                    "display": self.drug_name,
                }
            )

        medication_codeable_concept = CodeableConcept.construct(
            # https://build.fhir.org/datatypes.html#CodeableConcept
            coding=medication_codings or None,
            text=self.drug_name,
        )
        medication_reference = CodeableReference.construct(
            # https://build.fhir.org/references.html#CodeableReference
            concept=medication_codeable_concept
        )

        medication_request = MedicationRequest(
            # https://build.fhir.org/medicationrequest.html
            resourceType=MedicationRequest.__name__,
            id=str(uuid4()),
            status="active",  # active | on-hold | ended | stopped | completed | cancelled | entered-in-error | draft | unknown
            intent="order",  # proposal | plan | order | original-order | reflex-order | filler-order | instance-order | option
            medication=medication_reference,  # CodableReference
            subject=Reference(
                reference=self._patient_reference,
                display=f"Patient Name: {self._patient_reference}",
            ),  # https://build.fhir.org/references.html#Reference
            requester=Reference(
                reference=self._requester_reference,
                display=f"Practitioner Name: {self._requester_reference}",
            ),
            dosageInstruction=[dosage_instruction],
            authoredOn=DateTime.validate(datetime.datetime.now().isoformat()),
            performer=[
                Reference(
                    reference=self._performer_reference,
                    display=f"Requesting Organization: {self._performer_reference}",
                )
            ],
        )

        return medication_request


@register_class
class PhysicalExamRequestFHIR(BaseModel):
    """
    Request for Physical Examination data.
    """

    # Not shown to the LLM via ".model_schema()"
    _patient_reference: str = PrivateAttr()
    _requester_reference: str = PrivateAttr()
    _performer_reference: str = PrivateAttr()
    _authored_on: datetime.datetime = PrivateAttr()
    _pe_code: str = PrivateAttr()

    def __init__(
        self,
        *,
        patient_id: str,
        practitioner_id: str,
        organization_id: str,
        **data,
    ):
        """
        Initializes the PhysicalExamRequestFHIR instance with necessary references.

        Args:
            patient_id (str): The ID of the Patient.
            practitioner_id (str): The ID of the Practitioner making the request.
            organization_id (str): The ID of the Organization performing the request.
        """
        super().__init__(**data)

        # Validate and set references
        self._patient_reference = get_patient_reference(patient_id)
        self._requester_reference = get_practitioner_reference(practitioner_id)
        self._performer_reference = get_performer_reference(organization_id)
        self._authored_on = datetime.datetime.now()
        self._pe_code = "PE"

    def to_fhir(self):
        pe_request = ServiceRequest(
            resourceType="ServiceRequest",
            id=str(uuid4()),
            status="active",
            intent="order",
            category=[
                CodeableConcept(
                    coding=[
                        Coding(
                            system="http://terminology.hl7.org/CodeSystem/service-category",
                            code="exam",
                            display="Examination",
                        )
                    ],
                    text="Physical Examination",
                )
            ],
            code=CodeableReference(
                concept=CodeableConcept(
                    coding=[
                        Coding(
                            system="http://mimic.mit.edu/fhir/mimic/CodeSystem/physical-exam-codes",
                            code=self._pe_code,
                            display="Physical Examination",
                        )
                    ]
                )
            ),
            subject=Reference(
                reference=self._patient_reference,
                display=f"Patient Name: {self._patient_reference}",
            ),
            authoredOn=DateTime.validate(self._authored_on.isoformat()),
            requester=Reference(
                reference=self._requester_reference,
                display=f"Practitioner Name: {self._requester_reference}",
            ),
            performer=[
                Reference(
                    reference=self._performer_reference,
                    display=f"Requesting Organization: {self._performer_reference}",
                )
            ],
        )
        return pe_request


class MicrobiologyRequestFHIR(BaseModel):
    """Request for a Microbiology Test"""

    microbiology_value: MicroBiologyValue = Field(
        description="The microbiology test to request, selected from the MicroBiologyValue Enum.",
        example=MicroBiologyValue._90144,
    )

    # Private attributes not shown to the LLM via ".model_schema()"
    _patient_reference: str = PrivateAttr()
    _requester_reference: str = PrivateAttr()
    _performer_reference: str = PrivateAttr()
    _authored_on: datetime.datetime = PrivateAttr()
    _microbiology_test_itemid_code: str = PrivateAttr()

    def __init__(
        self,
        *,
        microbiology_value: MicroBiologyValue,
        patient_id: str,
        practitioner_id: str,
        organization_id: str,
        **data,
    ):
        """
        Initializes the MicrobiologyRequestFHIR instance with necessary references.

        Args:
            microbiology_value (MicroBiologyValue): The microbiology test to request.
            patient_id (str): The ID of the Patient.
            practitioner_id (str): The ID of the Practitioner making the request.
            organization_id (str): The ID of the Organization performing the request.
        """
        super().__init__(microbiology_value=microbiology_value, **data)

        # Validate and set references
        self._patient_reference = get_patient_reference(patient_id)
        self._requester_reference = get_practitioner_reference(practitioner_id)
        self._performer_reference = get_performer_reference(organization_id)
        self._authored_on = datetime.datetime.now()
        self._microbiology_test_itemid_code = MicroBiologyValue(
            self.microbiology_value
        ).name[1:]

    def to_fhir(self) -> ServiceRequest:
        """
        Converts the MicrobiologyRequestFHIR instance to a FHIR ServiceRequest resource.

        Returns:
            ServiceRequest: The FHIR ServiceRequest resource.
        """
        microbiology_request = ServiceRequest(
            resourceType="ServiceRequest",
            id=str(uuid4()),
            status="active",
            intent="order",
            category=[
                CodeableConcept(
                    coding=[
                        Coding(
                            system="http://terminology.hl7.org/CodeSystem/service-category",
                            code="laboratory",
                            display="Laboratory",
                        )
                    ],
                    text="Laboratory",
                )
            ],
            code=CodeableReference(
                concept=CodeableConcept(
                    coding=[
                        Coding(
                            system="http://mimic.mit.edu/fhir/mimic/CodeSystem/microbiology-test-itemid",
                            code=self._microbiology_test_itemid_code,
                            display=self.microbiology_value,
                        ),
                    ],
                    text=self.microbiology_value,
                )
            ),
            subject=Reference(
                reference=self._patient_reference,
                display=f"Patient ID: {self._patient_reference}",
            ),
            authoredOn=DateTime.validate(self._authored_on.isoformat()),
            requester=Reference(
                reference=self._requester_reference,
                display=f"Practitioner ID: {self._requester_reference}",
            ),
            performer=[
                Reference(
                    reference=self._performer_reference,
                    display=f"Organization ID: {self._performer_reference}",
                )
            ],
        )
        return microbiology_request


class RadiologyRequestFHIR(BaseModel):
    """Request for a radiology examination. "Venous" Ultrasound refers to a venous ultrasound of the lower extremities (Duplex)."""

    modality: RadiologyModalityValue = Field(
        description="The imaging modality to be used.",
        example=RadiologyModalityValue.CT,
    )
    region: RadiologyRegionValue = Field(
        description="The body region to be imaged.",
        example=RadiologyRegionValue.Abdomen,
    )
    info: Optional[str] = Field(
        description="Any additional clinical information or questions for the radiologist to consider.",
        example="Evaluate for pulmonary embolism.",
    )

    # Private attributes (not exposed to the LLM)
    _patient_reference: str = PrivateAttr()
    _requester_reference: str = PrivateAttr()
    _performer_reference: str = PrivateAttr()
    _authored_on: datetime.datetime = PrivateAttr()
    _procedure_loinc_code: Optional[str] = PrivateAttr()
    _procedure_snomed_code: Optional[str] = PrivateAttr()

    def __init__(
        self,
        *,
        modality: RadiologyModalityValue,
        region: RadiologyRegionValue,
        info: Optional[str] = None,
        patient_id: str,
        practitioner_id: str,
        organization_id: str,
        **data,
    ):
        """
        Initializes the RadiologyRequestFHIR instance with necessary references.

        Args:
            modality (RadiologyModalityValue): The imaging modality to be used.
            region (RadiologyRegionValue): The body region to be imaged.
            info (Optional[str]): Additional clinical information or questions.
            patient_id (str): The ID of the Patient.
            practitioner_id (str): The ID of the Practitioner making the request.
            organization_id (str): The ID of the Organization performing the request.
        """
        super().__init__(modality=modality, region=region, info=info, **data)

        # Set references
        self._patient_reference = get_patient_reference(patient_id)
        self._requester_reference = get_practitioner_reference(practitioner_id)
        self._performer_reference = get_performer_reference(organization_id)
        self._authored_on = datetime.datetime.now()

        # Map modality and region to standard codes
        self._procedure_snomed_code, self._procedure_loinc_code = (
            self.get_procedure_codes(modality, region)
        )

    def get_procedure_codes(
        self, modality: RadiologyModalityValue, region: RadiologyRegionValue
    ):
        """
        Maps the modality and region to LOINC and SNOMED CT procedure codes.

        Args:
            modality (RadiologyModalityValue): The imaging modality.
            region (RadiologyRegionValue): The body region.

        Returns:
            Tuple[Optional[str], Optional[str]]: The SNOMED CT code and LOINC code.
        """

        snomed_code = radiology_modality_and_region_to_snomed_concept.get(
            f"{modality}_{region}"
        )
        loinc_code = radiology_modality_and_region_to_loinc_concept.get(
            f"{modality}_{region}"
        )
        return snomed_code, loinc_code

    def to_fhir(self):
        # Build the ServiceRequest FHIR resource
        radiology_request = ServiceRequest(
            resourceType="ServiceRequest",
            id=str(uuid4()),
            status="active",
            intent="order",
            category=[
                CodeableConcept(
                    coding=[
                        Coding(
                            system="http://terminology.hl7.org/CodeSystem/service-category",
                            code="RAD",
                            display="Radiology",
                        )
                    ],
                    text="Radiology",
                )
            ],
            code=CodeableReference(
                concept=CodeableConcept(
                    coding=[
                        Coding(
                            system="http://loinc.org",
                            code=self._procedure_loinc_code or "unknown",
                            display=f"{self.modality.value} {self.region.value}",
                        ),
                        Coding(
                            system="http://snomed.info/sct",
                            code=self._procedure_snomed_code or "unknown",
                            display=f"{self.modality.value} {self.region.value}",
                        ),
                    ],
                    text=f"{self.modality.value} {self.region.value}",
                ),
            ),
            subject=Reference(
                reference=self._patient_reference,
                display=f"Patient ID: {self._patient_reference}",
            ),
            authoredOn=DateTime.validate(self._authored_on.isoformat()),
            requester=Reference(
                reference=self._requester_reference,
                display=f"Practitioner Name: {self._requester_reference}",
            ),
            performer=[
                Reference(
                    reference=self._performer_reference,
                    display=f"Requesting Organization: {self._performer_reference}",
                )
            ],
            # Remove or correct the 'relevantHistory' field
            # Include 'info' in the 'note' field if it exists
            note=[Annotation(text=self.info)] if self.info else None,
        )
        return radiology_request


class ProcedureRequestFHIR(BaseModel):
    """A class representing a procedure request in FHIR format that is requested for a patient."""

    procedure: str = Field(
        description="Exact name of the procedure to perform. Should be called after `ProcedureSearch` tool with one of the options `option` where option is the exact name of the procedure. If the search did not return options you were looking for, try to search again, or skip. This involves therapeutic procedures, like surgeries. For mostly diagnostic procedures like `ERCP` use the `RadiologyRequestFHIR` tool.",
        example="Laparoscopic appendectomy",
    )
    # procedure_extended: str = Field(
    #     description="Extended description of the procedure to perform",
    #     example="laparoscopic cholecystectomy for removal of gallstones",
    # )

    # Private attributes not shown to the LLM via ".model_schema()"
    _patient_reference: str = PrivateAttr()
    _requester_reference: str = PrivateAttr()
    _performer_reference: str = PrivateAttr()
    _authored_on: datetime.datetime = PrivateAttr()

    def __init__(
        self,
        *,
        procedure: str,
        # procedure_extended: str,
        patient_id: str,
        practitioner_id: str,
        organization_id: str,
        **data,
    ):
        """
        Initializes the ProcedureRequestFHIR instance with necessary references.

        Args:
            procedure (str): The description of the procedure to perform.
            patient_id (str): The ID of the Patient.
            practitioner_id (str): The ID of the Practitioner making the request.
            organization_id (str): The ID of the Organization performing the request.
        """
        # super().__init__(procedure=procedure, procedure_extended=procedure_extended, **data)
        super().__init__(procedure=procedure, **data)

        # Validate and set references
        self._patient_reference = get_patient_reference(patient_id)
        self._requester_reference = get_practitioner_reference(practitioner_id)
        self._performer_reference = get_performer_reference(organization_id)
        self._authored_on = datetime.datetime.now()

    def to_fhir(self) -> ServiceRequest:
        # Use text-only concept here; coded match is resolved downstream.
        procedure_code = CodeableReference(concept=CodeableConcept(text=self.procedure))
        service_request = ServiceRequest(
            status="active",
            intent="order",
            code=procedure_code,
            subject=Reference(
                reference=self._patient_reference,
                display=f"Patient ID: {self._patient_reference}",
            ),
            authoredOn=DateTime.validate(self._authored_on.isoformat()),
            requester=Reference(
                reference=self._requester_reference,
                display=f"Practitioner Name: {self._requester_reference}",
            ),
            performer=[
                Reference(
                    reference=self._performer_reference,
                    display=f"Requesting Organization: {self._performer_reference}",
                )
            ],
        )

        print(colored(f"Procedure service request: {service_request}", "cyan"))

        return service_request


class ProcedureSearch(BaseModel):
    """Search for a procedure and receive a list of up to 10 options that you can call the `ProcedureRequestFHIR` tool with.
    Always search for possible procedures with this tool before using the `ProcedureRequestFHIR` tool.
    """

    procedure: str = Field(
        description="Short description of the procedure to perform. This involves therapeutic procedures, like surgeries. For mostly diagnostic procedures like `ERCP` use the `RadiologyRequestFHIR` tool.",
        example="laparoscopic cholecystectomy",
    )
    _patient_reference: str = PrivateAttr()
    _requester_reference: str = PrivateAttr()
    _performer_reference: str = PrivateAttr()
    _authored_on: datetime.datetime = PrivateAttr()

    def __init__(
        self,
        *,
        procedure: str,
        # procedure_extended: str,
        patient_id: str,
        practitioner_id: str,
        organization_id: str,
        **data,
    ):
        """
        Initializes the ProcedureRequestFHIR instance with necessary references.

        Args:
            procedure (str): The description of the procedure to perform.
            patient_id (str): The ID of the Patient.
            practitioner_id (str): The ID of the Practitioner making the request.
            organization_id (str): The ID of the Organization performing the request.
        """
        # super().__init__(procedure=procedure, procedure_extended=procedure_extended, **data)
        super().__init__(procedure=procedure, **data)

        # Validate and set references
        self._patient_reference = get_patient_reference(patient_id)
        self._requester_reference = get_practitioner_reference(practitioner_id)
        self._performer_reference = get_performer_reference(organization_id)
        self._authored_on = datetime.datetime.now()

    def to_fhir(self) -> ServiceRequest:
        # Use text-only concept here; coded match is resolved downstream.
        procedure_code = CodeableReference(concept=CodeableConcept(text=self.procedure))
        service_request = ServiceRequest(
            status="active",
            intent="order",
            code=procedure_code,
            subject=Reference(
                reference=self._patient_reference,
                display=f"Patient ID: {self._patient_reference}",
            ),
            authoredOn=DateTime.validate(self._authored_on.isoformat()),
            requester=Reference(
                reference=self._requester_reference,
                display=f"Practitioner Name: {self._requester_reference}",
            ),
            performer=[
                Reference(
                    reference=self._performer_reference,
                    display=f"Requesting Organization: {self._performer_reference}",
                )
            ],
        )

        return service_request


class MedicationRequestList(BaseModel):
    """Request for a list of medications"""

    medications: List[MedicationRequestFHIR] = Field(
        description="The list of medications"
    )


class MicrobiologyRequestList(BaseModel):
    """Request for a list of microbiology tests"""

    microbiology_tests: List[MicrobiologyRequestFHIR] = Field(
        description="The list of microbiology tests"
    )


class LabRequestList(BaseModel):
    """Request for a list of lab values"""

    lab_values: List[LabRequestFHIR] = Field(
        ..., description="The list of lab values to request for the patient."
    )


class PhysicalExamination(BaseModel):
    """Perform a physical examination of a patient."""

    ...


# new revision
class VitalSigns(BaseModel):
    """Get the vital signs of a patient (Temperature, heart rate, respiratory rate, o2 saturation, blood pressure, pain, etc.)."""

    # Watch out we fetch this from triage ; not from vitalsigns table
    ...


class Finish(BaseModel):
    """Indicate that the patient case is ready for to be closed in the emergency department, once you have thoroughly completed all necessary diagnostic and therapeutic steps so far."""

    diagnosis: str = Field(
        description="The diagnosis of the patient in short form. Example: `Left sided pneumonia`"
    )


class Plan(BaseModel):
    """Generate a structured sequence of next actions and steps to be taken to complete the patient case."""

    ...


class PatientHistory(BaseModel):
    """Lookup available information about the patient history from previous visits or from external sources."""

    ...


@register_class
class UrineRequestFHIR(BaseModel):
    """Request for a single Urine Value"""

    urine_value: UrineValue = Field(
        description="The urine value to request, selected from the UrineValue Enum.",
        example=UrineValue._51486,
    )

    # not shown to the LLM via ".model_schema()"
    _patient_reference: str = PrivateAttr()
    _requester_reference: str = PrivateAttr()
    _performer_reference: str = PrivateAttr()
    _authored_on: datetime.datetime = PrivateAttr()
    _lab_value_loinc_code: str = PrivateAttr()

    def __init__(
        self,
        *,
        urine_value: UrineValue,
        patient_id: str,
        practitioner_id: str,
        organization_id: str,
        **data,
    ):
        """
        Initializes the LabRequestFHIR instance with necessary references.

        Args:
            lab_value (BloodValue): The blood value to request.
            patient_id (str): The ID of the Patient.
            practitioner_id (str): The ID of the Practitioner making the request.
            organization_id (str): The ID of the Organization performing the request.
        """
        super().__init__(urine_value=urine_value, **data)

        # Validate and set references
        self._patient_reference = get_patient_reference(patient_id)
        self._requester_reference = get_practitioner_reference(practitioner_id)
        self._performer_reference = get_performer_reference(organization_id)
        self._authored_on = datetime.datetime.now()
        self._urine_value_loinc_code = UrineValue(self.urine_value).name[
            1:
        ]  # remove "_"-prefix

        self._urine_value_omop_concept_code = lab_itemid_to_omop_concept.get(
            self.urine_value
        )

    def to_fhir(self):
        urine_request = ServiceRequest(
            resourceType="ServiceRequest",
            id=str(uuid4()),
            status="active",
            intent="order",
            category=[
                CodeableConcept(
                    coding=[
                        Coding(
                            system="http://terminology.hl7.org/CodeSystem/service-category",
                            code="laboratory",
                            display="Laboratory",
                        )
                    ],
                    text="Laboratory",
                )
            ],
            code=CodeableReference(
                concept=CodeableConcept(
                    coding=[
                        Coding(
                            # mapping from here: https://github.com/MIT-LCP/mimic-code/blob/e39825259beaa9d6bc9b99160049a5d251852aae/mimic-iv/mapping/d_labitems_to_loinc.csv
                            system="http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems",
                            code=self._urine_value_loinc_code,  # LOINC code for "Complete Blood Count (CBC) panel"
                            display=self.urine_value,
                        ),
                        Coding(
                            # mapping from here: https://github.com/MIT-LCP/mimic-code/blob/e39825259beaa9d6bc9b99160049a5d251852aae/mimic-iv/mapping/d_labitems_to_loinc.csv
                            system="https://fhir-terminology.ohdsi.org",
                            code=self._urine_value_omop_concept_code,  # OMOP Concept Code
                            display=self.urine_value,
                        ),
                    ]
                )
            ),
            subject=Reference(
                reference=self._patient_reference,
                display=f"Patient Name: {self._patient_reference}",
            ),
            authoredOn=DateTime.validate(self._authored_on.isoformat()),
            requester=Reference(
                reference=self._requester_reference,
                display=f"Practitioner Name: {self._requester_reference}",
            ),
            performer=[
                Reference(
                    reference=self._performer_reference,
                    display=f"Requesting Organization: {self._performer_reference}",
                )
            ],
        )
        return urine_request


class UrineRequestList(BaseModel):
    """Request for a list of urine values"""

    urine_values: List[UrineRequestFHIR] = Field(
        ..., description="The list of urine values to request for the patient."
    )


# new for revision
@register_class
class VitalSignsRequestFHIR(BaseModel):
    """
    Request for a Vital-Signs panel (LOINC 85353-1).
    """

    _patient_reference: str = PrivateAttr()
    _requester_reference: str = PrivateAttr()
    _performer_reference: str = PrivateAttr()
    _authored_on: datetime.datetime = PrivateAttr()
    _vs_code: str = PrivateAttr()

    def __init__(
        self,
        *,
        patient_id: str,
        practitioner_id: str,
        organization_id: str,
        **data,
    ):
        """
        Args:
            patient_id (str): The Patient’s logical ID.
            practitioner_id (str): The Practitioner placing the order.
            organization_id (str): The Organization expected to perform it.
        """
        super().__init__(**data)

        # Build FHIR references once, store privately
        self._patient_reference = get_patient_reference(patient_id)
        self._requester_reference = get_practitioner_reference(practitioner_id)
        self._performer_reference = get_performer_reference(organization_id)

        self._authored_on = datetime.datetime.now()
        self._vs_code = "85353-1"  # Vital-signs panel, LOINC; # build from: https://loinc.org/85353-1

    def to_fhir(self) -> ServiceRequest:
        """
        Creates and returns a `ServiceRequest` FHIR resource that orders a
        Vital-Signs panel for the given patient.
        """
        vs_request = ServiceRequest(
            resourceType="ServiceRequest",
            id=str(uuid4()),
            status="active",
            intent="order",
            category=[
                CodeableConcept(
                    coding=[
                        Coding(
                            system="http://terminology.hl7.org/CodeSystem/service-category",
                            code="exam",
                            display="Examination",
                        )
                    ],
                    text="Vital Signs",
                )
            ],
            code=CodeableReference(
                concept=CodeableConcept(
                    coding=[
                        Coding(
                            system="http://loinc.org",
                            code=self._vs_code,
                            display="Vital signs panel",
                        )
                    ],
                    text="Vital signs panel",
                )
            ),
            subject=Reference(
                reference=self._patient_reference,
                display=f"Patient Name: {self._patient_reference}",
            ),
            authoredOn=DateTime.validate(self._authored_on.isoformat()),
            requester=Reference(
                reference=self._requester_reference,
                display=f"Practitioner Name: {self._requester_reference}",
            ),
            performer=[
                Reference(
                    reference=self._performer_reference,
                    display=f"Requesting Organization: {self._performer_reference}",
                )
            ],
        )
        return vs_request


class CloseCase(BaseModel):
    """
    Finalizes the emergency department (ED) case after all required diagnostic and therapeutic actions have been taken.
    Use this only after you are certain the case is ready for closure—no further workup or acute intervention is needed.
    """

    diagnosis: str = Field(
        ...,
        description=(
            "Concise primary diagnosis, ideally with location or severity as relevant. "
            "Examples: 'Left lower lobe pneumonia', 'Uncomplicated appendicitis', 'NSTEMI'."
        ),
    )

    decision: Literal["discharge", "admission"] = Field(
        ...,
        description=(
            "Final ED disposition: 'discharge' if the patient is safe to go home (eventually with follow-up visits the next 24-48 hrs), "
            "'admission' if inpatient care is required (including observation stays). "
            "Choose based on clinical status, risk, and standard of care."
        ),
    )

    reasoning: str = Field(
        ...,
        description=(
            "Short but clear summary explaining the rationale for the disposition. "
            "Address clinical stability, risk factors, social situation, need for monitoring, or specific findings. "
            "Examples: 'Patient is stable, afebrile, reliable for follow-up—safe for discharge.' "
            "'Needs IV antibiotics and close monitoring—admit to medicine.'"
            "Whenever possible, include clinical scores (e.g. qSOFA) etc for evidence."
        ),
    )
