---
type: community
cohesion: 0.18
members: 15
---

# Module Cluster 17

**Cohesion:** 0.18 - loosely connected
**Members:** 15 nodes

## Members
- [[Generates a Patient FHIR resource from a MIMIC row and associates it with a Prac_1]] - rationale - src/runs/run_optional_admission.py
- [[Handle the case where the admission chief complaint is not available._1]] - rationale - src/runs/run_optional_admission.py
- [[Handle the case where the admission medication is not available._1]] - rationale - src/runs/run_optional_admission.py
- [[Patient_1]] - code
- [[Prepare a single patient instance with all required resources.      Parameters_1]] - rationale - src/runs/run_optional_admission.py
- [[Run simulations for patients using the provided dataset and configuration._1]] - rationale - src/runs/run_optional_admission.py
- [[Series_6]] - code
- [[Yield a single patient at a time along with the total length._1]] - rationale - src/runs/run_optional_admission.py
- [[generate_patient_resource()_1]] - code - src/runs/run_optional_admission.py
- [[get_admission_chief_complaint()_1]] - code - src/runs/run_optional_admission.py
- [[get_admission_medication()_1]] - code - src/runs/run_optional_admission.py
- [[patient_iterator()_1]] - code - src/runs/run_optional_admission.py
- [[prepare_patient()_1]] - code - src/runs/run_optional_admission.py
- [[run_optional_admission.py]] - code - src/runs/run_optional_admission.py
- [[run_simulations()_1]] - code - src/runs/run_optional_admission.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Module_Cluster_17
SORT file.name ASC
```

## Connections to other communities
- 4 edges to [[_COMMUNITY_FHIR Backend]]
- 3 edges to [[_COMMUNITY_Agent Orchestration]]
- 3 edges to [[_COMMUNITY_Lab Data Processing]]
- 2 edges to [[_COMMUNITY_Module Cluster 20]]
- 2 edges to [[_COMMUNITY_Module Cluster 27]]
- 1 edge to [[_COMMUNITY_Tool Execution]]
- 1 edge to [[_COMMUNITY_FHIR Request Handlers]]
- 1 edge to [[_COMMUNITY_Visualization Output]]
- 1 edge to [[_COMMUNITY_Module Cluster 24]]
- 1 edge to [[_COMMUNITY_Module Cluster 26]]

## Top bridge nodes
- [[run_optional_admission.py]] - degree 15, connects to 7 communities
- [[prepare_patient()_1]] - degree 13, connects to 5 communities
- [[run_simulations()_1]] - degree 4, connects to 1 community