---
doc_id: feature-breakdown
version: v2.3.0
last_updated: 2026-09-16
constitution_ref: ../../.specify/memory/constitution.md
related_docs:
  - ../top_level_design/workflow.md
  - ../top_level_design/architecture_modules.md
  - ../top_level_design/module_schemas.md
  - review.md
---

# LangAgent Feature 拆解与排序表

> 本文件是 Feature 00（顶层设计）的下游交付物，将 LangAgent 整套系统的实现过程拆解为 13 个 feature。
> 每个 feature 对应 1+ 个 speckit.specify 任务；feature 之间的开发顺序由依赖矩阵拓扑排序确定。
> 本文件的事实来源：`harness/top_level_design/` 三份 artefact + 宪法第 XV 条顶层设计优先。
>
> **v0.5.0 变更**（**review.md v0.1.0 评审修复后**）：
> - log tag 命名空间：v0.4.0 起 `la.lifecycle.*` 取代 v0.3.0 的 `la.cli.*` 命名空间（12 项 rename；review.md v0.4.0 M-NEW-3 修复；**v0.5.0 评审 v0.1.0 §四.C-9 修正措辞**：原文"rename"改为"取代"——v0.4.0 直接用新名，不是真 rename）；详见 §三.6.2 表。
> - 模块清单：19 → **20**（v2.2.2 review.md v0.1.0 P0-1 方案 A' 修复：**新增 `cross_cutting_stage_guard` 模块**；`stage_guard.py` 从 `langagent/runtime/stage_guard.py` 移到 `langagent/cross_cutting/stage_guard.py`；cross_cutting 层 4 → 5；模块总数 19 → 20；F02 / F03 / F05 / F06 / F10 共 5 个 feature 应用 `@cross_cutting_stage_guard_decorator` 装饰器实施 6 阶段能力边界技术保障）。
> - Schema 清单：24 → **25**（v0.4.0 M-NEW-1 修复新增 `EvalRunResult` 类型；v0.5.0 评审 v0.1.0 §二.A.1 修复补建 schema 章节并字段统一 3 字段 `eval_report` / `final_state` / `exit_code`）。
> - 依赖矩阵：19×19 → **20×20**（v2.2.2 review.md v0.1.0 P0-1 修复后新增 cross_cutting_stage_guard 行/列；矩阵 19×19 → 20×20 = **400 单元格**；新增 9 条硬例外单向边：6 条 stage_guard 边（4 个 runtime + 2 个 primitives）+ 1 条 guardrail 边（P0-2）+ 保留原 2 条 logger 边）。
> - **退出码**：12 → **13**（v0.5.0 评审 v0.1.0 §四.C-7 修复新增退出码 67 = `name_already_exists`，从原 66 双语义拆分）。
> - F11 runner 签名：`run(agent_dir, args: dict) -> EvalRunResult(eval_report, final_state, exit_code)`（review.md v0.4.0 M-NEW-1 修复）；原 `args: CliArgs` 违反分层，改为 dict。
> - F06 cleanup 步骤失败 continue-on-failure 策略显式化（review.md v0.4.0 M-NEW-4 修复）：§3.6.1 新增失败处理细则。
>
> **v1.1.0 变更**（**review.md v1.0.0 评审修复后**——本轮 19 项问题全部应用修复；详见 `harness/feature/review.md` §七 changelog v1.1.0）：
> - [P0-1] F01 doctor probe 工厂从 F01 移到 F05 runtime 层（新增 `build_doctor_probes()` API）；恢复 `architecture_modules.md` CLI × primitives 黑名单约束。
>    - [P0-2] 推荐批次表修订：F08 拆 Phase 1（cross_cutting_logger + EventBusProtocol 接口 + ALLOWED_TAGS **45 项**契约）/ Phase 2（metrics_collector）；Phase 1 与 F10 在第 1 批并行；Phase 2 在第 3 批与 F09 并行。
> - [P0-3] F11 依赖列补 F03（`config_resolver.resolve()`）。
> - [P1-1] F01 一句话定位补 stdout/stderr 语义分离 + format_chat_message / format_*_stdout 3 个 stdout API 说明。
> - [P1-2] F02 §3.4 错误引用"宪法第 V 条"修正为"workflow.md §系统视角：6 阶段"。
>    - [P1-3] F08 行增加 **45 项**ALLOWED_TAGS 契约性质说明。
> - [P1-4] architecture_modules.md#mod-primitives-state-reducers 修正为 3 个唯一 reducer 函数。
> - [P2-1] F01 §3.5 新增各子命令退出码表格（4 子命令 × 4-5 场景）。
> - [P2-2] F02 §3.4a monkeypatch 单线程约束强化（pytest-xdist 禁用 / main_thread 断言）。
> - [P2-3] F03 §三.4 默认 `model_provider="openai-compatible"` 与宪法第 IV 条 4 款对齐的注脚。
> - [P2-4] F04 §七 deliverable 拆分：`protocol/schemas.py` → `skill_schemas.py` + `tool_schemas.py`。
> - [P2-5] F05 §4.4b "6 个 la.lifecycle.run.*" → "5 个"。
> - [P2-6] F05 §3.6 中间件注入描述修正 + §3.6a doctor probe 工厂新增。
> - [P2-7] 与 [P0-1] 合并修复。
> - [P2-8] F09 §3.4 network_call 注脚 + §3.4a endpoint 决策细则 + GuardrailPolicy 增 `allow_internal_endpoints` 字段。
> - [P2-9] F04 + F10 dynamic import 命名空间约定。
> - [P2-10] F11 EvalTaskSpec schema 层 `@field_validator('expected')` 按 grader 校验 expected 类型。
> - [P2-11] F11 §三.1 EvalRunResult 增 exit_code 字段用途说明。
> - [P2-12] F13 §一 + README §一 F13 行区分 "打包时静态依赖 F01 / F11" vs "运行时依赖 仅 F01"。
>
> **v1.2.0 变更**（**review.md v1.1.0 评审修复后**——本轮 26 项问题全部应用修复；详见 `harness/feature/review.md` §六 changelog v1.2.0）：
> - [P0-1] F07 `drain_events()` + F08 `drain_spans()` + F06 cleanup step 6 拆 6.1-6.4（Span/Event 数据流断链修复）
> - [P0-2] `LoadedAgent.compiled_graph` 字段**删除**（方案 B）；schema_version v0.1.0 → v0.2.0；F01 dispatch 独立持 LoadedAgent + CompiledStateGraph 两变量
> - [P0-3 + P0-5] F07 / F08 / F09 / F10 / F11 五处 prompt header 批次与依赖列与 README §二 推荐批次表对齐；F10 依赖列补 F08 Phase 1
> - [P0-4] F11 runner.run() RuntimeConfig 来源明确；F11 依赖列补 F03；F11 TDD 新增 2 项配置解析测试
> - [P0-6] F07 §3.4 标题"≥12 种" → "≥13 种"
> - [P1-1 ~ P1-9] 9 项 P1 中等问题全部修复（emitter 边界 / exit_code 用途 / evals 5 grader / guardrail 转发 / 阶段黑名单引用 / §3.3 拆分 / pyproject.toml 双重含义）
> - [P2-1 ~ P2-11] 11 项 P2 轻微问题全部修复（模板 typo / API docstring / 脱敏测试 / schema 路径 / grader 兜底 / 退出码备注 / layout 测试 / hiddenimports 注释 / dispatch 测试改写 / tool_call_match 双层校验）
> - 顶层设计三件套主版本号同步 v0.5.0/v0.4.0 → **v1.2.0**

