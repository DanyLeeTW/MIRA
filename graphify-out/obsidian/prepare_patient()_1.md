---
source_file: "src/runs/run_optional_admission.py"
type: "code"
community: "Module Cluster 17"
location: "L195"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Module_Cluster_17
---

# prepare_patient()

## Connections
- [[MIMIC_Dataset_Admission_Experiments]] - `references` [EXTRACTED]
- [[MedAssistant]] - `calls` [INFERRED]
- [[PatientAssistant]] - `calls` [INFERRED]
- [[PatientContext]] - `calls` [INFERRED]
- [[PatientHistory]] - `indirect_call` [INFERRED]
- [[generate_patient_resource()_1]] - `calls` [EXTRACTED]
- [[get_admission_chief_complaint()_1]] - `calls` [EXTRACTED]
- [[get_admission_medication()_1]] - `calls` [EXTRACTED]
- [[post_fhir_resource()]] - `calls` [INFERRED]
- [[setup_org_and_practitioner()]] - `calls` [INFERRED]

#graphify/code #graphify/INFERRED #community/Module_Cluster_17