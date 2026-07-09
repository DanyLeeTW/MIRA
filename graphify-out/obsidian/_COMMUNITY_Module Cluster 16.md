---
type: community
cohesion: 0.17
members: 15
---

# Module Cluster 16

**Cohesion:** 0.17 - loosely connected
**Members:** 15 nodes

## Members
- [[Check if any entry in the discharge_text dataframe is invalid.     Invalid entri]] - rationale - src/dataset/validators.py
- [[Check if any of the final entries in the lab events dataframe are invalid.     I]] - rationale - src/dataset/validators.py
- [[Check if any of the final entries in the radiology events dataframe are invalid.]] - rationale - src/dataset/validators.py
- [[DataFrame_5]] - code
- [[DataFrame_8]] - code
- [[Extract and process data for a specific diagnosis from various MIMIC-IV datafram]] - rationale - src/dataset/make_dataset.py
- [[If the diagnosis is not in the long_title or it is but the seq_num is not 1, the]] - rationale - src/dataset/validators.py
- [[Validates the ED diagnosis dataframe.     An invalid hadm_id is one where the di]] - rationale - src/dataset/validators.py
- [[extract_data()]] - code - src/dataset/make_dataset.py
- [[validate_diagnoses_ed()]] - code - src/dataset/validators.py
- [[validate_diagnoses_icd()]] - code - src/dataset/validators.py
- [[validate_discharge_text()]] - code - src/dataset/validators.py
- [[validate_lab_events()]] - code - src/dataset/validators.py
- [[validate_radiology_events()]] - code - src/dataset/validators.py
- [[validators.py]] - code - src/dataset/validators.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Module_Cluster_16
SORT file.name ASC
```

## Connections to other communities
- 5 edges to [[_COMMUNITY_Module Cluster 15]]
- 3 edges to [[_COMMUNITY_Module Cluster 22]]
- 2 edges to [[_COMMUNITY_Module Cluster 28]]
- 2 edges to [[_COMMUNITY_Dataset Core]]
- 2 edges to [[_COMMUNITY_Module Cluster 29]]
- 1 edge to [[_COMMUNITY_Module Cluster 19]]
- 1 edge to [[_COMMUNITY_Lab Data Processing]]
- 1 edge to [[_COMMUNITY_Module Cluster 32]]
- 1 edge to [[_COMMUNITY_Module Cluster 33]]

## Top bridge nodes
- [[extract_data()]] - degree 24, connects to 9 communities