---

## 一、Feature 总览表（13 个）

> **依赖列定义**（**review.md v2.4.0 P1-2 修复**）：将原单列"依赖的 feature"拆为 2 列：
> - **模块 import 依赖**：F 本模块代码中 `from X import ...` 直接依赖的 feature（可通过 `architecture_modules.md` 依赖矩阵 + 20×20 边校验）。
> - **运行时调用依赖**：F 通过 F01 dispatch 间接调用或其他机制（如 F13 打包时 AST 追踪）形成的依赖；非 import 关系，不进 module_id 依赖矩阵。
> 对仅一类依赖的 feature，另一列留 `—`。

| feature_id | 中文名称 | 涉及模块（来自 architecture_modules.md） | 涉及 schema（来自 module_schemas.md） | 触发阶段（来自 workflow.md） | 对应 MDA 能力 | 模块 import 依赖 | 运行时调用依赖 |
|---|---|---|---|---|---|---|---|
| **F01** | Primitives 层封装 | `primitives_chat_model_factory` / `primitives_state_graph_builder` / `primitives_checkpoint_adapter` / **`primitives_langchain_types`**（**v0.3.0 M-3 修复新增**）/ **`primitives_state_reducers`**（**v0.4.0 M-4 方案 C 修复新增**） | `MiddlewareSpec`（评审 s-3 修复后：F01 拥有）；**v0.4.0 M-4 方案 C 修复后**：reducer 函数实现位于 `primitives_state_reducers` | `model_adapt` / `graph_compose` | agent-definition / middleware / tools | **F02 Phase 1（硬例外单向依赖）**（**review.md v2.2.0 P1-3 修复**：F01 通过 `primitives → cross_cutting_logger` 硬例外单向边 →¹ 调用 `cross_cutting_logger.emit()` 接口发射 9 个 model_adapt / graph_compose log tag；`architecture_modules.md` v2.4.0 依赖矩阵显式登记 + CHK-AR-021 校验单向性；F02 Phase 1 与 F01 在第 1 批并行开发；**review.md v3.0.0 P2-2 修复补充**：logger 是被动接口，不反向依赖 F01）<br>**F06（硬例外单向依赖，v2.4.0 新增）**：F01 `chat_model_factory.create()` + `state_graph_builder.build()` 应用 `@cross_cutting_stage_guard_decorator` 实施 model_adapt / graph_compose 阶段能力边界（CHK-AR-023 校验）；F06 拥有 `langagent/cross_cutting/stage_guard.py` 公开 API | — |
| **F02** | 横切层日志与指标（**45 项 ALLOWED_TAGS 契约定义方**） | `cross_cutting_logger`（**review.md v0.5.0 评审 v0.1.0 §二.A.3 方案 A 修复**：合并 EventBusProtocol 接口定义；**review.md v2.4.0 P0-1 修复**：F02 是 45 项 log tag 白名单的**权威契约定义方**，F03/F04/F05/F06/F07/F08/F09/F01/F11 共 9 个 feature 是**消费方**，各 feature `test_*_log_tags_in_whitelist` 仅断言"本 feature 发射的 tag 在白名单中"，不约束白名单本身内容）/ `cross_cutting_metrics_collector` | `Span` / `Trace` / `MetricsSnapshot` | `dir_load` / `config_resolve` / `model_adapt` / `graph_compose` / `main_loop` / `exit_cleanup`（横切） | （横切能力） | —（Phase 1 logger 是 primitives 层之上的最底层横切基础；Phase 2 metrics_collector 订阅 F03 event bus） | F01（**review.md v1.0.0 P1-3 修复**：F02 Phase 1（cross_cutting_logger + ALLOWED_TAGS **45 项**契约 + EventBusProtocol 接口）必须与 F01 在同一批次并行开发——F01 通过硬例外单向边 `primitives → cross_cutting_logger` 依赖 `emit()` 接口发射 9 个 model_adapt / graph_compose log tag） |
| **F03** | Protocol 层 Event 总线 | `protocol_event_bus` | `Event` | `graph_compose` / `main_loop` / `exit_cleanup` | （Event 总线基础设施） | F02（logger 子模块 + EventBusProtocol）；F02 Phase 2 metrics_collector 订阅 F03 事件总线 | — |
| **F04** | 横切层审计与护栏（三级护栏模式） | `cross_cutting_audit_recorder` / `cross_cutting_guardrail_middleware` | `AuditEntry` / **`GuardrailPolicy`** / **`GuardrailDecision`**（**review.md v0.1.0 R-002 修复明确**：F04 owns GuardrailPolicy / GuardrailDecision 类型；RuntimeConfig.guardrail_policy 字段由 F07 注入，**但 F04 TDD 阶段不依赖 F07 代码**，仅在 F10 整合测试阶段通过 `config.guardrail_policy` 接口集成） | `main_loop` / `exit_cleanup` | guardrails | F02 / F03 / F01（AgentMiddleware / BaseTool 类型注解通过 primitives_langchain_types re-export） | — |
| **F05** | Protocol 层 Skill + Tool 加载 | `protocol_skill_loader` / `protocol_tool_registry` | `SkillSpec` / `SkillFrontmatter` / `ToolSpec` | `dir_load` / `graph_compose` | skills / tools | F02 / F03 / F01（BaseTool / AgentMiddleware 类型注解） | — |
| **F06** | 智能体目录加载（dir_load 阶段） | `runtime_dir_loader` + **`cross_cutting_stage_guard`**（**review.md v2.2.2 P0-1 修复后归属**：F06 是 `cross_cutting/stage_guard.py` 首批实现方；`stage_guard.py` v0.3.0 M-9 用 `sys.addaudithook` + monkeypatch 混合方案；**v0.4.0 M-NEW-5 修复后**模板 agent.py 含完整 5 字段 AgentState + 占位符统一 `<your-...>` 形式） | `LoadedAgent` | `dir_load` | project-structure / instructions / agent-definition | F02 / F05 | F01 / F07 / F08 / F09（共用 `@cross_cutting_stage_guard_decorator`，由 F06 拥有 `stage_guard.py` 公开 API；CHK-AR-023 校验 6 阶段装饰器应用） |
| **F07** | 配置解析（config_resolve 阶段） | `runtime_config_resolver`（v0.3.0 S-1 修复：RuntimeConfig.model 改可选 + with_model；v0.3.0 m-5 修复：占位符校验） | `RuntimeConfig`（v0.3.0 schema_version v0.3.0，含 `guardrail_policy` 字段） | `config_resolve` | local-development / identity | F02 + F06（`stage_guard.py` 公开 API） | — |
| **F08** | ReAct 主循环（main_loop 阶段） | `runtime_main_loop_dispatcher`（v0.3.0 M-3 修复：通过 primitives.langchain_types re-export LangChain 类型，不直接 import；**v0.4.0 M-4 方案 C 修复后**：reducer 函数从 primitives.state_reducers import，不在本模块定义 reducer） | `AgentState` | `main_loop` | agent-definition / evals | F02 / F03 / F04 / F06（`stage_guard_decorator`）+ F01（`primitives_state_graph_builder` 提供 CompiledStateGraph + `primitives_langchain_types` re-export + `primitives_state_reducers` 提供 **3 个唯一 reducer 函数**覆盖 4 个自定义字段，**v1.0.0 P1-4 修复**）<br>**v2.4.0 P0-1 新增**：F08 `build_doctor_probes()` API 内部硬例外单向 import `primitives_chat_model_factory` + `primitives_checkpoint_adapter`（**review.md v3.0.0 P2-3 修复补充**：2 条硬例外边 `runtime_main_loop_dispatcher → primitives_{chat_model_factory, checkpoint_adapter}`；primitives 是被动接口 `create(config)` 构造方法，不反向依赖 F08；CHK-AR-025 校验这 2 条硬例外边的单向性） | — |
| **F09** | 退出清理（exit_cleanup 阶段 + doctor 自检） | `runtime_exit_handler`（v0.3.0 S-3 修复：cleanup API 扩展 5 参 = 2 positional + 3 keyword-only；**v0.5.0 评审 v0.1.0 §二.A.2 修正**：原 prose 误写 6 参；v0.3.0 M-7 修复：worst_of 退出码仲裁；v0.3.0 S-2 修复：DoctorReport 改 RuntimeConfigSnapshot；**v0.4.0 M-NEW-4 修复**§3.6.1 cleanup 步骤失败 continue-on-failure 策略显式化） | `DoctorReport` / `EvalReport` / **`RuntimeConfigSnapshot`**（**v0.3.0 S-2 修复新增**） | `exit_cleanup` | cli / evals / doctor | F01 / F02 / F03 / F04 / F06（`stage_guard_decorator`）+ F08（`primitives_checkpoint_adapter.close()`） | — |
| **F10** | CLI 入口与子命令分发 | `cli_runner` / `cli_parser` / `cli_output_formatter`（v0.3.0 M-8 修复：init 子命令移除 --template 参数；v0.3.0 S-5 修复：dispatch 显式调用 checkpoint_adapter.create；v0.3.0 M-2 修复：增补 format_chat_message / format_*_stdout 3 个 stdout 输出 API） | （消费 F09 的 DoctorReport / F11 的 EvalReport；v0.3.0 第四批 S-5 修复：doctor dispatch 编排 probe lambda 注入 F09.run_doctor_checks） | （CLI 入口跨所有阶段；v0.3.0 S-2 修复：CLI 严禁直接发射 la.* tag，由 F01 / F06 / F07 / F08 / F09 / F11 各自按阶段归属发射） | cli | F01 / F06 / F07 / F08 / F09 | F11（**接口契约依赖，无 import，v2.4.0 P1-2 修复明确 + review.md v3.0.0 P1-1 修复**：F10 `cli_runner.parse_argv()` 输出 dict 结构通过 `eval_runner.run(agent_dir, *, config, args)` 参数传入；F10 dispatch `langagent eval` 分支 lazy import `from langagent.eval.runner import run`；F11 runner 不反向 import F10 任何符号；详见 F11 §三 header 接口契约依赖段） |
| **F11** | Eval 子系统（EvalTaskSpec + Grader + EvalReport） | **`eval_runner`**（**v2.4.0 P1-3 修复后 21st module_id 显式登记**；`langagent/eval/runner.py`）+ `eval/task_loader` + `eval/report_aggregator` + **5 graders**（**v2.4.0 P2-3 修复后显式登记**：`langagent/eval/graders/{exact_match,contains,regex,llm_judge,tool_call_match}.py`；统一接口 `grade(actual, expected, **kwargs) -> bool`；不计入 21 个 module_id 计数） | `EvalTaskSpec` / `EvalReport` / **`EvalRunResult`**（**v0.4.0 M-NEW-1 修复新增**：runner 返回类型）/ **`RuntimeConfig`**（**review.md v1.0.0 P0-3 修复**：F11 消费 F07 的 RuntimeConfig，构造 `EvalRunResult` 需 RuntimeConfig 用于 model / checkpointer 实例化） | `main_loop` / `exit_cleanup` | evals | F01 / F03（**v2.2.0 P2-6 修复新增**：F11 runner.publish `eval_task_started` / `eval_task_done` 事件）+ F06（`dir_loader.load()` 加载被评测智能体）+ **F07（RuntimeConfig 类型消费；**review.md v2.4.0 P0-2 修复**：F11 runner 不内部 resolve config，由 F10 dispatch 注入）**+ F08（`main_loop_dispatcher.run_until_done()` 跑每条任务）（`chat_model_factory.create()` 用于 llm_judge judge_model 独立实例） | F10（**接口契约依赖，无 import，v2.0.0 P1-2 修复明确**：F10 `cli_runner.parse_argv()` 输出 dict 结构 `{cli_args: dict, grader_only: str-or-None, task: str-or-None}` 通过 `eval_runner.run(agent_dir, *, config, args)` 参数传入；F11 runner 不 import F10 任何符号）+ F09（F10 dispatch eval 分支在 `eval_runner.run()` 返回后调 `exit_handler.cleanup(result.final_state, config, eval_report=...)` 写盘 + 退出码仲裁；F11 runner 不直接 import F09） |
| **F12** | 打包与分发（PyInstaller 单文件二进制） | （跨 cli/runtime 整合，无独立模块） | （无新 schema） | （打包阶段，非 6 阶段之一） | （MDA 无对应；宪法第 XI 条要求） | —（F12 build script 不 import 任何业务模块符号） | **打包时静态依赖**：F10（PyInstaller 入口 `langagent/__main__.py`）+ F11（**v2.2.0 P1-4 修复**：PyInstaller AST 静态分析追踪 F10 `cli_runner.py` 中 `langagent eval` 分支的 lazy import `from langagent.eval.runner import run`，**自动发现并打包 F11 runner 模块进二进制**；**不需要在 hiddenimports 列表中显式列出** `langagent.eval.runner`，详见 F12 §3.2 hiddenimports 配置）<br>**运行时依赖**：仅 F10（**review.md v3.0.0 P1-3 修复明确**：用户执行二进制后由 F10 dispatch 决定是否 lazy import F11；F12 打包阶段非 6 阶段之一，"运行时调用依赖"在此处指"用户运行二进制后的依赖"） |
| **F13** | V1 预留接口（6 个 schema 类型 stub） | （无对应模块；v1 仅定义类型） | `ChannelSpec` / `ChannelContext` / `SandboxSpec` / `ScheduleSpec` / `MemorySpec` / `IdentitySpec` | （v1 不触发） | channels / sandboxes / schedules / memory / identity | — | — |

