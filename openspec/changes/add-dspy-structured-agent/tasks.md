# Tasks for Add DSPy-structured agent architecture alongside src/

## 1. Scaffolding

- [ ] **1.1** 创建 `dspy/` 包骨架 + `pyproject.toml`（依赖 `hospitalagent-src @ file://../src` + `dspy-ai`）
- [ ] **1.2** 确认 `dspy-ai` 在 `src/` 现有的 Python ≥3.12 环境里能干净安装，无依赖冲突
- [ ] **1.3** Smoke-test `glm-5.2` 的 function-calling 稳定性（parallel tool calls、JSON schema 遵循程度）——在深入投入前先验证 API 层面可靠，见 design.md 第 6 节

## 2. Signatures & Tools

- [ ] **2.1** 在 `dspy/signatures.py` 定义 `PlanDifferentialWorkup`、`ConductWorkup` 两个 Signature
- [ ] **2.2** 在 `dspy/tools.py` 把现有 `tool_execs.py` 函数逐个包成 `dspy.Tool`，复用 `MimicEnums` 类型约束，不重写执行逻辑
- [ ] **2.3** 在 `dspy/program.py` 组装 `MiraDoctorProgram(dspy.Module)`（`self.plan` + `self.execute`）

## 3. Metrics（对应 design.md 第 4 节）

- [ ] **3.1** 实现 `category_f_beta`（plain F1，beta=1）
- [ ] **3.2** 实现 `composite_order_score`（macro-average，覆盖 lab/urine/radiology/procedure/microbiology）
- [ ] **3.3** 实现 `feedback_text` 生成器，供 GEPA per-predictor 反馈使用
- [ ] **3.4** 组装 `mira_metric`（复用现成 `evalaute_diagnosis()` + `composite_order_score`，各占 0.5）

## 4. Trainset & Compilation

- [ ] **4.1** 从 `src.evaluations.preprocess.PatientGroundTruth` 构造 trainset（`dspy.Example` 按 admission 生成）
- [ ] **4.2** 在 `dspy/config.py` 配置 `dspy.LM`（task LM + optimizer/teacher LM 均为 `glm-5.2`）
- [ ] **4.3** 实现问诊噪声的 mitigation 策略（钉死 `PatientAssistant` 的 temperature/seed，或多次 rollout 平均——二选一，见 design.md 第 1 节）
- [ ] **4.4** 用 `dspy.GEPA` 对 `MiraDoctorProgram` 跑 `compile()`，metric 用 `mira_metric`
- [ ] **4.5** 编译产物存入 `dspy/compiled/`

## 5. Entrypoint & Known Limitations

- [ ] **5.1** 编写 `dspy/runs/compile_and_run.py`，用 `variant` 参数统一处理 baseline/bias/optional-admission，不复制 `src/runs/*.py` 的三份重复
- [ ] **5.2** 在代码注释或 README 里记录 `procedure` 类目 exact-match 的已知局限（同义表述可能误判不匹配，修复方案已知但本次不做）

## 6. Validation

- [ ] **6.1** 用编译后的 program 跑一批 held-out MIMIC admissions，对比优化前后的 `mira_metric` 分数
- [ ] **6.2** Code review

