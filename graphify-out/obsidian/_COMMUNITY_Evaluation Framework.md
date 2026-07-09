---
type: community
cohesion: 0.07
members: 50
---

# Evaluation Framework

**Cohesion:** 0.07 - loosely connected
**Members:** 50 nodes

## Members
- [[.__str__()_2]] - code - src/evaluations/objectives.py
- [[A class to store the evaluation results for each objective.]] - rationale - src/evaluations/objectives.py
- [[Evaluate a single assistant output file against the ground truth and write the e]] - rationale - src/evaluations/evaluate.py
- [[Evaluates all objectives.     Args         client The OpenAI client.         d]] - rationale - src/evaluations/objectives.py
- [[Evaluates the diagnosis objective.     Args         client The OpenAI client.]] - rationale - src/evaluations/objectives.py
- [[Evaluates the diagnosis.]] - rationale - src/evaluations/objectives.py
- [[Evaluates the lab requests.     Current implementation     - Check the overlap]] - rationale - src/evaluations/objectives.py
- [[Evaluates the microbiology requests.     Current implementation     - Check the]] - rationale - src/evaluations/objectives.py
- [[Evaluates the physical examination request.     Current implementation     - Ch]] - rationale - src/evaluations/objectives.py
- [[Evaluates the procedure requests.     Current implementation     - Check the ov]] - rationale - src/evaluations/objectives.py
- [[Evaluates the radiology requests.     Current implementation     - Check the ov]] - rationale - src/evaluations/objectives.py
- [[Evaluates the urine requests.     Current implementation     - Check the overla]] - rationale - src/evaluations/objectives.py
- [[Evaluation]] - code - src/evaluations/objectives.py
- [[Extracts the tool use from the medical assistant outputs into structured format]] - rationale - src/evaluations/preprocess.py
- [[Flattens the tool arguments with edge case handling for different tools.]] - rationale - src/evaluations/preprocess.py
- [[Loads a single result from a jsonl file and returns the medical assistant output]] - rationale - src/evaluations/preprocess.py
- [[Main function to evaluate assistant outputs for a given diagnosis.]] - rationale - src/evaluations/evaluate.py
- [[Matches the ground truth to the assistant's tool calls.]] - rationale - src/evaluations/preprocess.py
- [[Measures the overlap between the ground truth and the assistant's data.]] - rationale - src/evaluations/objectives.py
- [[Merge the requests if tools were called multiple times,     to facilitate evalua]] - rationale - src/evaluations/preprocess.py
- [[OpenAI]] - code
- [[OpenAI_1]] - code
- [[Path_1]] - code
- [[Reads a single jsonl file and returns the first (and only) entry.]] - rationale - src/evaluations/preprocess.py
- [[Recursively get all .jsonl file paths under the given base path.      Args]] - rationale - src/evaluations/evaluate.py
- [[Use an LLM call to evaluate the medication requests.]] - rationale - src/evaluations/objectives.py
- [[_flatten_tool_args()]] - code - src/evaluations/preprocess.py
- [[evalaute_diagnosis()]] - code - src/evaluations/objectives.py
- [[evaluate.py]] - code - src/evaluations/evaluate.py
- [[evaluate_all_objectives()]] - code - src/evaluations/objectives.py
- [[evaluate_blood_requests()]] - code - src/evaluations/objectives.py
- [[evaluate_diagnosis_objective()]] - code - src/evaluations/objectives.py
- [[evaluate_medication_objective()]] - code - src/evaluations/objectives.py
- [[evaluate_medication_requests()]] - code - src/evaluations/objectives.py
- [[evaluate_microbiology_requests()]] - code - src/evaluations/objectives.py
- [[evaluate_one_file()]] - code - src/evaluations/evaluate.py
- [[evaluate_pe_request()]] - code - src/evaluations/objectives.py
- [[evaluate_procedure_requests()]] - code - src/evaluations/objectives.py
- [[evaluate_radiology_requests()]] - code - src/evaluations/objectives.py
- [[evaluate_urine_requests()]] - code - src/evaluations/objectives.py
- [[extract_tool_use()]] - code - src/evaluations/preprocess.py
- [[get_file_paths()]] - code - src/evaluations/evaluate.py
- [[load_one_result()]] - code - src/evaluations/preprocess.py
- [[main()_2]] - code - src/evaluations/evaluate.py
- [[match_ground_truth_and_assistant()]] - code - src/evaluations/preprocess.py
- [[measure_overlap()]] - code - src/evaluations/objectives.py
- [[merge_called_args()]] - code - src/evaluations/preprocess.py
- [[objectives.py]] - code - src/evaluations/objectives.py
- [[preprocess.py]] - code - src/evaluations/preprocess.py
- [[read_single_jsonl()]] - code - src/evaluations/preprocess.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Evaluation_Framework
SORT file.name ASC
```

## Connections to other communities
- 8 edges to [[_COMMUNITY_Dataset Core]]
- 1 edge to [[_COMMUNITY_Module Cluster 27]]

## Top bridge nodes
- [[evaluate.py]] - degree 8, connects to 2 communities
- [[evaluate_one_file()]] - degree 12, connects to 1 community
- [[preprocess.py]] - degree 11, connects to 1 community
- [[main()_2]] - degree 7, connects to 1 community
- [[load_one_result()]] - degree 5, connects to 1 community