> **说明 0**：F13 没有运行时依赖（仅 v1 schema 类型 stub），可与任何 feature 并行开发；为流程顺序清晰排在末尾。
> **说明 0a**（**review.md v3.0.0 P1-3 修复新增**）：F12 特殊性——打包时静态依赖 vs 运行时依赖：F12 在**打包时**静态依赖 F10/F11（PyInstaller 入口 + AST 分析），在**运行时**仅依赖 F10（用户执行二进制后由 F10 dispatch 决定是否 lazy import F11）。F12 本身是打包阶段（非 6 阶段之一），"运行时调用依赖"列的语义在 F12 行指"用户运行二进制后的依赖"。
> **说明 1**：F01、F02、F03、F04、F05 在 architecture_modules.md 中已建立映射。本表完整复用，按开发顺序重新编号。
> **说明 2**：F11、F12、F13 是顶层设计未显式编号但必须补齐的"补集" feature，对应 23 个 schema 中未被 F01-F10 显式承载的类型 + 宪法第 XI 条打包要求。

---

## 二、开发顺序（拓扑排序）

> 按 `architecture_modules.md` 依赖矩阵的 `→` 边做拓扑排序；
> 所有 `→` 边均从高层指向低层（cli / runtime / protocol / cross_cutting → primitives），无回路。

