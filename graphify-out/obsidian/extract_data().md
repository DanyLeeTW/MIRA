---
source_file: "src/dataset/make_dataset.py"
type: "code"
community: "Module Cluster 16"
location: "L263"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Module_Cluster_16
---

# extract_data()

## Connections
- [[.load_dataset()]] - `calls` [EXTRACTED]
- [[Any_1]] - `references` [EXTRACTED]
- [[DataFrame_5]] - `references` [EXTRACTED]
- [[MIMIC_Dataset]] - `calls` [INFERRED]
- [[extract_admisson_medication()]] - `indirect_call` [INFERRED]
- [[extract_diagnosis_from_discharge()]] - `calls` [INFERRED]
- [[extract_history()]] - `indirect_call` [INFERRED]
- [[extract_physical_examination()]] - `indirect_call` [INFERRED]
- [[extract_procedures()]] - `calls` [INFERRED]
- [[fill_missing_hadm_ids()]] - `calls` [INFERRED]
- [[filter_medication()]] - `calls` [INFERRED]
- [[match_lab_events_to_loinc()]] - `calls` [INFERRED]
- [[parse_microbiology()]] - `calls` [INFERRED]
- [[process_radiology()]] - `calls` [INFERRED]
- [[sanitize_hadm_texts()]] - `calls` [INFERRED]
- [[sanitize_radiology_entries()]] - `calls` [INFERRED]
- [[validate_diagnoses_ed()]] - `calls` [INFERRED]
- [[validate_diagnoses_icd()]] - `calls` [INFERRED]
- [[validate_discharge_text()]] - `calls` [INFERRED]
- [[validate_lab_events()]] - `calls` [INFERRED]
- [[validate_radiology_events()]] - `calls` [INFERRED]

#graphify/code #graphify/INFERRED #community/Module_Cluster_16