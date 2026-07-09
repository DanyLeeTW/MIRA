---
type: community
cohesion: 0.06
members: 55
---

# Agent Architecture Docs

**Cohesion:** 0.06 - loosely connected
**Members:** 55 nodes

## Members
- [[Async Architecture Pattern]] - rationale - docs/系統架構分析報告.md
- [[CloseCase Tool]] - concept - docs/MIRA醫療代理流程解析.md
- [[Dataset Preparation Module]] - document - src/dataset/README.md
- [[Diagnosis Dataset]] - concept - src/dataset/README.md
- [[Evaluation Pipeline]] - document - src/evaluations/README.md
- [[FHIR Backend Integration]] - document - src/backend/README.md
- [[FHIR R4 Standard]] - concept - docs/系統架構分析報告.md
- [[Finish Tool]] - concept - docs/MIRA醫療代理流程解析.md
- [[GPT-4o Model]] - concept - docs/MIRA醫療代理流程解析.md
- [[HAPI FHIR Server]] - concept - docs/系統架構分析報告.md
- [[HAPI FHIR Server Docker Compose]] - code - src/backend/hapi-fhir-server/docker-compose.yml
- [[HospitalAgent src Module]] - document - src/README.md
- [[LabRequestList Tool]] - concept - docs/MIRA醫療代理流程解析.md
- [[MIMIC Enums]] - document - src/MimicEnums/README.md
- [[MIMIC-IV Dataset]] - concept - docs/系統架構分析報告.md
- [[MIRA - Towards Autonomous Medical AI Agents]] - document - README.md
- [[MedAssistant Medical Decision Agent]] - concept - docs/MIRA醫療代理流程解析.md
- [[Medication Code Mapper]] - document - src/codes/README.md
- [[Medication Code Mapping (NDCRxNormSNOMEDATC)]] - concept - src/codes/README.md
- [[MedicationRequestFHIR Tool]] - concept - docs/MIRA醫療代理流程解析.md
- [[OpenAI API Integration]] - concept - docs/系統架構分析報告.md
- [[P0 Risk Hardcoded Configuration]] - concept - docs/系統架構分析報告.md
- [[P0 Risk Missing Error Recovery]] - concept - docs/系統架構分析報告.md
- [[P1 Risk Insufficient Test Coverage]] - concept - docs/系統架構分析報告.md
- [[P2 Risk Notebook Mixed Logic]] - concept - docs/系統架構分析報告.md
- [[PatientAssistant Patient Simulation Agent]] - concept - docs/MIRA醫療代理流程解析.md
- [[PatientContext Data Structure]] - concept - docs/MIRA醫療代理流程解析.md
- [[Phase 1 History Taking]] - concept - docs/MIRA醫療代理流程解析.md
- [[Phase 2 Diagnostic Planning and Execution]] - concept - docs/MIRA醫療代理流程解析.md
- [[Phase 3 Treatment Decision]] - concept - docs/MIRA醫療代理流程解析.md
- [[Phase 4 Case Closure]] - concept - docs/MIRA醫療代理流程解析.md
- [[PhysicalExamination Tool]] - concept - docs/MIRA醫療代理流程解析.md
- [[Plan Tool - Core Decision Engine]] - concept - docs/MIRA醫療代理流程解析.md
- [[ProcedureRequestFHIR Tool]] - concept - docs/MIRA醫療代理流程解析.md
- [[ProcedureSearch Tool]] - concept - docs/MIRA醫療代理流程解析.md
- [[Pydantic Type Safety Pattern]] - rationale - docs/系統架構分析報告.md
- [[Qdrant Vector Database]] - concept - docs/系統架構分析報告.md
- [[RadiologyRequestFHIR Tool]] - concept - docs/MIRA醫療代理流程解析.md
- [[Raw Data Layout]] - document - src/raw/README.md
- [[Run Entrypoints]] - document - src/runs/README.md
- [[Separation of Concerns Architecture]] - rationale - docs/系統架構分析報告.md
- [[Stable Resources]] - document - src/resources/README.md
- [[Tool Registration Pattern]] - rationale - docs/系統架構分析報告.md
- [[Utility Notebooks]] - document - src/notebooks/README.md
- [[assistants.py AI Agent Implementation]] - concept - docs/系統架構分析報告.md
- [[code_maps.py MIMIC Code Mapping]] - concept - docs/系統架構分析報告.md
- [[config.py Global Configuration]] - concept - docs/系統架構分析報告.md
- [[fhir_handlers.py FHIR Handlers]] - concept - docs/系統架構分析報告.md
- [[fhir_observations.py Observation Resources]] - concept - docs/系統架構分析報告.md
- [[mimic_to_fhir.py Data Conversion]] - concept - docs/系統架構分析報告.md
- [[o1 Chain-of-Thought Reasoning Model]] - concept - docs/MIRA醫療代理流程解析.md
- [[routines.py Routine Prompts]] - concept - docs/系統架構分析報告.md
- [[run.py Simulation Runner]] - concept - docs/系統架構分析報告.md
- [[tool_execs.py Tool Executor]] - concept - docs/系統架構分析報告.md
- [[tools.py FHIR Request Models]] - concept - docs/系統架構分析報告.md

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Agent_Architecture_Docs
SORT file.name ASC
```