```
[F01 + F02 Phase 1 并行] → [F03] → [F02 Phase 2 + F04 并行] → [F05] → [F06] → [F07] → [F08 / F09 并行] → [F10] → [F11] → [F12]
                                                                                                        └─ [F13] 任意时机并行
```

> **review.md v2.1.0 P0-1 修复**：原 `[F06 / F07 并行]` 修订为 `[F06] → [F07]`（F07 必须排在 F06 之后）。原因：F07 `runtime_config_resolver.resolve()` 入口装饰器 `@stage_guard_decorator` 由 F06 `stage_guard.py` 提供（F06 §3.4b "F06 是 stage_guard.py 首批实现方，**作为 runtime 层公用工具模块被 F07/F08/F09 复用**"）；若 F06 / F07 并行启动，F07 TDD Red 阶段拿不到 `stage_guard_decorator` 接口。第 5 批拆为"F06 → F07"二阶段；F06 完成 §七 deliverable 中 `langagent/cross_cutting/stage_guard.py` 后 F07 才能启动。

> **review.md v1.0.0 P0-2 修复**：原 `[F01] → [F02]` 顺序修订为 `[F01 + F02 Phase 1 并行]`。原因：F01 依赖 F02 `cross_cutting_logger.emit()` 接口发射 model_adapt/graph_compose 阶段 9 个 log tag（architecture_modules.md 依赖矩阵 primitives → cross_cutting_logger 是 →¹ 硬例外单向边）；若 F02 排在 F01 之后，F01 的测试（mock `emit()`）找不到接口。F02 Phase 1（logger + ALLOWED_TAGS **45 项** + EventBusProtocol 接口）与 F01 同批次并行，Phase 2（metrics_collector）依赖 F03 event bus 实现，移到第 3 批与 F04 并行。详见 `harness/feature/review.md` §二.P0-2 与 §三.3.2。
> F11 内部 3 相位（**v0.3.0 M-6 修复**）：Phase 1 task_loader + report_aggregator → Phase 2 5 graders → Phase 3 runner 整合（详见 F11 prompt §3.1）。

### 推荐分阶段批次（**review.md v1.0.0 P0-2 修复后**：F02 拆 Phase 1 / Phase 2，Phase 1 与 F01 在第 1 批并行）

| 批次 | feature | 阶段产物 | 可独立验证的最小命令 |
|---|---|---|---|
| **第 1 批（基座）** | **F01 + F02 Phase 1 并行** | F01：LangChain / LangGraph 原语封装 + 6 种 model_provider 工厂（无硬编码 base_url） + checkpointer 适配器 + primitives_langchain_types re-export + primitives_state_reducers + 9 个 model_adapt/graph_compose tag 发射；F02 Phase 1：cross_cutting_logger（emit + ALLOWED_TAGS **45 项** + EventBusProtocol 接口定义） | `pytest tests/test_primitives_* tests/test_logger_*` |
| **第 2 批（事件基础设施）** | F03 | Event pub/sub 总线 + Event schema + `flush(timeout=5)` + `publish_async`（实现 F02 Phase 1 的 EventBusProtocol 接口） | `pytest tests/test_event_bus_*` |
| **第 3 批（横切指标 + 安全）** | **F02 Phase 2 + F04 并行** | F02 Phase 2：cross_cutting_metrics_collector（订阅 F03 event bus）+ MetricsSnapshot 聚合；F04：AuditEntry append-only 写入 + GuardrailMiddleware（三级护栏模式） | `pytest tests/test_metrics_* tests/test_audit_* tests/test_guardrail_*` |
| **第 4 批（协议层）** | F05 | SkillSpec/ToolSpec 加载器（**v0.3.0 M-2 修复后**：移除 MCP 预留小节）+ dynamic import 不污染 sys.path | `pytest tests/test_skill_loader_* tests/test_tool_registry_*` |
| **第 4 批加注（F11 Phase 1，**review.md v0.1.0 R-006 修复新增**）** | **F11 Phase 1** | task_loader + report_aggregator（无运行时依赖；可与 F05 并行启动） | `pytest tests/eval/test_task_loader.py tests/eval/test_report_aggregator.py` |
| **第 5 批 a（运行时 1.a）** | **F06**（**review.md v2.1.0 P0-1 修复**：F06 先启动） | `LoadedAgent` 构造 + stage_guard 用 sys.addaudithook + monkeypatch 混合方案（`langagent/cross_cutting/stage_guard.py` 公开 API 落地，含 `@stage_guard_decorator` + 阶段级黑名单注册表） | `pytest tests/test_dir_loader_* tests/test_stage_guard_*` |
| **第 5 批 b（运行时 1.b）** | **F07**（**review.md v2.1.0 P0-1 修复**：F07 依赖 F06 stage_guard API，必须排在 F06 之后） | `RuntimeConfig` 冻结实例（model=None）+ 占位符校验 + stage_guard 复用 F06 @stage_guard_decorator('config_resolve', ...) | `pytest tests/test_config_resolver_*` |
| **第 6 批（运行时 2）** | F08 + F09 | LangGraph ReAct 主循环跑通（通过 primitives.langchain_types re-export；reducer 从 primitives.state_reducers import）+ checkpointer 关闭 / 报告写出（含 RuntimeConfigSnapshot）+ `langagent doctor` 4 项 check（probe 工厂由 F08 `build_doctor_probes()` 提供，**review.md v1.0.0 P0-1 修复**）+ worst_of 退出码仲裁 + continue-on-failure cleanup | `pytest tests/test_main_loop_* tests/test_exit_handler_* tests/test_doctor_checks_* tests/test_exit_code_* tests/test_runtime_config_snapshot_*` |
| **第 6 批加注（F11 Phase 2，**review.md v0.1.0 R-006 修复新增**）** | **F11 Phase 2** | 5 个 graders（exact_match / contains / regex / llm_judge / tool_call_match；依赖 F02 metrics 聚合；与 F08/F09 并行） | `pytest tests/eval/test_graders/` |
| **第 7 批（CLI）** | F10 | `langagent init / run / eval / doctor` 4 子命令端到端（init 移除 --template；run dispatch 显式调 checkpoint_adapter.create + with_model；doctor 调 F08 build_doctor_probes() 注入 probe 函数） | `langagent init demo && cd demo && langagent doctor` |
| **第 8 批（评测）** | **F11 Phase 3**（**review.md v0.1.0 R-006 修复明确**：原"第 8 批 F11"实际指 Phase 3；前两相位已在更早批次完成） | `langagent eval` 端到端：eval_runner.run() 整合（依赖 F06 / F07 / F08 / F09 / F10）+ 5 种 grader 全部实现 + EvalRunResult 3 字段 frozen dataclass | `langagent eval tests/fixtures/agent-evals/` |
| **第 8 批加注（v0.3.0 M-6 修复，**review.md v0.1.0 R-006 修复后仍保留为索引**）** | F11（按相位） | 3 相位排布索引：Phase 1 → 第 4 批加注行；Phase 2 → 第 6 批加注行；Phase 3 → 第 8 批 | 见各 phase 对应验证命令 |
| **第 9 批（交付物）** | F12 | 单文件二进制 + wheels 离线包 + 版本/Commit hash（hiddenimports 含 F11 langagent.eval.runner） | `./dist/langagent --version` |
| **并行（任意时机）** | F13 | 6 个 v1 预留 schema 类型 stub | `pytest tests/test_v1_reserved_types_*` |

