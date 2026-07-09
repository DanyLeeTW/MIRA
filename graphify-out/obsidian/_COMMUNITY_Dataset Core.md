---
type: community
cohesion: 0.06
members: 44
---

# Dataset Core

**Cohesion:** 0.06 - loosely connected
**Members:** 44 nodes

## Members
- [[.__getitem__()]] - code - src/dataset/mimic_dataset.py
- [[.__init__()]] - code - src/dataset/mimic_dataset.py
- [[.__init__()_2]] - code - src/evaluations/preprocess.py
- [[.__iter__()]] - code - src/dataset/mimic_dataset.py
- [[.__len__()]] - code - src/dataset/mimic_dataset.py
- [[.__next__()]] - code - src/dataset/mimic_dataset.py
- [[.__repr__()]] - code - src/dataset/mimic_dataset.py
- [[.__str__()]] - code - src/dataset/mimic_dataset.py
- [[.__str__()_3]] - code - src/evaluations/preprocess.py
- [[.fetch_admission_medication_results_gt()]] - code - src/evaluations/preprocess.py
- [[.fetch_diagnosis_gt()]] - code - src/evaluations/preprocess.py
- [[.fetch_hospital_admission_medication_results_gt()]] - code - src/evaluations/preprocess.py
- [[.fetch_lab_results_gt()]] - code - src/evaluations/preprocess.py
- [[.fetch_microbiology_results_gt()]] - code - src/evaluations/preprocess.py
- [[.fetch_pe_results_gt()]] - code - src/evaluations/preprocess.py
- [[.fetch_procedure_results_gt()]] - code - src/evaluations/preprocess.py
- [[.fetch_radiology_results_gt()]] - code - src/evaluations/preprocess.py
- [[.list_tables()]] - code - src/dataset/mimic_dataset.py
- [[.load_dataset()]] - code - src/dataset/mimic_dataset.py
- [[.save_dataset()]] - code - src/dataset/mimic_dataset.py
- [[.save_dataset_csv()]] - code - src/dataset/mimic_dataset.py
- [[.save_dataset_excel()]] - code - src/dataset/mimic_dataset.py
- [[A class that contains the ground truth for a patient.]] - rationale - src/evaluations/preprocess.py
- [[BaseModel_1]] - code
- [[Class to hold data for a MIMIC dataset filtered for a specific diagnosis.      T]] - rationale - src/dataset/mimic_dataset.py
- [[Class to hold data for a single MIMIC hospital admission.      This class repres]] - rationale - src/dataset/mimic_dataset.py
- [[Config_1]] - code - src/dataset/mimic_dataset.py
- [[Load the dataset from a metadata.json and parquet (pd.DataFrame) files]] - rationale - src/dataset/mimic_dataset.py
- [[MIMIC_Dataset]] - code - src/dataset/mimic_dataset.py
- [[MIMIC_Hadm_Dataset]] - code - src/dataset/mimic_dataset.py
- [[PatientGroundTruth]] - code - src/evaluations/preprocess.py
- [[Remove the hadm_ids attribute from the dataset]] - rationale - src/dataset/mimic_dataset.py
- [[Return medication results from the medication table, that were prescribed]] - rationale - src/evaluations/preprocess.py
- [[Return medication that the patient was taking when coming to the hospital.]] - rationale - src/evaluations/preprocess.py
- [[Return physical examination results from the discharge letter.]] - rationale - src/evaluations/preprocess.py
- [[Returns a list of dictionaries containing the procedure information,         fro]] - rationale - src/evaluations/preprocess.py
- [[Returns the diagnosis for the patient.]] - rationale - src/evaluations/preprocess.py
- [[Returns the microbiology results for all unique (by test_name) microbiology test]] - rationale - src/evaluations/preprocess.py
- [[Returns the results for all unique (by itemid) lab events performed within the f]] - rationale - src/evaluations/preprocess.py
- [[Save the dataset to a metadata.json and csv (pd.DataFrame) files]] - rationale - src/dataset/mimic_dataset.py
- [[Save the dataset to a metadata.json and excel (pd.DataFrame) files]] - rationale - src/dataset/mimic_dataset.py
- [[Save the dataset to a metadata.json and parquet (pd.DataFrame) files]] - rationale - src/dataset/mimic_dataset.py
- [[mimic_dataset.py]] - code - src/dataset/mimic_dataset.py
- [[valid()_1]] - code - src/evaluations/preprocess.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dataset_Core
SORT file.name ASC
```

## Connections to other communities
- 8 edges to [[_COMMUNITY_Evaluation Framework]]
- 3 edges to [[_COMMUNITY_Module Cluster 20]]
- 3 edges to [[_COMMUNITY_Module Cluster 26]]
- 2 edges to [[_COMMUNITY_Module Cluster 16]]
- 1 edge to [[_COMMUNITY_Module Cluster 15]]
- 1 edge to [[_COMMUNITY_Module Cluster 27]]

## Top bridge nodes
- [[mimic_dataset.py]] - degree 9, connects to 1 community