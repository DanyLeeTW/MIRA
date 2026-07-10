## ADDED Requirements

### Requirement: DSPy-structured workup program
The system SHALL provide a `dspy.Module` (`MiraDoctorProgram`) that, given a chief complaint, prior history, and a tool catalog, produces a diagnostic workup trajectory (ordered labs/imaging/procedures/microbiology) and a final diagnosis, independent of and without modifying the existing `src/` implementation.

#### Scenario: Running the program on a MIMIC admission
- **GIVEN** a chief complaint and history string derived from a MIMIC admission
- **WHEN** `MiraDoctorProgram.forward(chief_complaint, history_so_far, tool_catalog_desc)` is invoked
- **THEN** it returns a `dspy.Prediction` containing a `diagnosis`, a `trajectory` of tool calls, and the intermediate `plan`

#### Scenario: src/ behavior is unaffected
- **GIVEN** the new `mira_dspy/` package is installed alongside `src/`
- **WHEN** any existing `src/runs/*.py` entrypoint is executed
- **THEN** its behavior and output are identical to before this change was added

### Requirement: Composite workup metric
The system SHALL compute a single scalar metric combining diagnosis accuracy and test-ordering accuracy, suitable for use as a DSPy optimizer objective.

#### Scenario: Scoring a completed trajectory against ground truth
- **GIVEN** a completed `MiraDoctorProgram` trajectory and the corresponding `PatientGroundTruth` for an admission
- **WHEN** `mira_metric(gold, pred)` is computed
- **THEN** it returns a float in `[0, 1]` equal to `0.5 * diagnosis_score + 0.5 * order_score`, where `order_score` is the macro-average of plain (beta=1) F1 across the lab/urine/radiology/procedure/microbiology categories

#### Scenario: Per-category feedback for reflective optimizers
- **GIVEN** the same completed trajectory and ground truth
- **WHEN** `feedback_text(category, gt_and_assistant, gt_only, assistant_only)` is generated for a category
- **THEN** it returns a natural-language description of any missed or unnecessary orders in that category, suitable as GEPA per-predictor feedback

### Requirement: GEPA-based compilation
The system SHALL support compiling `MiraDoctorProgram` with `dspy.GEPA` against the composite workup metric, targeting the `glm-5.2` model for both the task and optimizer/teacher roles.

#### Scenario: Compiling against a MIMIC-derived trainset
- **GIVEN** a trainset of `dspy.Example` built from `src.evaluations.preprocess.PatientGroundTruth`
- **WHEN** `dspy.GEPA(metric=mira_metric).compile(MiraDoctorProgram(...), trainset=trainset)` is run
- **THEN** an optimized program is produced and persisted under `mira_dspy/compiled/`

### Requirement: Frozen patient simulator
The system SHALL treat the existing `PatientAssistant`/`conv.py` history-taking dialogue as a frozen, non-optimized component during compilation, so that only the ordering and diagnosis stages are subject to DSPy optimization.

#### Scenario: Patient dialogue is not a named predictor
- **GIVEN** a compile run of `MiraDoctorProgram`
- **WHEN** the DSPy optimizer inspects the program's named predictors
- **THEN** `PatientAssistant` does not appear among them, and its outputs are treated as external input to `self.plan`/`self.execute`
