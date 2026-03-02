# mypy: ignore-errors

"""This whole file has a lot of redundancy in event handlers and could be simplified"""

import asyncio
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, List, Optional, Union

import pandas as pd
from backend.log import logger
from fhir.resources.diagnosticreport import DiagnosticReport
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.observation import Observation
from fhir.resources.procedure import Procedure

# from fhir.resources.resource import Resource
from fhir.resources.servicerequest import ServiceRequest
from fhir_observations import (
    generate_lab_observation_resource,
    generate_medication_observation_resource,
    generate_microbiology_observations,
    generate_pe_observation_resource,
    generate_procedure_resource,
    generate_procedure_search_resource,
    generate_radiology_report_resource,
    generate_urine_observation_resource,
    generate_vital_sign_observation_resource,
)
from mimic_to_fhir import (
    fetch_lab_results,
    fetch_medication_results,
    fetch_microbiology_results,
    fetch_pe_results,
    fetch_procedure_request_results,
    fetch_procedure_search_results,
    fetch_radiology_results,
    fetch_urine_results,
    fetch_vital_sign_results,
)
from qdrant_collection import Qdrant_Collection
from tools import (
    LabRequestFHIR,
    MedicationRequestFHIR,
    MicrobiologyRequestFHIR,
    PhysicalExamRequestFHIR,
    ProcedureRequestFHIR,
    ProcedureSearch,
    RadiologyRequestFHIR,
    UrineRequestFHIR,
    VitalSigns,
)


def handle_errors(func):
    """
    Decorator to handle errors and log them.
    """

    if asyncio.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                raise

        return async_wrapper
    else:

        @wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                raise

        return sync_wrapper


class FHIRResourceHandler(ABC):
    """
    Abstract Base Class for FHIR Resource Handlers.
    """

    @abstractmethod
    def to_fhir(self) -> Any:
        """Convert to a FHIR resource."""
        pass

    @handle_errors
    async def fetch_result(self, patient_id: str, patient_hadm_id: str) -> pd.Series:
        """Fetch the result using the specialist implementation."""
        return await self._fetch_result_impl(patient_id, patient_hadm_id)

    @handle_errors
    async def generate_result_resource(
        self,
        result: pd.Series,
        patient_id: str,
        service_request_id: str,
        organization_id: str,
    ) -> Observation:
        """Generate the result resource using the specialist implementation."""
        return await self._generate_result_resource_impl(
            result, patient_id, service_request_id, organization_id
        )

    @abstractmethod
    async def _fetch_result_impl(
        self, patient_id: str, patient_hadm_id: str
    ) -> pd.Series:
        """Specialist implementation for fetching results."""
        ...

    @abstractmethod
    async def _generate_result_resource_impl(
        self,
        result: pd.Series,
        patient_id: str,
        service_request_id: str,
        organization_id: str,
    ) -> Observation:
        """Specialist implementation for generating result resources."""
        ...


class LabRequestHandler(FHIRResourceHandler):
    """Handles the LabRequestFHIR instance and fetches the result."""

    def __init__(self, request: LabRequestFHIR, patient_data: pd.DataFrame):
        self.request = request
        self.patient_data = patient_data

    def to_fhir(self) -> ServiceRequest:
        service_request = self.request.to_fhir()
        logger.info(
            f"Converted LabRequestFHIR to ServiceRequest: {service_request.json()}"
        )
        return service_request

    async def _fetch_result_impl(
        self, patient_id: str, patient_hadm_id: str
    ) -> pd.Series:
        """Specialist implementation to fetch lab results."""
        return await asyncio.to_thread(
            fetch_lab_results,
            self.request,
            self.patient_data,
            patient_id,
            patient_hadm_id,
        )

    async def _generate_result_resource_impl(
        self,
        result: pd.Series,
        patient_id: str,
        service_request_id: str,
        organization_id: str,
    ) -> Observation:
        """Specialist implementation to generate Observation resource."""
        return await asyncio.to_thread(
            generate_lab_observation_resource,
            self.request,
            result,
            patient_id,
            service_request_id,
            organization_id,
        )


class UrineRequestHandler(FHIRResourceHandler):
    """Handles the UrineRequestFHIR instance and fetches the result."""

    def __init__(self, request: UrineRequestFHIR, patient_data: pd.DataFrame):
        self.request = request
        self.patient_data = patient_data

    def to_fhir(self) -> ServiceRequest:
        service_request = self.request.to_fhir()
        logger.info(
            f"Converted UrineRequestFHIR to ServiceRequest: {service_request.json()}"
        )
        return service_request

    async def _fetch_result_impl(
        self, patient_id: str, patient_hadm_id: str
    ) -> pd.Series:
        """Specialist implementation to fetch lab results."""
        return await asyncio.to_thread(
            fetch_urine_results,
            self.request,
            self.patient_data,
            patient_id,
            patient_hadm_id,
        )

    async def _generate_result_resource_impl(
        self,
        result: pd.Series,
        patient_id: str,
        service_request_id: str,
        organization_id: str,
    ) -> Observation:
        """Specialist implementation to generate Observation resource."""
        return await asyncio.to_thread(
            generate_urine_observation_resource,
            self.request,
            result,
            patient_id,
            service_request_id,
            organization_id,
        )


