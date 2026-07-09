---
type: community
cohesion: 0.21
members: 13
---

# Module Cluster 20

**Cohesion:** 0.21 - loosely connected
**Members:** 13 nodes

## Members
- [[Handle the case where the admission chief complaint is not available.]] - rationale - src/runs/run.py
- [[Handle the case where the admission medication is not available.]] - rationale - src/runs/run.py
- [[Lookup available information about the patient history from previous visits or f_1]] - rationale - src/tools.py
- [[PatientHistory]] - code - src/tools.py
- [[Prepare a single patient instance with all required resources.      Parameters]] - rationale - src/runs/run.py
- [[Run simulations for patients using the provided dataset and configuration.]] - rationale - src/runs/run.py
- [[Yield a single patient at a time along with the total length.]] - rationale - src/runs/run.py
- [[get_admission_chief_complaint()]] - code - src/runs/run.py
- [[get_admission_medication()]] - code - src/runs/run.py
- [[patient_iterator()]] - code - src/runs/run.py
- [[prepare_patient()]] - code - src/runs/run.py
- [[run.py]] - code - src/runs/run.py
- [[run_simulations()]] - code - src/runs/run.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Module_Cluster_20
SORT file.name ASC
```

## Connections to other communities
- 4 edges to [[_COMMUNITY_FHIR Backend]]
- 3 edges to [[_COMMUNITY_Agent Orchestration]]
- 3 edges to [[_COMMUNITY_Dataset Core]]
- 3 edges to [[_COMMUNITY_FHIR Request Handlers]]
- 2 edges to [[_COMMUNITY_Module Cluster 27]]
- 2 edges to [[_COMMUNITY_Module Cluster 17]]
- 1 edge to [[_COMMUNITY_Tool Execution]]
- 1 edge to [[_COMMUNITY_Visualization Output]]
- 1 edge to [[_COMMUNITY_Module Cluster 24]]
- 1 edge to [[_COMMUNITY_Module Cluster 26]]

## Top bridge nodes
- [[run.py]] - degree 14, connects to 7 communities
- [[prepare_patient()]] - degree 13, connects to 5 communities
- [[PatientHistory]] - degree 6, connects to 1 community
- [[run_simulations()]] - degree 4, connects to 1 community