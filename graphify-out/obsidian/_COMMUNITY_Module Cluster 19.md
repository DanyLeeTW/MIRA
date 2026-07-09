---
type: community
cohesion: 0.19
members: 13
---

# Module Cluster 19

**Cohesion:** 0.19 - loosely connected
**Members:** 13 nodes

## Members
- [[Add missing hadm_ids if the charttime of lab_events, microbiology, and radiology]] - rationale - src/dataset/data.py
- [[DataFrame_3]] - code
- [[Format Laboratory values into string represntation value unit or flag]] - rationale - src/dataset/formats.py
- [[Format microbiology values into a string represntation bacteria antibiotics RS]] - rationale - src/dataset/formats.py
- [[consort_tracker.py]] - code - src/dataset/consort_tracker.py
- [[data.py]] - code - src/dataset/data.py
- [[fill_missing_hadm_ids()]] - code - src/dataset/data.py
- [[format_lab_value()]] - code - src/dataset/formats.py
- [[format_microbiology_value()]] - code - src/dataset/formats.py
- [[formats.py]] - code - src/dataset/formats.py
- [[read_data()]] - code - src/dataset/data.py
- [[read_ed_data()]] - code - src/dataset/data.py
- [[valid()]] - code - src/dataset/formats.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Module_Cluster_19
SORT file.name ASC
```

## Connections to other communities
- 4 edges to [[_COMMUNITY_Module Cluster 15]]
- 1 edge to [[_COMMUNITY_Code Mapping]]
- 1 edge to [[_COMMUNITY_Dataset Tracking]]
- 1 edge to [[_COMMUNITY_Module Cluster 27]]
- 1 edge to [[_COMMUNITY_Module Cluster 16]]

## Top bridge nodes
- [[data.py]] - degree 8, connects to 1 community
- [[consort_tracker.py]] - degree 3, connects to 1 community