> **本批测试数汇总**（**review.md v2.1.0 P3-4 修复新增**，按 F01-F13 §四 prompt "TDD 测试用例先行" 段计数）：
>
> | 批次 | feature | 测试目标数（≥） |
> |---|---|---|
> | 第 1 批 | F01 + F02 Phase 1 | F01 ≥42 + F02 ≥22 = **≥64** |
> | 第 2 批 | F03 | ≥24 + ≥3 = **≥27** |
> | 第 3 批 | F02 Phase 2 + F04 | F02 Phase 2 ≥11 + F04 ≥20 = **≥31** |
> | 第 4 批 | F05 | **≥20** |
> | 第 5 批 | F06 + F07 | F06 ≥37 + F07 ≥20 = **≥57** |
> | 第 6 批 | F08 + F09 | F08 ≥33 + F09 ≥41 = **≥74** |
> | 第 7 批 | F10 | **≥39** |
> | 第 8 批 | F11 | F11 ≥30 + F11 graders ≥15 + F11 cli ≥4 = **≥49** |
> | 第 9 批 | F12 | F12 ≥5 + F12 smoke ≥6 + F12 wheels ≥3 = **≥14** |
> | 并行 | F13 | **≥15** |
> | **合计** | — | **≥390** |
>
> **注（review.md v0.1.0 R-009 修复明确）**：≥390 为规划下限估算；speckit.specify + TDD Red 阶段会按需增补；最终实际测试数通常 **≥450**。

### 关键依赖说明

- **F02 内部相位**：F02 包含 `cross_cutting_logger`（无依赖）与 `cross_cutting_metrics_collector`（依赖 F03 的 event_bus）。
  开发时分两相位：（a）先实现 logger → （b）实现 F03 后回填 metrics 子模块。F02 的 TDD 用例需分两组：纯 logger 用例可独立运行；metrics 用例需要 F03 的 stub。
- **F01 不依赖任何 feature**：是依赖关系图的最底端，唯一允许直接 import LangChain / LangGraph 的层（**v0.3.0 M-3 修复后**：runtime / cross_cutting / protocol / cli 层仅通过 `primitives.langchain_types` re-export 间接访问）。
- **F13 不进入运行时依赖图**：仅作为 schema 类型存根，跨 feature 引用极少；任何阶段需要时可即时 stub，不阻塞主线开发。
- **F11 内部 3 相位（v0.3.0 M-6 修复）**：Phase 1 (task_loader + report_aggregator) 与 F02 / F03 / F05 并行；Phase 2 (5 graders) 可分批 PR；Phase 3 (runner 整合) 最后做。
- **F06 → F07 严格顺序**（**review.md v2.1.0 P0-1 修复新增**）：F07 复用 F06 `stage_guard.py`（详见 F06 §3.4b），F06 §七 deliverable 中 `langagent/cross_cutting/stage_guard.py` 必须在 F07 Red 阶段开始前可 import；F06 与 F07 同一批内串行（先 F06 后 F07），不可并行启动。

---

## 三、覆盖度验证（不重复不遗漏）

### 1. 模块覆盖（**21 / 21 = 100%**，**v2.4.0 P1-3 修复后 20 → 21**）

| module_id | 归属 feature |
|---|---|
| `cli_runner` | F10 |
| `cli_parser` | F10 |
| `cli_output_formatter` | F10 |
| `runtime_dir_loader` | F06 |
| `runtime_config_resolver` | F07 |
| `runtime_main_loop_dispatcher` | F08 |
| `runtime_exit_handler` | F09 |
| `protocol_event_bus` | F03 |
| `protocol_skill_loader` | F05 |
| `protocol_tool_registry` | F05 |
| `cross_cutting_logger` | F02（**review.md v0.5.0 评审 v0.1.0 §二.A.3 方案 A 修复**：本模块除日志发射外，承载 EventBusProtocol 接口定义；EventBusProtocol 接口从原独立模块 `cross_cutting_event_bus_protocol` 合并入本模块） |
| `cross_cutting_metrics_collector` | F02 |
| `cross_cutting_audit_recorder` | F04 |
| `cross_cutting_guardrail_middleware` | F04 |
| **`cross_cutting_stage_guard`** | **F06**（**review.md v2.2.2 P0-1 修复新增**：F06 首批实现 `langagent/cross_cutting/stage_guard.py`；`stage_guard.py` 从 `langagent/runtime/stage_guard.py` 移到 `langagent/cross_cutting/stage_guard.py`（**review.md v3.0.0 P2-1 修复补充**：理由是 F01 也需应用 `@stage_guard_decorator` 实施 model_adapt / graph_compose 阶段能力边界，primitives → runtime 跨层依赖违反分层约束；移到 cross_cutting 层后所有层均可单向依赖）；`@cross_cutting_stage_guard_decorator` 装饰器被 F06 / F07 / F08 / F09 / F01 共 5 个 feature 复用实施 6 阶段能力边界技术保障） |
| `primitives_chat_model_factory` | F01 |
| `primitives_state_graph_builder` | F01 |
| `primitives_checkpoint_adapter` | F01 |
| `primitives_langchain_types` | F01（v0.3.0 M-3 修复新增） |
| `primitives_state_reducers` | **F01**（**v0.4.0 M-4 方案 C 修复新增**） |
| **`eval_runner`** | **F11**（**review.md v3.0.0 P1-1 修复新增**：`langagent/eval/runner.py`，21st module_id 在 `architecture_modules.md` v2.4.0 依赖矩阵 21×21 显式登记；`cli_runner → eval_runner` 是显式登记边；跨 runtime/cli 整合模块） |

合计 **21 个模块**（**v0.3.0 M-3 + v0.4.0 M-4 方案 C + v0.5.0 评审修复 + v2.2.2 P0-1 修复 + v3.0.0 P1-1 修复**：新增 `primitives_langchain_types` + `primitives_state_reducers` + `cross_cutting_stage_guard` + `eval_runner`，17 → 18 → 19 → 20 → **21**；cross_cutting 层 **4 → 5**（v2.2.2 P0-1 修复：`cross_cutting_stage_guard` 从 runtime 层移到 cross_cutting 层）；primitives 层 4 → **5** 个；eval_runner 跨层整合模块归属 F11），每个 feature 至少 1 个模块，每个模块归属唯一 feature → **不重叠**。

### 2. Schema 覆盖（**27 / 27 = 100%**，**review.md v2.1.0 P1-4 修复后**：25 → 27；**review.md v3.0.0 P2-4 修复后**：增加"定义文件"列）

