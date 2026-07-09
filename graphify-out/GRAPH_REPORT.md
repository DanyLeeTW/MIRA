# Graph Report - .  (2026-07-09)

## Corpus Check
- 77 files · ~71,042 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 785 nodes · 1480 edges · 47 communities (40 shown, 7 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 223 edges (avg confidence: 0.65)
- Token cost: 15,000 input · 8,000 output

## Community Hubs (Navigation)
- FHIR Request Handlers
- Medical Enums
- Agent Architecture Docs
- Evaluation Framework
- Dataset Core
- FHIR Implementation
- Lab Data Processing
- Tool Execution
- Code Mapping
- FHIR Backend
- Agent Orchestration
- FHIR Observations
- FHIR Resources
- Dataset Tracking
- Visualization Output
- Module Cluster 15
- Module Cluster 16
- Module Cluster 17
- Module Cluster 18
- Module Cluster 19
- Module Cluster 20
- Module Cluster 21
- Module Cluster 22
- Module Cluster 23
- Module Cluster 24
- Module Cluster 25
- Module Cluster 26
- Module Cluster 27
- Module Cluster 28
- Module Cluster 29
- Module Cluster 30
- Module Cluster 31
- Module Cluster 32
- Module Cluster 33
- Module Cluster 34
- Module Cluster 35
- Module Cluster 36
- Module Cluster 37
- Module Cluster 38

## God Nodes (most connected - your core abstractions)
1. `FHIRResourceHandler` - 28 edges
2. `Qdrant_Collection` - 25 edges
3. `extract_data()` - 24 edges
4. `MIMIC_Dataset` - 22 edges
5. `MicrobiologyRequestFHIR` - 21 edges
6. `ProcedureRequestFHIR` - 20 edges
7. `RadiologyRequestFHIR` - 19 edges
8. `LabRequestHandler` - 18 edges
9. `UrineRequestHandler` - 18 edges
10. `MedicationRequestHandler` - 18 edges

## Surprising Connections (you probably didn't know these)
- `Config` --uses--> `EvaluationOutputCollector`  [INFERRED]
  src/assistants.py → src/visualisations.py
- `main()` --indirect_call--> `read_ed_data()`  [INFERRED]
  src/dataset/make_dataset.py → src/dataset/data.py
- `extract_data()` --calls--> `sanitize_radiology_entries()`  [INFERRED]
  src/dataset/make_dataset.py → src/dataset/radiology.py
- `extract_data()` --calls--> `sanitize_hadm_texts()`  [INFERRED]
  src/dataset/make_dataset.py → src/dataset/utils.py
- `process_radiology()` --calls--> `map_note_id_to_name()`  [INFERRED]
  src/dataset/radiology.py → src/dataset/utils.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Medical Agent Tool Chain** — docs_mira_medassistant, docs_mira_plan_tool, docs_mira_physicalexamination, docs_mira_labrequestlist, docs_mira_radiologyrequestfhir, docs_mira_medicationrequestfhir, docs_mira_procedurerequestfhir, docs_mira_closecase_tool [EXTRACTED 1.00]
- **Clinical Workflow Phases** — docs_mira_history_taking_phase, docs_mira_diagnostic_planning_phase, docs_mira_treatment_decision_phase, docs_mira_case_closure_phase [EXTRACTED 1.00]
- **MIRA Core Module Triad** — docs_mira_tools_py, docs_mira_tool_execs_py, docs_mira_assistants_py [INFERRED 0.85]

## Communities (47 total, 7 thin omitted)

### Community 0 - "FHIR Request Handlers"
Cohesion: 0.06
Nodes (71): ABC, Filter, FHIRResourceHandler, handle_errors(), LabRequestHandler, MedicationRequestHandler, MicrobiologyRequestHandler, PhysicalExamRequestHandler (+63 more)

### Community 1 - "Medical Enums"
Cohesion: 0.06
Nodes (42): BloodValue, MicroBiologyValue, BloodValue, Enum, str, MicroBiologyValue, Enum, str (+34 more)

### Community 2 - "Agent Architecture Docs"
Cohesion: 0.06
Nodes (55): assistants.py AI Agent Implementation, Async Architecture Pattern, Phase 4: Case Closure, CloseCase Tool, code_maps.py MIMIC Code Mapping, config.py Global Configuration, Diagnosis Dataset, Phase 2: Diagnostic Planning and Execution (+47 more)

### Community 3 - "Evaluation Framework"
Cohesion: 0.07
Nodes (46): evaluate_one_file(), get_file_paths(), main(), OpenAI, Path, Main function to evaluate assistant outputs for a given diagnosis., Recursively get all .jsonl file paths under the given base path.      Args:, Evaluate a single assistant output file against the ground truth and write the e (+38 more)

### Community 4 - "Dataset Core"
Cohesion: 0.06
Nodes (21): Config, MIMIC_Dataset, MIMIC_Hadm_Dataset, BaseModel, Class to hold data for a MIMIC dataset filtered for a specific diagnosis.      T, Save the dataset to a metadata.json and parquet (pd.DataFrame) files, Save the dataset to a metadata.json and excel (pd.DataFrame) files, Save the dataset to a metadata.json and csv (pd.DataFrame) files (+13 more)

### Community 5 - "FHIR Implementation"
Cohesion: 0.07
Nodes (31): Any, Specialist implementation to fetch lab results., Specialist implementation to fetch lab results., Specialist implementation to fetch medication results.         Since there's no, Fetch the PE data for the patient., Fetch the microbiology data for the patient., Fetch the PE data for the patient., Convert to a FHIR resource. (+23 more)

### Community 6 - "Lab Data Processing"
Cohesion: 0.08
Nodes (25): match_lab_events_to_loinc(), add_extracted_rad_events(), check_radiology_modality_region(), concatenate_cases(), main(), make_dataset(), make_pe_admission_dataset(), make_pneumonia_admission_dataset() (+17 more)

### Community 7 - "Tool Execution"
Cohesion: 0.10
Nodes (34): QdrantClient, close_case(), connect_qdrant(), finish(), generate_routine(), generate_routine_optional_admission(), get_blood_value_results(), get_medication_results() (+26 more)

### Community 8 - "Code Mapping"
Cohesion: 0.12
Nodes (26): get_atc_code_from_umls(), get_drug_codes_from_name(), get_loinc_code_from_modality_region(), get_medication_codes(), get_ndc_codes_from_name(), get_rxnorm_code_from_name(), get_rxnorm_code_from_ndc(), get_snomed_code_from_modality_region() (+18 more)

### Community 9 - "FHIR Backend"
Cohesion: 0.10
Nodes (22): Organization, Practitioner, create_fhir_session(), post_fhir_resource(), Session, Creates and configures a requests.Session with retry logic.      Args:         r, Posts a FHIR resource to the server with enhanced error handling and logging., generate_organization_resource() (+14 more)

### Community 10 - "Agent Orchestration"
Cohesion: 0.11
Nodes (17): call_chat(), Config, format_conversation(), MedAssistant, PatientAssistant, BaseModel, A class representing an AI assistant with various attributes and methods for int, Update the patient info in the patient context. (+9 more)

### Community 11 - "FHIR Observations"
Cohesion: 0.17
Nodes (20): generate_lab_observation_resource(), generate_medication_observation_resource(), generate_micro_org_observation_resource(), generate_micro_susc_observation_resource(), generate_micro_test_observation_resource(), generate_microbiology_observations(), generate_pe_observation_resource(), generate_urine_observation_resource() (+12 more)

### Community 12 - "FHIR Resources"
Cohesion: 0.13
Nodes (11): Observation, Series, Generate the result resource using the specialist implementation., Specialist implementation for fetching results., Specialist implementation for generating result resources., Specialist implementation to generate Observation resource., Specialist implementation to generate Observation resource., Specialist implementation to generate Observation resource from MedicationReques (+3 more)

### Community 13 - "Dataset Tracking"
Cohesion: 0.14
Nodes (9): Sized, ConsortTracker, DataFrame, • If you pass a DataFrame + column(s) → counts unique rows of those cols., Write counts, edges, order to JSON so you can resume later., Load a previously saved JSON snapshot and overwrite in-memory state., Register/overwrite a box.  n=None means 'fill later'., Declare a directed connection between boxes. (+1 more)

### Community 14 - "Visualization Output"
Cohesion: 0.12
Nodes (9): EvaluationOutputCollector, GradioOutputCollector, A class to collect and display output from a simulation of patient and medical d, Collects a message to be displayed later with JavaScript.          Parameters:, Saves the collected HTML content to the specified file, allowing either immediat, Initializes the OutputCollector with a specified filename.          Parameters:, This class is used to collect and display output from a simulation of patient an, Initializes the HTML file with necessary headers and styles. (+1 more)

### Community 15 - "Module Cluster 15"
Cohesion: 0.19
Nodes (11): extract_diagnosis_from_discharge(), DataFrame, _get_env_int(), main(), Any, Runs a function with a live progress indicator and returns its result.      Para, Main function to run the dataset creation process., _resolve_diagnosis_subset() (+3 more)

### Community 16 - "Module Cluster 16"
Cohesion: 0.17
Nodes (14): extract_data(), DataFrame, Extract and process data for a specific diagnosis from various MIMIC-IV datafram, DataFrame, Check if any of the final entries in the lab events dataframe are invalid.     I, If the diagnosis is not in the long_title or it is but the seq_num is not 1, the, Validates the ED diagnosis dataframe.     An invalid hadm_id is one where the di, Check if any of the final entries in the radiology events dataframe are invalid. (+6 more)

### Community 17 - "Module Cluster 17"
Cohesion: 0.18
Nodes (14): generate_patient_resource(), get_admission_chief_complaint(), get_admission_medication(), patient_iterator(), prepare_patient(), Patient, Series, Handle the case where the admission medication is not available. (+6 more)

### Community 18 - "Module Cluster 18"
Cohesion: 0.21
Nodes (9): Distance, PointStruct, batch_upsert_procedures(), create_procedures_points(), Any, Upserts data in batches of max_batch_size.     Args:         collection (Qdrant_, Initialize a new collection.         Args:             collection_name (str): Na, Add points to the collection. Generic method - points need to be created with th (+1 more)

### Community 19 - "Module Cluster 19"
Cohesion: 0.19
Nodes (9): fill_missing_hadm_ids(), Add missing hadm_ids if the charttime of lab_events, microbiology, and radiology, read_data(), read_ed_data(), format_lab_value(), format_microbiology_value(), DataFrame, Format Laboratory values into string represntation: value unit or flag (+1 more)

### Community 20 - "Module Cluster 20"
Cohesion: 0.21
Nodes (12): get_admission_chief_complaint(), get_admission_medication(), patient_iterator(), prepare_patient(), Handle the case where the admission medication is not available., Handle the case where the admission chief complaint is not available., Prepare a single patient instance with all required resources.      Parameters:, Yield a single patient at a time along with the total length. (+4 more)

### Community 21 - "Module Cluster 21"
Cohesion: 0.27
Nodes (4): CodeableConcept, ServiceRequest, Creates and returns a `ServiceRequest` FHIR resource that orders a         Vital, Converts the MicrobiologyRequestFHIR instance to a FHIR ServiceRequest resource.

### Community 22 - "Module Cluster 22"
Cohesion: 0.21
Nodes (11): extract_admisson_medication(), extract_history(), extract_physical_examination(), extract_rad_events(), parse_report(), DataFrame, Series, Extracts the admission medication information from the discharge letter text. (+3 more)

### Community 23 - "Module Cluster 23"
Cohesion: 0.42
Nodes (11): AscitesValue, BloodValue, BoneMarrowValue, CerebrospinalFluidValue, JointFluidValue, OtherBodyFluidValue, PleuralValue, Enum (+3 more)

### Community 24 - "Module Cluster 24"
Cohesion: 0.20
Nodes (7): PatientContext, Any, Process a new input message and generate a response.          Args:, Generates a chat completion response based on the provided user input., Encapsulates all necessary context for processing patient-specific tool calls., Executes the tool calls specified in the tool_call parameter.          This meth, Converts the PatientContext to a dictionary for easy passing.

### Community 25 - "Module Cluster 25"
Cohesion: 0.27
Nodes (9): Procedure, _build_procedure_code(), _extract_procedure_payload(), generate_procedure_resource(), generate_procedure_search_resource(), Any, Procedure, Generates a Procedure FHIR resource from the procedure result.      Args: (+1 more)

### Community 26 - "Module Cluster 26"
Cohesion: 0.25
Nodes (10): get_admission_chief_complaint(), get_admission_medication(), patient_iterator(), prepare_patient(), Handle the case where the admission medication is not available., Handle the case where the admission chief complaint is not available., Prepare a single patient instance with all required resources.      Parameters:, Yield a single patient at a time along with the total length. (+2 more)

### Community 27 - "Module Cluster 27"
Cohesion: 0.22
Nodes (6): _backup_scope_from_save_dir(), Save the conversation to a JSONL file - for EVALUATION.     Args:         medica, Map a save directory to a stable backup namespace., save_conversation(), _env_path(), Path

### Community 28 - "Module Cluster 28"
Cohesion: 0.22
Nodes (8): filter_medication(), Filter medication by days in a 24hr interval for each patient, also removing dup, add_days(), map_note_id_to_name(), DataFrame, Series, Calculate the number of days since first event (medication admission, lab, radio, sanitize_hadm_texts()

### Community 29 - "Module Cluster 29"
Cohesion: 0.43
Nodes (7): action_input_pretty_printer(), count_matches(), count_radiology_modality_and_organ_matches(), itemid_to_field(), process_radiology(), DataFrame, sanitize_radiology_entries()

### Community 30 - "Module Cluster 30"
Cohesion: 0.40
Nodes (4): DiagnosticReport, generate_radiology_report_resource(), DiagnosticReport, Generates a DiagnosticReport FHIR resource from a radiology report.

### Community 31 - "Module Cluster 31"
Cohesion: 0.67
Nodes (3): MicroBiologyValue, Enum, str

## Knowledge Gaps
- **15 isolated node(s):** `Config`, `Config`, `hospitalagent-src`, `MIRA Medical Agent Flow Analysis`, `System Architecture Analysis Report` (+10 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MedicationRequestFHIR` connect `FHIR Request Handlers` to `Medical Enums`?**
  _High betweenness centrality (0.002) - this node is a cross-community bridge._
- **Why does `FHIRResourceHandler` connect `FHIR Request Handlers` to `FHIR Resources`, `FHIR Implementation`?**
  _High betweenness centrality (0.001) - this node is a cross-community bridge._
- **Why does `Qdrant_Collection` connect `FHIR Request Handlers` to `Module Cluster 18`?**
  _High betweenness centrality (0.001) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `FHIRResourceHandler` (e.g. with `Qdrant_Collection` and `LabRequestFHIR`) actually correct?**
  _`FHIRResourceHandler` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `extract_data()` (e.g. with `fill_missing_hadm_ids()` and `extract_diagnosis_from_discharge()`) actually correct?**
  _`extract_data()` has 18 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Imaging modalities including external like CT and MRI and internal like ERCP.`, `Venous = Lower extremity veins`, `Un-uncomment if you want to generate the enums and code maps. However, these are` to the rest of the system?**
  _248 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `FHIR Request Handlers` be split into smaller, more focused modules?**
  _Cohesion score 0.057236842105263155 - nodes in this community are weakly interconnected._