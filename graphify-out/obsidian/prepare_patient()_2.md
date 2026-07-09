---
source_file: "src/runs/run_with_sex_bias.py"
type: "code"
community: "Module Cluster 26"
location: "L146"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Module_Cluster_26
---

# prepare_patient()

## Connections
- [[MIMIC_Dataset]] - `references` [EXTRACTED]
- [[MedAssistant]] - `calls` [INFERRED]
- [[PatientAssistant]] - `calls` [INFERRED]
- [[PatientContext]] - `calls` [INFERRED]
- [[PatientHistory]] - `indirect_call` [INFERRED]
- [[generate_patient_resource()_1]] - `calls` [INFERRED]
- [[get_admission_chief_complaint()_2]] - `calls` [EXTRACTED]
- [[get_admission_medication()_2]] - `calls` [EXTRACTED]
- [[post_fhir_resource()]] - `calls` [INFERRED]
- [[setup_org_and_practitioner()]] - `calls` [INFERRED]

#graphify/code #graphify/INFERRED #community/Module_Cluster_26