| schema_id（python_type） | 归属 feature | 定义文件（**review.md v3.0.0 P2-4 修复新增**） |
|---|---|---|
| `AgentState` | F08 | `langagent/runtime/agent_state.py` |
| `StateReducers` | **F01**（**v0.4.0 M-4 方案 C 修复新增**） | `langagent/primitives/state_reducers.py` |
| `RuntimeConfig` | F07（v0.3.0 S-1 修复：model 改可选 + with_model；**review.md v2.1.0 P1-4 修复**：增 `guardrail_policy` 字段，schema_version v0.2.0 → v0.3.0） | `langagent/runtime/config_resolver.py` |
| `RuntimeConfigSnapshot` | **F09 拥有**（**v0.3.0 S-2 修复新增**：DoctorReport 嵌套用，不含 BaseChatModel；**review.md v2.1.0 P1-4 修复**：增 `guardrail_allow_internal_endpoints` 字段，schema_version v0.1.0 → v0.2.0） | `langagent/runtime/exit_handler.py` |
| `LoadedAgent` | F06（**review.md v1.1.0 P0-2 修复后**：5 字段 `agent_dir` / `instructions` / `tool_ids` / `skill_names` / `metadata`；**已删除 `compiled_graph` 字段**；schema_version v0.2.0） | `langagent/runtime/dir_loader.py` |
| `SkillSpec` | F05（**review.md v1.1.0 P2-4 修复**：定义于 `langagent/protocol/skill_schemas.py:SkillSpec`） | `langagent/protocol/skill_schemas.py` |
| `SkillFrontmatter` | F05（**review.md v1.1.0 P2-4 修复**：定义于 `langagent/protocol/skill_schemas.py:SkillFrontmatter`） | `langagent/protocol/skill_schemas.py` |
| `ToolSpec` | F05（**review.md v1.1.0 P2-4 修复**：定义于 `langagent/protocol/tool_schemas.py:ToolSpec`） | `langagent/protocol/tool_schemas.py` |

| `MiddlewareSpec` | F01 拥有（v0.3.0 s-3 修复后：从 F05 移到 F01） | `langagent/primitives/middleware_spec.py` |
| `ChannelSpec` | F13（v1 预留） | `langagent/protocol/reserved_types/channel.py` |
| `ChannelContext` | F13（v1 预留） | `langagent/protocol/reserved_types/channel.py` |
| `SandboxSpec` | F13（v1 预留） | `langagent/protocol/reserved_types/sandbox.py` |
| `ScheduleSpec` | F13（v1 预留） | `langagent/protocol/reserved_types/schedule.py` |
| `MemorySpec` | F13（v1 预留） | `langagent/protocol/reserved_types/memory.py` |
| `IdentitySpec` | F13（v1 预留） | `langagent/protocol/reserved_types/identity.py` |
| `EvalTaskSpec` | F11（v0.3.0 M-4 修复：expected 类型扩展为 dict；schema_version v0.2.0） | `langagent/eval/task_loader.py` |
| `Span` | F02 | `langagent/cross_cutting/logger.py` |
| `Trace` | F02 | `langagent/cross_cutting/logger.py` |
| `Event` | F03 | `langagent/protocol/event_bus.py` |
| `MetricsSnapshot` | F02 | `langagent/cross_cutting/metrics_collector.py` |
| `AuditEntry` | F04 | `langagent/cross_cutting/audit_recorder.py` |
| `DoctorReport` | F09 拥有（v0.3.0 M-3 修复 + S-2 修复：runtime 改 RuntimeConfigSnapshot） | `langagent/runtime/exit_handler.py` |
| `EvalRunResult` | **F11**（**v0.4.0 M-NEW-1 修复新增**：runner.run() 返回类型；3 字段 frozen dataclass = `eval_report` / `final_state` / `exit_code`；**v0.5.0 评审 v0.1.0 §二.A.1 修复补建 schema 章节**） | `langagent/eval/runner.py` |
| `EvalReport` | F11 | `langagent/eval/report_aggregator.py` |
| **`GuardrailPolicy`** | **F04**（**review.md v2.1.0 P1-4 修复新增**：5 字段 `enabled` / `interrupt_on` / `redact_pii` / `allow_internal_endpoints` / `internal_endpoint_patterns`；承载宪法第 X 条 1 款 + 第 IV 条 4 款对齐——内网 vLLM 默认 allow） | `langagent/cross_cutting/guardrail_middleware.py` |
| **`GuardrailDecision`** | **F04**（**review.md v2.1.0 P1-4 修复新增**：5 字段 `allow` / `interrupt` / `redact` / `reason` / `is_internal_endpoint`） | `langagent/cross_cutting/guardrail_middleware.py` |

合计 **27 个类型**（**v0.3.0 S-2 修复后**：新增 RuntimeConfigSnapshot，22 → 23；**v0.4.0 M-4 方案 C 修复后**：新增 StateReducers，23 → 24；**v0.4.0 M-NEW-1 修复后**：新增 EvalRunResult，24 → 25；**review.md v2.1.0 P1-4 修复后**：新增 GuardrailPolicy + GuardrailDecision，25 → **27**；字段名 `final_state` 已统一），归属唯一 feature → **不重叠**。

### 3. 6 阶段覆盖（6 / 6 = 100%）

| stage | 归属 feature | 实现位置 |
|---|---|---|
| `dir_load` | F06 | `runtime_dir_loader.load()` |
| `config_resolve` | F07 | `runtime_config_resolver.resolve()`（产出 RuntimeConfig.model=None；v0.3.0 S-1） |
| `model_adapt` | F01 | `primitives_chat_model_factory.create()`（仅返回 BaseChatModel） |
| `graph_compose` | F01 | `primitives_state_graph_builder.build(loaded, config, checkpoint)`（checkpoint 显式传入；v0.3.0 S-5） |
| `main_loop` | F08 | `runtime_main_loop_dispatcher.dispatch()`（通过 primitives.langchain_types re-export LangChain 类型；v0.3.0 M-3） |
| `exit_cleanup` | F09 | `runtime_exit_handler.cleanup()`（含 `run_doctor_checks` 4 项 check；v0.3.0 S-3 扩展 API） |

合计 6 阶段全部分配；F01 独占 2 阶段（符合 primitives 层唯一接触 LangChain / LangGraph 的约束）。
**v0.3.0 S-5 修复**：F10 dispatch 严格按 `dir_load → config_resolve → model_adapt → graph_compose → main_loop → exit_cleanup` 编排，并显式调用 `checkpoint_adapter.create()`。

### 4. CLI 子命令覆盖（4 / 4 = 100%）

| 子命令 | 归属 feature |
|---|---|
| `langagent init <name>` | F10（编排，无 --template 参数，**v0.3.0 M-8 修复**）+ F06（`runtime_dir_loader.write_template(name)` 生成模板 + 发射 `la.lifecycle.init.start`；**review.md v3.0.0 P2-5 修复补充**：退出码 67 = `name_already_exists` 由 F06 `write_template()` 触发，当 cwd 下同名目录已存在时；workflow.md §退出码 67 指定唯一触发阶段 = `dir_load`）+ F09（`cleanup(state=None, config=None, *, init_only=True)` 极简分支 + 发射 `la.lifecycle.init.end`，**review.md v2.1.0 P1-2 修复后**：`init.end` 由 F09 在 exit_cleanup 阶段统一发射，F06 仅发 `init.start`） |
| `langagent run [agent-dir]` | F10（编排：`config.with_model(...)` + `checkpoint_adapter.create(...)` + `state_graph_builder.build(..., checkpoint)`）+ F06 + F07 + F01 + F08 + F09 |
| `langagent eval [agent-dir]` | F10（编排：`result = eval_runner.run(agent_dir, *, config, args)` → **`EvalRunResult(eval_report, final_state, exit_code)`**；**review.md v2.2.0 P1-2 + P2-1 修复**：F10 dispatch 入口 resolve config 一次，通过 keyword-only `config` 参数注入 runner；`evals/` 目录不存在 → `EvalRunResult(exit_code=66)` 由 F10 dispatch 走 cleanup 路径返回）+ F06（加载被评测智能体）+ F07（仅类型注解引用 RuntimeConfig，F11 runner 不再内部 resolve）+ F08（每条 task 跑 main_loop，**最后一条 task 的 final_state 传 F09 cleanup**）+ F11（5 种 grader 判定 + EvalReport 聚合；**v0.4.0 M-NEW-1 修复后**：runner 返回 `EvalRunResult` 而非 `int`）+ F09（最终 report 写盘） |
| `langagent doctor` | F10（编排：`DoctorReport.runtime = RuntimeConfigSnapshot.from_runtime_config(config)`，**v0.3.0 S-2**）+ F06（轻量 dir_load）+ F07 + F09（`run_doctor_checks`）+ F01 + F02 |

