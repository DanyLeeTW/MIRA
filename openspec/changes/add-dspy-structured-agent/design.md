# Design: Add DSPy-structured agent architecture alongside src/

## 现状架构（参照实现，src/ 保持不动）

- 无任何 agent 框架：纯 `openai` SDK (`==1.44.1`) + `pydantic`。DSPy/LangChain/Instructor 在仓库里零依赖（repo-wide grep 确认），本方案是 greenfield 引入。
- `assistants.py` (524 行)：`PatientAssistant`（persona LM，无 tools）+ `MedAssistant`（手写 ReAct 风格 tool-calling 循环，`chat()` 方法 `max_steps=20` 强制收尾，`assistants.py:212-374`）。
- `tools.py` (1170 行)：`LabRequestFHIR`/`MedicationRequestFHIR`/`RadiologyRequestFHIR`/`ProcedureRequestFHIR` 等 Pydantic tool models，经 `openai.pydantic_function_tool()` 转成 tool schema；`func_name_to_func` 字典手写 dispatch 到 `tool_execs.py`。
- `MimicEnums/`：`BloodValue`/`UrineValue`/`MicroBiologyValue`/`RadiologyModalityValue`/`RadiologyRegionValue`/`RouteUnit`/`PeriodUnit`，均为 `str, Enum`，作为 closed-vocabulary 约束（JSON-schema `enum`）。
- `routines.py`：`PATIENT_SYSTEM_PROMPT`/`MEDICAL_SYSTEM_PROMPT`/`ROUTINE_PROMPT` 等 f-string 大 prompt；`generate_routine()`（`tool_execs.py:754-767`）是 schema-free 的 freeform planning LLM 调用，触发于空参数的 `Plan` tool。
- `conv.py:38-95`：`run_simulation()`，doctor↔patient 手写 ping-pong 循环，通过 `call_chat()` 交替调用双方，共享一份 message transcript。
- `evaluations/objectives.py`：`evalaute_diagnosis()` 是现成的 boolean LLM-judge metric（`gpt-4o` + `.parse()` structured output）；`evaluate_blood_requests`/`urine_requests`/`radiology_requests`/`procedure_requests`/`microbiology_requests` 只产出 set-overlap dicts（`gt_and_assistant`/`gt_only`/`assistant_only`），没有 reduce 成 scalar 的函数。
- 三个 `runs/*.py` 入口文件（`run.py`/`run_with_sex_bias.py`/`run_optional_admission.py`）85-90% 重复，与本次改造无关的独立清理机会。
- `config.py`：`MEDICAL_ASSISTANT_MODEL`/`PATIENT_ASSISTANT_MODEL`/`REASONING_MODEL` 均为 `"glm-5.2"`（通过 `OPENAI_BASE_URL` 覆写指向 OpenAI-compatible endpoint）；原论文用 `gpt-4o`/`gpt-4o`/`o1`。

## 架构对比

```
现状（src/，保持不动）：

PatientAssistant.chat_completion()   — persona LM，无 tools
        │
        ▼
MedAssistant.chat()  ──while 循环──▶ chat_completion(tools=[...])
   │                                        │
   │ 遇到 Plan tool call                     ▼
   ▼                              execute_tool_calls() → tool_execs.py
generate_routine()                          │
 (schema-free 调用，                          ▼
  ROUTINE_PROMPT f-string)          FHIR backend (labs/imaging/meds/procedures)


新增（dspy/，本次改造范围）：

conv.py 的 ping-pong（冻结，不参与优化，原样复用）
        │ 产出完整问诊 transcript
        ▼
MiraDoctorProgram.forward(chief_complaint, history_so_far, tool_catalog_desc)
   │
   ├── self.plan = dspy.ChainOfThought(PlanDifferentialWorkup)   # 取代 generate_routine()
   │
   └── self.execute = dspy.ReAct(ConductWorkup, tools=all_tools) # 取代 MedAssistant.chat()
              │
              ▼
      dspy.Tool 薄封装 → tool_execs.py（原样复用，不重写）
```

## 关键设计决策

### 1. Two-agent 环境 = noisy-metric 问题，不是结构性障碍

DSPy optimizer 只在 `Example` / `Prediction` / `trace` 边界工作；`PatientAssistant` 只要不包成 `dspy.Predict`，对 optimizer 就是不可见的"环境噪声"，与调用一个不稳定的外部 API 是同一类问题。Noise 集中在 `conv.py` 的问诊对话部分；lab/imaging ordering 走 FHIR/MIMIC backend，相对更 deterministic。

查过 DSPy 官方文档（context7 / dspy.ai），没有找到"optimizer 针对另一个独立采样 LM 作为环境"这种场景的现成案例——这对 MIRA 是真正的新领域，实现阶段需要实测验证，不能假设套用现成模式一定有效。

**Mitigation（实现阶段二选一或结合）**：
1. 编译期把 `PatientAssistant` 的 temperature/seed 钉死，牺牲一些真实感换稳定的优化信号；
2. 接受噪声、靠多次 rollout 平均，复用现有 `ThreadPoolExecutor` 并行基建。

### 2. Optimizer 选型：`dspy.GEPA`

Rollout 很贵（每次是完整多轮 simulation）+ diagnosis metric 偏 sparse（boolean）的组合下，GEPA 的 per-predictor 文本反馈（`pred_name`/`pred_trace`）比 MIPROv2/BootstrapFewShot 的纯 scalar 反馈，能从每次昂贵 rollout 里榨出更多学习信号；GEPA 也能对 `MiraDoctorProgram` 里 `self.plan`/`self.execute` 两个 sub-predictor 给出有区分度的反馈，不需要手动拆成两次独立 compile。

