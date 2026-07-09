---
type: community
cohesion: 0.12
members: 27
---

# Code Mapping

**Cohesion:** 0.12 - loosely connected
**Members:** 27 nodes

## Members
- [[Get LOINC code for a given imaging modality and body region using UMLS API.]] - rationale - src/codes/medication_codes.py
- [[Get NDC codes for a medication name using openFDA API.]] - rationale - src/codes/medication_codes.py
- [[Get RxNorm code for a medication name using RxNav API.]] - rationale - src/codes/medication_codes.py
- [[Get RxNorm code for an NDC code using RxNav API.]] - rationale - src/codes/medication_codes.py
- [[Get SNOMED CT code for a given imaging modality and body region using UMLS API.]] - rationale - src/codes/medication_codes.py
- [[Get SNOMED CT code from an RxNorm code using RxNav API.]] - rationale - src/codes/medication_codes.py
- [[Get SNOMED CT codes from an RxNorm code using UMLS API.]] - rationale - src/codes/medication_codes.py
- [[Get specific ATC code from RxNorm code using UMLS API.]] - rationale - src/codes/medication_codes.py
- [[Inference call for getting medication codes for FHIR drug requests.     Retrieve]] - rationale - src/codes/medication_codes.py
- [[Load the prescriptions.csv and medrecon.csv files and generate unique combinatio]] - rationale - src/codes/medication_codes.py
- [[Obtain a Service Ticket (ST) for each UMLS API call.]] - rationale - src/codes/medication_codes.py
- [[Obtain the Ticket Granting Ticket (TGT) for UMLS authentication.]] - rationale - src/codes/medication_codes.py
- [[get_atc_code_from_umls()]] - code - src/codes/medication_codes.py
- [[get_drug_codes_from_name()]] - code - src/codes/medication_codes.py
- [[get_loinc_code_from_modality_region()]] - code - src/codes/medication_codes.py
- [[get_medication_codes()]] - code - src/codes/medication_codes.py
- [[get_ndc_codes_from_name()]] - code - src/codes/medication_codes.py
- [[get_rxnorm_code_from_name()]] - code - src/codes/medication_codes.py
- [[get_rxnorm_code_from_ndc()]] - code - src/codes/medication_codes.py
- [[get_snomed_code_from_modality_region()]] - code - src/codes/medication_codes.py
- [[get_snomed_code_from_rxnorm()]] - code - src/codes/medication_codes.py
- [[get_snomed_code_from_umls()]] - code - src/codes/medication_codes.py
- [[get_umls_service_ticket()]] - code - src/codes/medication_codes.py
- [[get_umls_tgt()]] - code - src/codes/medication_codes.py
- [[load_medication_data()]] - code - src/codes/medication_codes.py
- [[medication_codes.py]] - code - src/codes/medication_codes.py
- [[process_row()]] - code - src/codes/medication_codes.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Code_Mapping
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_FHIR Backend]]
- 1 edge to [[_COMMUNITY_Module Cluster 19]]
- 1 edge to [[_COMMUNITY_Medical Enums]]

## Top bridge nodes
- [[medication_codes.py]] - degree 16, connects to 2 communities