---
source_file: "docs/MIRA醫療代理流程解析.md"
type: "concept"
community: "Agent Architecture Docs"
tags:
  - graphify/concept
  - graphify/EXTRACTED
  - community/Agent_Architecture_Docs
---

# MedAssistant Medical Decision Agent

## Connections
- [[CloseCase Tool]] - `calls` [EXTRACTED]
- [[Finish Tool]] - `calls` [EXTRACTED]
- [[GPT-4o Model]] - `references` [EXTRACTED]
- [[LabRequestList Tool]] - `calls` [EXTRACTED]
- [[MedicationRequestFHIR Tool]] - `calls` [EXTRACTED]
- [[PatientAssistant Patient Simulation Agent]] - `references` [EXTRACTED]
- [[PhysicalExamination Tool]] - `calls` [EXTRACTED]
- [[Plan Tool - Core Decision Engine]] - `calls` [EXTRACTED]
- [[ProcedureRequestFHIR Tool]] - `calls` [EXTRACTED]
- [[RadiologyRequestFHIR Tool]] - `calls` [EXTRACTED]

#graphify/concept #graphify/EXTRACTED #community/Agent_Architecture_Docs