class MedicationRequestHandler(FHIRResourceHandler):
    """Handles the MedicationRequestFHIR instance and processes the request."""

    def __init__(self, request: MedicationRequestFHIR, patient_data: pd.DataFrame):
        self.request = request
        self.patient_data = patient_data

    def to_fhir(self) -> MedicationRequest:
        """Convert MedicationRequestFHIR to FHIR MedicationRequest."""
        medication_request = self.request.to_fhir()
        logger.info(
            f"Converted MedicationRequestFHIR to MedicationRequest: {medication_request.json()}"
        )
        return medication_request

    async def _fetch_result_impl(
        self, patient_id: str, patient_hadm_id: str
    ) -> Optional[pd.Series]:
        """
        Specialist implementation to fetch medication results.
        Since there's no ground truth, we'll simulate the medication confirmation.
        """
        return await asyncio.to_thread(
            fetch_medication_results,
            self.request,
            self.patient_data,
            patient_id,
            patient_hadm_id,
        )

    async def _generate_result_resource_impl(
        self,
        result: Optional[pd.Series],
        patient_id: str,
        service_request_id: str,
        organization_id: str,
    ) -> Observation:
        """
        Specialist implementation to generate Observation resource from MedicationRequest.
        """
        return await asyncio.to_thread(
            generate_medication_observation_resource,
            self.request,
            result,
            patient_id,
            service_request_id,
            organization_id,
        )


class PhysicalExamRequestHandler(FHIRResourceHandler):
    """Handles the PhysicalExamRequestFHIR instance and fetches the result."""

    def __init__(self, request: PhysicalExamRequestFHIR, patient_data: pd.DataFrame):
        self.request = request
        self.patient_data = patient_data

    def to_fhir(self) -> ServiceRequest:
        service_request = self.request.to_fhir()
        logger.info(
            f"Converted PhysicalExamRequestFHIR to ServiceRequest: {service_request.json()}"
        )
        return service_request

    async def _fetch_result_impl(
        self, patient_id: str, patient_hadm_id: str
    ) -> Optional[str]:
        """Fetch the PE data for the patient."""
        return await asyncio.to_thread(
            fetch_pe_results,
            self.request,
            self.patient_data,
            patient_id,
            patient_hadm_id,
        )

    async def _generate_result_resource_impl(
        self,
        result: Optional[str],
        patient_id: str,
        service_request_id: str,
        organization_id: str,
    ) -> Observation:
        """Generate the Observation resource containing the PE data."""
        return await asyncio.to_thread(
            generate_pe_observation_resource,
            self.request,
            result,
            patient_id,
            service_request_id,
            organization_id,
        )


class MicrobiologyRequestHandler(FHIRResourceHandler):
    """Handles the MicrobiologyRequestFHIR instance and processes the request."""

    def __init__(self, request: MicrobiologyRequestFHIR, patient_data: pd.DataFrame):
        self.request = request
        self.patient_data = patient_data

    def to_fhir(self) -> ServiceRequest:
        """Convert MicrobiologyRequestFHIR to FHIR ServiceRequest."""
        service_request = self.request.to_fhir()
        logger.info(
            f"Converted MicrobiologyRequestFHIR to ServiceRequest: {service_request.json()}"
        )
        return service_request

    async def _fetch_result_impl(
        self, patient_id: str, patient_hadm_id: str
    ) -> Optional[pd.Series]:
        """Fetch the microbiology data for the patient."""
        return await asyncio.to_thread(
            fetch_microbiology_results,
            self.request,
            self.patient_data,
            patient_id,
            patient_hadm_id,
        )

    async def _generate_result_resource_impl(
        self,
        result: Optional[pd.Series],
        patient_id: str,
        service_request_id: str,
        organization_id: str,
    ) -> List[Observation]:
        """
        Specialist implementation to generate Observation resources for microbiology test.

        Returns a list of Observations: [MicroTestObservation, MicroOrgObservation, MicroSuscObservation]
        """
        # Generate the MimicObservationMicroTest resource

        return await asyncio.to_thread(
            generate_microbiology_observations,
            self.request,
            result,
            patient_id,
            service_request_id,
            organization_id,
        )


