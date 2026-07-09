---
type: community
cohesion: 0.08
members: 40
---

# Lab Data Processing

**Cohesion:** 0.08 - loosely connected
**Members:** 40 nodes

## Members
- [[.__getitem__()_1]] - code - src/dataset/mimic_dataset_admission_experiments.py
- [[.__init__()_1]] - code - src/dataset/mimic_dataset_admission_experiments.py
- [[.__iter__()_1]] - code - src/dataset/mimic_dataset_admission_experiments.py
- [[.__len__()_1]] - code - src/dataset/mimic_dataset_admission_experiments.py
- [[.__next__()_1]] - code - src/dataset/mimic_dataset_admission_experiments.py
- [[.__repr__()_1]] - code - src/dataset/mimic_dataset_admission_experiments.py
- [[.__str__()_1]] - code - src/dataset/mimic_dataset_admission_experiments.py
- [[.list_tables()_1]] - code - src/dataset/mimic_dataset_admission_experiments.py
- [[.load_dataset()_1]] - code - src/dataset/mimic_dataset_admission_experiments.py
- [[.save_dataset()_1]] - code - src/dataset/mimic_dataset_admission_experiments.py
- [[.save_dataset_csv()_1]] - code - src/dataset/mimic_dataset_admission_experiments.py
- [[.save_dataset_excel()_1]] - code - src/dataset/mimic_dataset_admission_experiments.py
- [[BaseModel_2]] - code
- [[Build optional-admission experiment datasets from edited Excel case files.  This]] - rationale - src/dataset/make_admission_datasets.py
- [[Class to hold data for a MIMIC dataset filtered for a specific diagnosis.      T_1]] - rationale - src/dataset/mimic_dataset_admission_experiments.py
- [[Class to hold data for a single MIMIC hospital admission.      This class repres_1]] - rationale - src/dataset/mimic_dataset_admission_experiments.py
- [[Config_2]] - code - src/dataset/mimic_dataset_admission_experiments.py
- [[DataFrame_4]] - code
- [[Load the dataset from a metadata.json and parquet (pd.DataFrame) files_1]] - rationale - src/dataset/mimic_dataset_admission_experiments.py
- [[MIMIC_Dataset_Admission_Experiments]] - code - src/dataset/mimic_dataset_admission_experiments.py
- [[MIMIC_Hadm_Dataset_Admission_Experiments]] - code - src/dataset/mimic_dataset_admission_experiments.py
- [[Path]] - code
- [[Remove the hadm_ids attribute from the dataset_1]] - rationale - src/dataset/mimic_dataset_admission_experiments.py
- [[Save the dataset to a metadata.json and csv (pd.DataFrame) files_1]] - rationale - src/dataset/mimic_dataset_admission_experiments.py
- [[Save the dataset to a metadata.json and excel (pd.DataFrame) files_1]] - rationale - src/dataset/mimic_dataset_admission_experiments.py
- [[Save the dataset to a metadata.json and parquet (pd.DataFrame) files_1]] - rationale - src/dataset/mimic_dataset_admission_experiments.py
- [[add_extracted_rad_events()]] - code - src/dataset/make_admission_datasets.py
- [[check_radiology_modality_region()]] - code - src/dataset/make_admission_datasets.py
- [[concatenate_cases()]] - code - src/dataset/make_admission_datasets.py
- [[labs.py]] - code - src/dataset/labs.py
- [[main()]] - code - src/dataset/make_admission_datasets.py
- [[make_admission_datasets.py]] - code - src/dataset/make_admission_datasets.py
- [[make_dataset()]] - code - src/dataset/make_admission_datasets.py
- [[make_pe_admission_dataset()]] - code - src/dataset/make_admission_datasets.py
- [[make_pneumonia_admission_dataset()]] - code - src/dataset/make_admission_datasets.py
- [[match_lab_events_to_loinc()]] - code - src/dataset/labs.py
- [[mimic_dataset_admission_experiments.py]] - code - src/dataset/mimic_dataset_admission_experiments.py
- [[preprocess_cases()]] - code - src/dataset/make_admission_datasets.py
- [[read_cases_from_excel_dir()]] - code - src/dataset/make_admission_datasets.py
- [[set_patient_key_to_hadm_id()]] - code - src/dataset/make_admission_datasets.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Lab_Data_Processing
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Module Cluster 17]]
- 2 edges to [[_COMMUNITY_Module Cluster 27]]
- 1 edge to [[_COMMUNITY_Module Cluster 15]]
- 1 edge to [[_COMMUNITY_Module Cluster 16]]

## Top bridge nodes
- [[mimic_dataset_admission_experiments.py]] - degree 6, connects to 1 community
- [[labs.py]] - degree 4, connects to 1 community