### 3. 问诊范围：只做 (b)，不做 (a)

**(a) ask_patient 作为 ReAct tool** vs **(b) conv.py 冻结、ReAct 只管开单+诊断** —— 选 (b)。

(a) 需要把 `PatientAssistant` 包成带 running message history 的 stateful closure（现在的 `chat_completion` 是无状态的 persona 调用，真正的多轮状态由 `conv.py` 的外层循环维护），架构改动更大；且"问了什么"到"诊断对不对"的 credit assignment 链条比"开对了什么单"长得多、噪得多，会稀释掉本来干净的 ordering 信号；`ReAct` 的 `max_iters=20` budget 也要重新在问诊和开单两类动作之间分配，跟现在两层循环分开算 budget 不一样。

(b) 直接复用现有 metric 基建，rollout cost 更 bounded，且不挡住以后把 (a) 作为独立 phase 补上。

### 4. Metric 设计（`dspy/metrics.py`）

```python
def category_f_beta(gt_and_assistant, gt_only, assistant_only, beta=1.0):
    tp, fn, fp = len(gt_and_assistant), len(gt_only), len(assistant_only)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    if precision + recall == 0:
        return 0.0
    b2 = beta ** 2
    return (1 + b2) * precision * recall / (b2 * precision + recall)

def composite_order_score(ground_truth, trajectory, beta=1.0):
    categories = ["lab", "urine", "radiology", "procedure", "microbiology"]
    scores = {cat: category_f_beta(*match_category(ground_truth, trajectory, cat), beta=beta)
              for cat in categories}
    return sum(scores.values()) / len(scores)   # macro-average，不用 micro

def feedback_text(category, gt_and_assistant, gt_only, assistant_only):
    lines = []
    if gt_only:
        lines.append(f"Missed {category}: {', '.join(gt_only)} were in the actual workup but never ordered.")
    if assistant_only:
        lines.append(f"Unnecessary {category}: {', '.join(assistant_only)} were ordered but not part of the documented workup.")
    return " ".join(lines) or f"{category} ordering matched the documented workup exactly."

def mira_metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
    diag_score = evalaute_diagnosis(gold.ground_truth, pred.diagnosis)       # 复用现成 LLM-judge
    order_score = composite_order_score(gold.ground_truth, pred.trajectory)  # 上面两个函数
    return 0.5 * diag_score + 0.5 * order_score
```

决策：**plain F1（beta=1）+ macro-average + diagnosis/order 各 0.5**，全部先用最简单的默认值，等 pipeline 跑通有真实数据后再调——不在验证基本 loop 之前过度设计 metric。`procedure` 类目的 exact-match 局限性（同义表述判不匹配）有意保留，见 proposal.md 的 Known Limitations。

### 5. `dspy/` 目录结构

`src/` 是独立可安装包（`hospitalagent-src`，见 `src/pyproject.toml`，`uv pip install -e ./src`）——`dspy/` 同样做成独立包，通过 editable/path dependency 依赖它，而不是 `sys.path` hack。

```
dspy/
├── pyproject.toml          # dependencies = ["hospitalagent-src @ file://../src", "dspy-ai", ...]
├── signatures.py           # PlanDifferentialWorkup, ConductWorkup
├── tools.py                # dspy.Tool 薄封装，import src.tool_execs.*，不重新实现
├── program.py              # MiraDoctorProgram（composite Module）
├── metrics.py              # category_f_beta / composite_order_score / feedback_text / mira_metric
├── config.py               # DSPy 侧 LM 配置（glm-5.2，见下）
├── compiled/               # dspy 编译产物（.save() 输出、优化日志）——类比 src/raw/ 但完全分开
└── runs/
    └── compile_and_run.py  # 入口：从 src.evaluations.preprocess 建 trainset，GEPA compile，跑 evaluate
```

- `metrics.py` 放 `dspy/` 而不是 `src/evaluations/`：保持"`src/` 完全不动"，内部 import `src.evaluations.objectives` 的 matching 逻辑，只加 reduce-to-scalar 这一层。
- `runs/compile_and_run.py` 用 `variant` 参数/config object 统一处理 bias-injection 和 optional-admission 开关，不重蹈 `src/runs/*.py` 三份 85-90% 重复的覆辙（具体参数化设计留到实现阶段）。

### 6. 模型选型（`dspy/config.py`）

Task LM 和 optimizer/teacher LM 都用 `glm-5.2`（`dspy.LM` 走 LiteLLM，`"provider/model"` 格式 + 自定义 `api_base`，跟现在 `assistants.py` 用 `OPENAI_BASE_URL` 覆写是同一类机制，接 GLM 无技术障碍）。不引入第二个更强的 teacher 模型，不追求跟论文原始 `gpt-4o`/`o1` 数字可比——这是独立实验，衡量优化前后的提升。

实现阶段需要先做的验证：ReAct + enum-constrained Signature 依赖可靠的 tool-calling，MIPROv2/GEPA 能优化 prompt 措辞，治不好模型在 API 层面就吐畸形 tool-call JSON 的问题——动手前 smoke-test 一下 `glm-5.2` 的 function-calling 稳定性（parallel calls、JSON schema 遵循程度）。