class RadiologyRequestHandler(FHIRResourceHandler):
    def __init__(self, request: RadiologyRequestFHIR, patient_data: pd.DataFrame):
        self.request = request
        self.patient_data = patient_data

    def to_fhir(self) -> ServiceRequest:
        service_request = self.request.to_fhir()
        logger.info(
            f"Converted RadiologyRequestFHIR to ServiceRequest: {service_request.json()}"
        )
        return service_request

    async def _fetch_result_impl(
        self, patient_id: str, patient_hadm_id: str
    ) -> Optional[Union[pd.Series, dict, str]]:
        # Ensure fetch_radiology_results returns the correct type
        return await asyncio.to_thread(
            fetch_radiology_results,
            self.request,
            self.patient_data,
            patient_id,
            patient_hadm_id,
        )

    async def _generate_result_resource_impl(
        self,
        result: Union[pd.Series, dict, str, None],
        patient_id: str,
        service_request_id: str,
        organization_id: str,
    ) -> DiagnosticReport:
        return await asyncio.to_thread(
            generate_radiology_report_resource,
            self.request,
            result,
            patient_id,
            service_request_id,
            organization_id,
        )


class ProcedureSearchRequestHandler(FHIRResourceHandler):
    def __init__(
        self,
        request: ProcedureSearch,
        patient_data: pd.DataFrame,
        collection: Qdrant_Collection,
    ):
        self.request = request
        self.patient_data = patient_data
        self.collection = collection

    def to_fhir(self) -> ServiceRequest:
        service_request = self.request.to_fhir()
        logger.info(
            f"Converted ProcedureRequestFHIR to ServiceRequest: {service_request.json()}"
        )
        return service_request

    async def _fetch_result_impl(
        self, patient_id: str, patient_hadm_id: str
    ) -> Optional[List[dict]]:
        # Fetch procedure options from the vector database
        return await asyncio.to_thread(
            fetch_procedure_search_results,
            self.request,
            self.collection,
            patient_id,
            patient_hadm_id,
        )

    async def _generate_result_resource_impl(
        self,
        result: Union[List[dict], None],
        patient_id: str,
        service_request_id: str,
        organization_id: str,
    ) -> Procedure:
        return await asyncio.to_thread(
            generate_procedure_search_resource,
            self.request,
            result,
            patient_id,
            service_request_id,
            organization_id,
        )


class ProcedureRequestHandler(FHIRResourceHandler):
    def __init__(
        self,
        request: ProcedureRequestFHIR,
        patient_data: pd.DataFrame,
        collection: Optional[Qdrant_Collection] = None,
    ):
        self.request = request
        self.patient_data = patient_data
        self.collection = collection

    def to_fhir(self) -> ServiceRequest:
        service_request = self.request.to_fhir()
        logger.info(
            f"Converted ProcedureRequestFHIR to ServiceRequest: {service_request.json()}"
        )
        return service_request

    async def _fetch_result_impl(
        self, patient_id: str, patient_hadm_id: str
    ) -> Optional[Any]:
        # Fetch procedure options from the vector database
        return await asyncio.to_thread(
            fetch_procedure_request_results,
            self.request,
            self.collection,
            patient_id,
            patient_hadm_id,
        )

    async def _generate_result_resource_impl(
        self,
        result: Optional[Any],
        patient_id: str,
        service_request_id: str,
        organization_id: str,
    ) -> Procedure:
        return await asyncio.to_thread(
            generate_procedure_resource,
            self.request,
            result,
            patient_id,
            service_request_id,
            organization_id,
        )


# new revision
class VitalSignRequestHandler(FHIRResourceHandler):
    """Handles the VitalSigns instance and fetches the result."""

    def __init__(self, request: VitalSigns, patient_data: pd.DataFrame):
        self.request = request
        self.patient_data = patient_data

    def to_fhir(self) -> ServiceRequest:
        service_request = self.request.to_fhir()
        logger.info(f"Converted VitalSigns to ServiceRequest: {service_request.json()}")
        return service_request

    async def _fetch_result_impl(
        self, patient_id: str, patient_hadm_id: str
    ) -> Optional[str]:
        """Fetch the PE data for the patient."""
        return await asyncio.to_thread(
            fetch_vital_sign_results,
            self.request,
            self.patient_data,
            patient_id,
            patient_hadm_id,
        )

    async def _generate_result_resource_impl(
        self,
        result: Optional[str],
        patient_id: str,
        service_request_id: str,
        organization_id: str,
    ) -> Observation:
        """Generate the Observation resource containing the PE data."""
        return await asyncio.to_thread(
            generate_vital_sign_observation_resource,
            self.request,
            result,
            patient_id,
            service_request_id,
            organization_id,
        )
