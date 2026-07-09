---
type: community
cohesion: 0.10
members: 35
---

# Tool Execution

**Cohesion:** 0.10 - loosely connected
**Members:** 35 nodes

## Members
- [[Closes the patient case by sending the patient to the in-hospital admission depa]] - rationale - src/tool_execs.py
- [[Connect to a Qdrant collection]] - rationale - src/tool_execs.py
- [[DataFrame_12]] - code
- [[Finishes the patient case by sending the patient to the in-hospital admission de]] - rationale - src/tool_execs.py
- [[Generates a routine for a patient based on the provided tools and patient inform]] - rationale - src/tool_execs.py
- [[Generates a routine for a patient based on the provided tools and patient inform_1]] - rationale - src/tool_execs.py
- [[Lookup available information about the patient history from previous visits or f]] - rationale - src/tool_execs.py
- [[Processes microbiology requests for a patient.      Args         patient_id (st]] - rationale - src/tool_execs.py
- [[Processes multiple blood value requests for a patient.      Args         patien]] - rationale - src/tool_execs.py
- [[Processes multiple blood value requests for a patient.      Args         patien_1]] - rationale - src/tool_execs.py
- [[Processes multiple medication requests for a patient.      Args         patient]] - rationale - src/tool_execs.py
- [[Processes physical examination requests for a patient.      Args         patien]] - rationale - src/tool_execs.py
- [[Processes physical examination requests for a patient.      Args         patien_1]] - rationale - src/tool_execs.py
- [[Processes procedure requests for a patient.      Returns         str Concatena]] - rationale - src/tool_execs.py
- [[Processes procedure requests for a patient.      Returns         str Concatena_1]] - rationale - src/tool_execs.py
- [[Processes radiology requests for a patient.      Args         patient_id (str)]] - rationale - src/tool_execs.py
- [[QdrantClient]] - code
- [[Session_1]] - code
- [[close_case()]] - code - src/tool_execs.py
- [[connect_qdrant()]] - code - src/tool_execs.py
- [[finish()]] - code - src/tool_execs.py
- [[generate_routine()]] - code - src/tool_execs.py
- [[generate_routine_optional_admission()]] - code - src/tool_execs.py
- [[get_blood_value_results()]] - code - src/tool_execs.py
- [[get_medication_results()]] - code - src/tool_execs.py
- [[get_microbiology_results()]] - code - src/tool_execs.py
- [[get_physical_exam_results()]] - code - src/tool_execs.py
- [[get_procedure_request_results()]] - code - src/tool_execs.py
- [[get_procedure_search_results()]] - code - src/tool_execs.py
- [[get_radiology_results()]] - code - src/tool_execs.py
- [[get_urine_value_results()]] - code - src/tool_execs.py
- [[get_vitalsign_results()]] - code - src/tool_execs.py
- [[patient_history()]] - code - src/tool_execs.py
- [[request_fetch_and_poll()]] - code - src/tool_execs.py
- [[tool_execs.py]] - code - src/tool_execs.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tool_Execution
SORT file.name ASC
```

## Connections to other communities
- 22 edges to [[_COMMUNITY_FHIR Request Handlers]]
- 2 edges to [[_COMMUNITY_Module Cluster 18]]
- 2 edges to [[_COMMUNITY_FHIR Backend]]
- 2 edges to [[_COMMUNITY_Medical Enums]]
- 1 edge to [[_COMMUNITY_Module Cluster 20]]
- 1 edge to [[_COMMUNITY_Module Cluster 17]]
- 1 edge to [[_COMMUNITY_Module Cluster 26]]
- 1 edge to [[_COMMUNITY_Module Cluster 27]]

## Top bridge nodes
- [[tool_execs.py]] - degree 25, connects to 4 communities
- [[get_radiology_results()]] - degree 9, connects to 2 communities
- [[request_fetch_and_poll()]] - degree 12, connects to 1 community
- [[get_procedure_search_results()]] - degree 8, connects to 1 community
- [[get_blood_value_results()]] - degree 7, connects to 1 community