### 5. MDA 能力覆盖（15 / 15 = 100%）

| mda_capability | 归属 feature |
|---|---|
| agent-definition | F06 + F08 |
| cli | F10 |
| evals | F11（**review.md v1.1.0 P1-3 修复新增**：5 种 grader = `exact_match` / `contains` / `regex` / `llm_judge` / `tool_call_match`；F11 §三.3 实现） |
| identity | F13（v1 预留） |
| instructions | F06 |
| local-development | F06 + F07 |
| mcp-connectors | F05（**v0.3.0 M-2 修复后**：tool_registry 扩展点保留，但 v1 不实现；后续 v2 feature） |
| middleware | F05 + F04 |
| project-structure | F06 + F13 |
| skills | F05 |
| tools | F05 |
| sandboxes | F13（v1 预留） |
| schedules | F13（v1 预留） |
| memory | F13（v1 预留） |
| channels | F13（v1 预留） |

10 个 active 全部落到 F01-F11（agent-definition / cli / evals / instructions / local-development / mcp-connectors / middleware / project-structure / skills / tools）；**5 个 v1 预留（channels / sandboxes / schedules / memory / identity）全部落到 F13**（**review.md v2.0.0 P1-3 修复后**：原 prose "11 active + 4 个 v1 预留" 计数与表格 15 行冲突，统一为 "10 active + 5 个 v1 预留 = 15 项"）。

### 6. 退出码 + 日志标签覆盖

#### 6.1 退出码（13 个）

| 退出码 | 归属 feature | 触发场景 |
|---|---|---|
| 0 / 1 / 2 / 3 / 4 / 5 | F09 `cleanup()` `worst_of()` 仲裁 | 通用 / argparse / JSON / I/O / 字段缺失 |
| 64 / 65 / 66 / 67 / 70 / 78 | F09 + F06 / F07 / F05 / F01 各阶段 | EX_USAGE / EX_DATAERR / EX_NOINPUT / name_already_exists / EX_SOFTWARE / EX_CONFIG |
| 130 | F09 + F08 `run_until_done()` Ctrl-C 捕获 | SIGINT |

> **review.md v0.3.0 M-7 修复**：F09 提供 `worst_of(codes: list[int]) -> int` 函数实现 **13 级**优先级仲裁（**review.md v2.0.0 P1-1 修复后**：v0.5.0 changelog 新增的退出码 67 = `name_already_exists` 已补入 F09 §3.3 优先级表第 3 级；worst_of 函数自动适配）。

#### 6.2 日志标签（≥45 个，review.md v0.3.0 s-1 / s-2 / s-5 修复后归属）

| 标签分类 | 数量 | 发射方 feature（review.md v0.3.0 S-1 / S-2 / S-3 / S-4 修复明确） |
|---|---|---|
| `la.lifecycle.init.start` | 1 | F06 `runtime_dir_loader.write_template()` |
| `la.lifecycle.init.end` | 1 | F09 `runtime_exit_handler.cleanup()`（init-only cleanup 模式，**review.md v2.2.0 P1-1 修复**：`init.end` 触发阶段归属 = `exit_cleanup`，由 F09 在 init 子命令末尾 cleanup 阶段统一发射；F06 §3.5 不再发射 init.end） |
| `la.lifecycle.run.{start, turn, tool_call, tool_result, model_response}` | 5 | F08 `runtime_main_loop_dispatcher.dispatch()` |
| `la.lifecycle.eval.{start, case_done, summary}` | 3 | F11 `eval/runner.run()` / `_run_one_task()` |
| `la.lifecycle.doctor.{check, report}` | 2 | F09 `runtime_exit_handler.run_doctor_checks()` / `cleanup()` |
| `la.runtime.dir_load.{start, ok, fail}` | 3 | F06 `runtime_dir_loader.load()` |
| `la.runtime.config_resolve.{start, priority_merge, ok, fail}` | 4 | F07 `runtime_config_resolver.resolve()` |
| `la.runtime.model_adapt.{start, endpoint_probe, ok, fail}` | 4 | **F01 `primitives_chat_model_factory.create()`**（review.md v0.3.0 S-1 修复明确） |
| `la.runtime.graph_compose.{start, middleware_bind, tool_bind, ok, fail}` | 5 | **F01 `primitives_state_graph_builder.build()`**（review.md v0.3.0 S-1 修复明确） |
| `la.runtime.main_loop.{start, turn.start, turn.end, model_call, tool_call, tool_result, end}` | 7 | F08 `runtime_main_loop_dispatcher.dispatch()` |
| `la.runtime.exit_cleanup.{start, checkpointer_close, report_write, audit_flush, ok, fail}` | 6 | F09 `runtime_exit_handler.cleanup()` |
| `la.cross_cutting.guardrail.block` | 1 | F04 `cross_cutting_guardrail_middleware.evaluate()` |
| `la.cross_cutting.audit.write` | 1 | F04 `cross_cutting_audit_recorder.write()` |
| `la.cross_cutting.metrics.emit` | 1 | F02 `cross_cutting_metrics_collector.snapshot()` |
| `la.cross_cutting.event_handler_error` | 1 | F03 `protocol_event_bus.publish()` 异常隔离时（通过 F02 logger.emit） |
| **合计** | **45** | **F01 / F02 / F03 / F04 / F06 / F07 / F08 / F09 / F11 共 9 个 feature 直接发射；F02 还提供 `emit()` 接口 + 白名单校验（45 项登记）** |

> **review.md v0.3.0 s-5 修复明确**：
> - **CLI 层严禁直接发射任何 `la.*` tag**（architecture_modules.md#mod-cli-parser 硬约束：`× cross_cutting_logger`）。
> - F10 仅作为入口编排，`langagent init/run/eval/doctor` 启动后用户可观测到上述 tag 由各 feature 按阶段发射；F10 dispatch 不直接 import `cross_cutting_logger`。
> - **F02 logger 是 45 项 log tag 白名单的权威契约定义方**（**review.md v3.0.0 P1-2 修复**）：`ALLOWED_TAGS` 集合 ≥**45**；F01/F03/F04/F06/F07/F08/F09/F11 共 8 个 feature 是消费方，各 feature `test_*_log_tags_in_whitelist` 测试仅断言"本 feature 发射的 tag 在白名单中"，**不约束白名单本身内容**（白名单由 F02 唯一维护）。所有 9 个发射方 feature 通过 `from langagent.cross_cutting.logger import emit` 调用。
>
> **review.md v0.3.0 S-6 修复**：所有日志走 stderr（文本 + JSONL 双格式）；stdout 仅对话内容。

