# Feature: Add DSPy-structured agent architecture alongside src/

## Summary

在 repo 根目录新增一个独立的 `mira_dspy/` 包，把 MIRA agent 的 tool-calling/prompting 逻辑用 DSPy 的 Signature/Module/ReAct 结构重写一遍，作为跟 `src/`（论文复现参照实现）平行、可独立编译优化的实现。范围限定在"开单 + 诊断"这一段（对应现在 `generate_routine()` + `MedAssistant.chat()`）；问诊环节（`conv.py` 的 doctor↔patient ping-pong）保持冻结，不参与这轮优化。

## Motivation

现在的 `assistants.py`/`tool_execs.py`/`routines.py` 是纯手写的 prompt 字符串（f-string/`.format()`）+ 手写的 ReAct 风格 tool-calling 循环（`assistants.py:212-374`），没有系统化的方式去调整或优化 prompt。DSPy 提供 Signature/Module 抽象和 teleprompter（如 GEPA），可以针对现有的 `evalaute_diagnosis()` 等 metric 自动搜索更好的 instructions/demos，这是当前手写架构做不到的。仓库里目前没有任何 DSPy/LangChain/Instructor 依赖，这是一次 greenfield 引入。

## Proposed Solution

- 新建 `mira_dspy/` 作为独立可安装包，依赖 `hospitalagent-src`（`src/` 现有包名，`uv pip install -e ./src`）+ `dspy-ai`。
- 用 `dspy.Signature` 重写 planning（取代 `generate_routine()`/`ROUTINE_PROMPT`）和 execution（取代 `MedAssistant.chat()`）两个阶段，组合成一个 `MiraDoctorProgram(dspy.Module)`（`self.plan` + `self.execute` 两个 named predictor）。
- 每个现有的 `tool_execs.py` 函数包一层 `dspy.Tool`，复用 `MimicEnums`（`BloodValue`/`UrineValue`/`MicroBiologyValue` 等）作为类型约束，不重写执行逻辑，`func_name_to_func` 的手写 dispatch 由 `dspy.ReAct` 自带的 trajectory 机制取代。
- 新写 `category_f_beta`/`composite_order_score`（plain F1、macro-average）补上现有 evaluation 里缺失的 scalar reduction，跟现成的 `evalaute_diagnosis()` 组合成最终 `mira_metric`。
- 用 `dspy.GEPA` 做 optimizer——相比 MIPROv2/BootstrapFewShot，GEPA 的 per-predictor 文本反馈（`pred_name`/`pred_trace`）更适合"rollout 很贵（每次是完整多轮 simulation）+ diagnosis metric 偏 sparse（boolean）"这种场景。
- Task LM 和 optimizer/teacher LM 都沿用现有的 `glm-5.2`（`config.py` 里的现状），不引入额外模型，也不追求跟论文原始 `gpt-4o`/`o1` 数字可比——这是一次独立实验，衡量的是"这个模型 DSPy 优化前后的提升"。
- `src/` 完全不动，继续作为论文复现的参照实现。

## Alternatives Considered

- **把问诊也折进 ReAct trajectory**（`ask_patient` 作为 stateful tool，取代 `conv.py` 的 ping-pong）：能让优化器同时塑造"问什么"和"开什么单"，更接近真实临床推理的交织方式。但需要把 `PatientAssistant` 包成带 running message history 的 stateful closure，架构改动明显更大；且"问诊质量"到"诊断对不对"的 credit assignment 链条比"开单对不对"长得多、噪得多，会稀释掉本来干净的 ordering 信号；`ReAct` 的 `max_iters=20` budget 也要重新在问诊和开单两类动作之间分配。留作后续可能的 phase 2，不在本次范围内。
- **直接对齐论文原始模型（`gpt-4o`/`o1`）**：会让结果跟论文数字可比，便于验证 DSPy 优化不会改变原始实验结论。但当前决定优先验证 DSPy 本身的价值，不引入模型切换这个额外变量。
- **把 metric reduction 函数放进 `src/evaluations/`**：逻辑上是 `objectives.py` 里 set-overlap dicts 的自然延伸，论文自身的 evaluation notebook 也能顺带受益。但违背"`src/` 保持不动"的原则；改为在 `mira_dspy/metrics.py` 里 import `src/evaluations/objectives.py` 的 matching 逻辑，只加一层 reduce-to-scalar。

## Impact

- [ ] Breaking changes — 无，`src/` 及其现有行为不受影响，纯新增一个平行包
- [ ] Database migrations — 无
- [ ] API changes — 无（新增 `mira_dspy/` 包，不改动任何现有对外接口）

## Known Limitations (有意识保留，非遗漏)

- `procedure` 类目沿用现有的 exact-match set-overlap，`ProcedureRequestFHIR.procedure` 是 free-text 字段，同义表述（如 "Diagnostic laparoscopy" vs "Laparoscopic exploration"）会被判不匹配，可能低估该类目真实 F1。修复方案是复用 `ProcedureSearch` 已有的 `jinaai/jina-embeddings-v3` + Qdrant 做相似度 threshold match，本次不做，后续如发现该类目分数明显不可信可重新评估。
- `src/runs/run.py`/`run_with_sex_bias.py`/`run_optional_admission.py` 85-90% 重复的清理，不在本次范围内（`mira_dspy/runs/compile_and_run.py` 会用参数化设计规避同样的重复，但不回头改 `src/`）。
- DSPy 官方文档目前没有"optimizer 针对另一个独立采样 LM 作为环境"的现成案例（`conv.py` 的 doctor↔patient 交互属于此类）；本方案通过冻结 `PatientAssistant`（不包成 `dspy.Predict`）规避而非解决这个问题，其噪声敏感度需要在实现阶段通过实测验证。
