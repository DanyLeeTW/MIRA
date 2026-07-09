---
type: community
cohesion: 0.06
members: 96
---

# FHIR Request Handlers

**Cohesion:** 0.06 - loosely connected
**Members:** 96 nodes

## Members
- [[.__init__()_3]] - code - src/fhir_handlers.py
- [[.__init__()_5]] - code - src/fhir_handlers.py
- [[.__init__()_7]] - code - src/fhir_handlers.py
- [[.__init__()_6]] - code - src/fhir_handlers.py
- [[.__init__()_10]] - code - src/fhir_handlers.py
- [[.__init__()_9]] - code - src/fhir_handlers.py
- [[.__init__()_8]] - code - src/fhir_handlers.py
- [[.__init__()_4]] - code - src/fhir_handlers.py
- [[.__init__()_11]] - code - src/fhir_handlers.py
- [[._fetch_result_impl()_7]] - code - src/fhir_handlers.py
- [[.search()]] - code - src/qdrant_collection.py
- [[.to_fhir()_1]] - code - src/fhir_handlers.py
- [[.to_fhir()_3]] - code - src/fhir_handlers.py
- [[.to_fhir()_5]] - code - src/fhir_handlers.py
- [[.to_fhir()_4]] - code - src/fhir_handlers.py
- [[.to_fhir()_8]] - code - src/fhir_handlers.py
- [[.to_fhir()_7]] - code - src/fhir_handlers.py
- [[.to_fhir()_6]] - code - src/fhir_handlers.py
- [[.to_fhir()_2]] - code - src/fhir_handlers.py
- [[.to_fhir()_9]] - code - src/fhir_handlers.py
- [[.to_fhir()_11]] - code - src/tools.py
- [[A class representing a procedure request in FHIR format that is requested for a]] - rationale - src/tools.py
- [[ABC]] - code
- [[Abstract Base Class for FHIR Resource Handlers.]] - rationale - src/fhir_handlers.py
- [[Any_6]] - code
- [[BaseModel_3]] - code
- [[CloseCase]] - code - src/tools.py
- [[Convert MedicationRequestFHIR to FHIR MedicationRequest.]] - rationale - src/fhir_handlers.py
- [[Convert MicrobiologyRequestFHIR to FHIR ServiceRequest.]] - rationale - src/fhir_handlers.py
- [[DataFrame_9]] - code
- [[Decorator to handle errors and log them.]] - rationale - src/fhir_handlers.py
- [[FHIRResourceHandler]] - code - src/fhir_handlers.py
- [[Fetches the top_k matching procedure codes using vector database search.      Ar]] - rationale - src/mimic_to_fhir.py
- [[Filter]] - code
- [[Finalizes the emergency department (ED) case after all required diagnostic and t]] - rationale - src/tools.py
- [[Finish]] - code - src/tools.py
- [[Generate a structured sequence of next actions and steps to be taken to complete]] - rationale - src/tools.py
- [[Get the vital signs of a patient (Temperature, heart rate, respiratory rate, o2]] - rationale - src/tools.py
- [[Handles the LabRequestFHIR instance and fetches the result.]] - rationale - src/fhir_handlers.py
- [[Handles the MedicationRequestFHIR instance and processes the request.]] - rationale - src/fhir_handlers.py
- [[Handles the MicrobiologyRequestFHIR instance and processes the request.]] - rationale - src/fhir_handlers.py
- [[Handles the PhysicalExamRequestFHIR instance and fetches the result.]] - rationale - src/fhir_handlers.py
- [[Handles the UrineRequestFHIR instance and fetches the result.]] - rationale - src/fhir_handlers.py
- [[Handles the VitalSigns instance and fetches the result.]] - rationale - src/fhir_handlers.py
- [[Indicate that the patient case is ready for to be closed in the emergency depart]] - rationale - src/tools.py
- [[LabRequestFHIR]] - code - src/tools.py
- [[LabRequestHandler]] - code - src/fhir_handlers.py
- [[LabRequestList]] - code - src/tools.py
- [[MedicationRequest]] - code
- [[MedicationRequestFHIR]] - code - src/tools.py
- [[MedicationRequestHandler]] - code - src/fhir_handlers.py
- [[MedicationRequestList]] - code - src/tools.py
- [[MicrobiologyRequestFHIR]] - code - src/tools.py
- [[MicrobiologyRequestHandler]] - code - src/fhir_handlers.py
- [[MicrobiologyRequestList]] - code - src/tools.py
- [[Perform a physical examination of a patient.]] - rationale - src/tools.py
- [[PhysicalExamRequestFHIR]] - code - src/tools.py
- [[PhysicalExamRequestHandler]] - code - src/fhir_handlers.py
- [[PhysicalExamination]] - code - src/tools.py
- [[Plan]] - code - src/tools.py
- [[ProcedureRequestFHIR]] - code - src/tools.py
- [[ProcedureRequestHandler]] - code - src/fhir_handlers.py
- [[ProcedureSearch]] - code - src/tools.py
- [[ProcedureSearchRequestHandler]] - code - src/fhir_handlers.py
- [[Qdrant_Collection]] - code - src/qdrant_collection.py
- [[RadiologyRequestFHIR]] - code - src/tools.py
- [[RadiologyRequestHandler]] - code - src/fhir_handlers.py
- [[Request for Physical Examination data.]] - rationale - src/tools.py
- [[Request for a Microbiology Test]] - rationale - src/tools.py
- [[Request for a Vital-Signs panel (LOINC 85353-1).]] - rationale - src/tools.py
- [[Request for a list of lab values]] - rationale - src/tools.py
- [[Request for a list of medications]] - rationale - src/tools.py
- [[Request for a list of microbiology tests]] - rationale - src/tools.py
- [[Request for a list of urine values]] - rationale - src/tools.py
- [[Request for a radiology examination. Venous Ultrasound refers to a venous ultr]] - rationale - src/tools.py
- [[Request for a single Lab Value]] - rationale - src/tools.py
- [[Request for a single Urine Value]] - rationale - src/tools.py
- [[Request for a single medication]] - rationale - src/tools.py
- [[Search for a procedure and receive a list of up to 10 options that you can call]] - rationale - src/tools.py
- [[Search the collection with a query and filter. Generic method - query_filter nee]] - rationale - src/qdrant_collection.py
- [[ServiceRequest]] - code
- [[UrineRequestFHIR]] - code - src/tools.py
- [[UrineRequestHandler]] - code - src/fhir_handlers.py
- [[UrineRequestList]] - code - src/tools.py
- [[VitalSignRequestHandler]] - code - src/fhir_handlers.py
- [[VitalSigns]] - code - src/tools.py
- [[VitalSignsRequestFHIR]] - code - src/tools.py
- [[_import_local_module()]] - code - src/tools.py
- [[_normalize_code()]] - code - src/tools.py
- [[_split_codes()]] - code - src/tools.py
- [[fetch_procedure_search_results()]] - code - src/mimic_to_fhir.py
- [[fhir_handlers.py]] - code - src/fhir_handlers.py
- [[handle_errors()]] - code - src/fhir_handlers.py
- [[rA Qdrant vector database collection.]] - rationale - src/qdrant_collection.py
- [[register_class()]] - code - src/tools.py
- [[tools.py]] - code - src/tools.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/FHIR_Request_Handlers
SORT file.name ASC
```

## Connections to other communities
- 22 edges to [[_COMMUNITY_Tool Execution]]
- 16 edges to [[_COMMUNITY_FHIR Implementation]]
- 15 edges to [[_COMMUNITY_Medical Enums]]
- 11 edges to [[_COMMUNITY_FHIR Observations]]
- 9 edges to [[_COMMUNITY_FHIR Resources]]
- 9 edges to [[_COMMUNITY_Module Cluster 21]]
- 6 edges to [[_COMMUNITY_Module Cluster 18]]
- 4 edges to [[_COMMUNITY_Module Cluster 25]]
- 3 edges to [[_COMMUNITY_Module Cluster 20]]
- 2 edges to [[_COMMUNITY_Module Cluster 30]]
- 1 edge to [[_COMMUNITY_FHIR Backend]]
- 1 edge to [[_COMMUNITY_Module Cluster 17]]
- 1 edge to [[_COMMUNITY_Module Cluster 26]]

## Top bridge nodes
- [[fhir_handlers.py]] - degree 18, connects to 3 communities
- [[tools.py]] - degree 34, connects to 2 communities
- [[FHIRResourceHandler]] - degree 28, connects to 2 communities
- [[MicrobiologyRequestFHIR]] - degree 21, connects to 2 communities
- [[ProcedureRequestFHIR]] - degree 20, connects to 2 communities