### 7. 宪法硬约束覆盖

| 宪法条款 | 归属 feature |
|---|---|
| 第 I 条 项目身份与边界 | F10（CLI）+ F12（打包） |
| 第 II 条 技术栈与依赖范围 | F01（primitives 层 LangChain / LangGraph 封装）+ `primitives_langchain_types`（v0.3.0 M-3 修复） |
| 第 III 条 LangSmith 剥离原则 | F01（不依赖 LangSmith）+ F02（不写 LangSmith tag）+ F12（spec excludes） |
| 第 IV 条 模型抽象层 | F01（6 种 provider，无硬编码 base_url，**v0.3.0 S-4 修复**）+ F07（model_base_url=None，**v0.3.0 M-1 修复**） |
| 第 V 条 智能体目录契约 | F06（layout 校验 + .env.example 占位符 + stage_guard monkeypatch + audit_hook 混合方案，**v0.3.0 S-6 修复**）+ F05 + F13 |
| 第 VI 条 Agent Loop 与 State | F08（main_loop dispatcher 通过 primitives.langchain_types re-export，**v0.3.0 M-3**）+ F01（StateGraph 构造） |
| 第 VII 条 Middleware 与工具规则 | F05（tool 注册）+ F04（guardrail middleware，三级护栏模式） |
| 第 VIII 条 TDD 刚性约束 | 所有 feature 的 prompt 都明确"先 Red 后 Green 再 Refactor" |
| 第 IX 条 质量诊断能力矩阵 | F02（tracing + monitoring + EventBusProtocol 接口）+ F11（evaluation + testing）+ F04（guardrails） |
| 第 X 条 安全与隐私 | F04（guardrail + AuditEntry 3 类事件） |
| 第 XI 条 打包与分发 | F12（PyInstaller） |
| 第 XII 条 配置与可观测契约 | F07（优先级链 + 占位符校验 **v0.3.0 m-5** + RuntimeConfig.with_model **v0.3.0 S-1**）+ F02（Span 7 字段） |
| 第 XIII 条 禁止项 | 所有 feature prompt 强制引用；v0.3.0 S-4 修复 base_url 硬编码 |
| 第 XV 条 顶层设计优先 | 每个 feature prompt 顶部"MUST 先读三份顶层设计 artefact" |

---

## 四、Feature 提示词索引

| feature_id | 文件 | 一句话定位 |
|---|---|---|
| F01 | `01_primitives层封装.md` | 6 种 model_provider（无硬编码 base_url，v0.3.0 S-4）+ StateGraph 编译 + checkpointer + primitives_langchain_types re-export（v0.3.0 M-3）+ **v0.4.0 M-4 方案 C 新增 primitives_state_reducers 模块** + **v0.4.0 M-NEW-2 硬例外单向边 primitives → cross_cutting_logger** + **v0.4.0 m-NEW-6 importlib 强化** |
| F02 | `02_横切层日志与指标.md` | la.* 日志走 stderr（v0.3.0 S-6 + **v0.4.0 m-NEW-8 emit() 强制 stderr**）+ MetricsSnapshot 聚合 + EventBusProtocol 接口（v0.3.0 m-2）+ **v0.4.0 M-NEW-3 log tag rename** |
| F03 | `03_event总线.md` | protocol_event_bus pub/sub + flush(timeout=5)（v0.3.0 M-5）+ publish_async（v0.3.0 m-1） |
| F04 | `04_横切层审计与护栏.md` | AuditEntry 写入 + 三级护栏模式（v0.3.0 M-3 通过 primitives.langchain_types 导入 AgentMiddleware） |
| F05 | `05_protocol层skill与tool加载.md` | 扫描 skills/ 与 tools/ 产出 SkillSpec / ToolSpec（v0.3.0 M-2 移除 MCP 预留）+ **v0.4.0 m-NEW-2 未声明 SIDE_EFFECTS 警告日志** + **v0.4.0 m-NEW-3 args_schema JSON Schema Draft 7** + **v0.4.0 m-NEW-10 tool_id 异常传播路径** |
| F06 | `06_智能体目录加载.md` | 校验宪法第 V 条布局 + stage_guard monkeypatch+audit_hook 混合方案（v0.3.0 M-9 + S-6）+ 产出 `LoadedAgent` + **v0.4.0 M-NEW-5 模板 5 字段 AgentState 修复** + **v0.4.0 m-NEW-7 占位符统一 `<your-...>`** |
| F07 | `07_配置解析.md` | CLI > 环境变量 > .env > 内置默认 优先级链合并 + 占位符校验（v0.3.0 m-5 + **v0.4.0 m-NEW-7 统一 `<your-...>`**）+ RuntimeConfig.model=None + with_model（v0.3.0 S-1） |
| F08 | `08_react主循环.md` | 驱动 LangGraph CompiledStateGraph 跑 ReAct（v0.3.0 M-3 通过 primitives.langchain_types re-export）+ **v0.4.0 M-4 方案 C reducer 从 primitives.state_reducers import** + **v0.4.0 M-NEW-3 log tag rename** |
| F09 | `09_退出清理.md` | 关闭 checkpointer + 写出 Span / Event / 报告 + 5 参 cleanup API（v0.3.0 S-3；**v0.5.0 评审 v0.1.0 §二.A.2 修正**：原 prose 误写 6 参）+ worst_of 仲裁（v0.3.0 M-7）+ RuntimeConfigSnapshot（v0.3.0 S-2）+ **v0.4.0 M-NEW-4 §3.6.1 步骤失败 continue-on-failure 显式化** |
| F10 | `10_cli入口与子命令分发.md` | 把 argv 翻译成 4 个子命令并接入 6 阶段调度（v0.3.0 修复：init 无 --template；run 显式 checkpoint_adapter.create；**v0.4.0 M-NEW-3 修复**：la.cli.* → la.lifecycle.*；**v0.4.0 M-NEW-1 修复**：eval dispatch 接 EvalRunResult；**v0.3.0 M-2 修复**：stdout/stderr 语义分离 + 新增 format_chat_message / format_*_stdout 3 个 stdout API；**review.md v1.0.0 P0-1 修复**：doctor probe 工厂从 F10 移到 F08 `build_doctor_probes()`，恢复 CLI × primitives 黑名单约束） |
| F11 | `11_eval子系统.md` | EvalTaskSpec 加载 + 5 种 grader + EvalReport（3 相位开发，v0.3.0 M-6）+ eval_runner 归属明确（v0.3.0 M-4）+ **v0.4.0 M-NEW-1 runner 返回 EvalRunResult(eval_report, final_state)** + **v0.4.0 m-NEW-1 args: dict 类型** + **v0.4.0 M-NEW-3 log tag rename** + **v0.4.0 m-NEW-9 grader_extensibility 用途澄清** |
| F12 | `12_打包与分发.md` | PyInstaller 单文件二进制 + wheels 离线包 + **v0.4.0 m-NEW-5 hiddenimports 扩展 langchain_core 等基础包** |
| F13 | `13_v1预留接口.md` | 6 个 v1 预留 schema 类型 stub |

---

