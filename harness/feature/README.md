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
> - [P0-2] 推荐批次表修订：F08 拆 Phase 1（cross_cutting_logger + EventBusProtocol 接口 + ALLOWED_TAGS **46 项**契约）/ Phase 2（metrics_collector）；Phase 1 与 F10 在第 1 批并行；Phase 2 在第 3 批与 F09 并行。
> - [P0-3] F11 依赖列补 F03（`config_resolver.resolve()`）。
> - [P1-1] F01 一句话定位补 stdout/stderr 语义分离 + format_chat_message / format_*_stdout 3 个 stdout API 说明。
> - [P1-2] F02 §3.4 错误引用"宪法第 V 条"修正为"workflow.md §系统视角：6 阶段"。
> - [P1-3] F08 行增加 **46 项**ALLOWED_TAGS 契约性质说明。
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
| **F10** | Primitives 层封装 | `primitives_chat_model_factory` / `primitives_state_graph_builder` / `primitives_checkpoint_adapter` / **`primitives_langchain_types`**（**v0.3.0 M-3 修复新增**）/ **`primitives_state_reducers`**（**v0.4.0 M-4 方案 C 修复新增**） | `MiddlewareSpec`（评审 s-3 修复后：F10 拥有）；**v0.4.0 M-4 方案 C 修复后**：reducer 函数实现位于 `primitives_state_reducers` | `model_adapt` / `graph_compose` | agent-definition / middleware / tools | **F08 Phase 1（硬例外单向依赖）**（**review.md v2.2.0 P1-3 修复**：F10 通过 `primitives → cross_cutting_logger` 硬例外单向边 →¹ 调用 `cross_cutting_logger.emit()` 接口发射 9 个 model_adapt / graph_compose log tag；`architecture_modules.md` v2.4.0 依赖矩阵显式登记 + CHK-AR-021 校验单向性；F08 Phase 1 与 F10 在第 1 批并行开发；**review.md v3.0.0 P2-2 修复补充**：logger 是被动接口，不反向依赖 F10）<br>**F02（硬例外单向依赖，v2.4.0 新增）**：F10 `chat_model_factory.create()` + `state_graph_builder.build()` 应用 `@cross_cutting_stage_guard_decorator` 实施 model_adapt / graph_compose 阶段能力边界（CHK-AR-023 校验）；F02 拥有 `langagent/cross_cutting/stage_guard.py` 公开 API | — |
| **F08** | 横切层日志与指标（**46 项 ALLOWED_TAGS 契约定义方**） | `cross_cutting_logger`（**review.md v0.5.0 评审 v0.1.0 §二.A.3 方案 A 修复**：合并 EventBusProtocol 接口定义；**review.md v2.4.0 P0-1 修复**：F08 是 46 项 log tag 白名单的**权威契约定义方**，F02/F03/F04/F05/F06/F07/F09/F10/F11 共 9 个 feature 是**消费方**，各 feature `test_*_log_tags_in_whitelist` 仅断言"本 feature 发射的 tag 在白名单中"，不约束白名单本身内容）/ `cross_cutting_metrics_collector` | `Span` / `Trace` / `MetricsSnapshot` | `dir_load` / `config_resolve` / `model_adapt` / `graph_compose` / `main_loop` / `exit_cleanup`（横切） | （横切能力） | —（Phase 1 logger 是 primitives 层之上的最底层横切基础；Phase 2 metrics_collector 订阅 F07 event bus） | F10（**review.md v1.0.0 P1-3 修复**：F08 Phase 1（cross_cutting_logger + ALLOWED_TAGS **46 项**契约 + EventBusProtocol 接口）必须与 F10 在同一批次并行开发——F10 通过硬例外单向边 `primitives → cross_cutting_logger` 依赖 `emit()` 接口发射 9 个 model_adapt / graph_compose log tag） |
| **F07** | Protocol 层 Event 总线 | `protocol_event_bus` | `Event` | `graph_compose` / `main_loop` / `exit_cleanup` | （Event 总线基础设施） | F08（logger 子模块 + EventBusProtocol）；F08 Phase 2 metrics_collector 订阅 F07 事件总线 | — |
| **F09** | 横切层审计与护栏 | `cross_cutting_audit_recorder` / `cross_cutting_guardrail_middleware` | `AuditEntry` / **`GuardrailPolicy`** / **`GuardrailDecision`**（**review.md v0.1.0 R-002 修复明确**：F09 owns GuardrailPolicy / GuardrailDecision 类型；RuntimeConfig.guardrail_policy 字段由 F03 注入，**但 F09 TDD 阶段不依赖 F03 代码**，仅在 F01 整合测试阶段通过 `config.guardrail_policy` 接口集成） | `main_loop` / `exit_cleanup` | guardrails | F07 / F08 / F10（AgentMiddleware / BaseTool 类型注解通过 primitives_langchain_types re-export） | — |
| **F04** | Protocol 层 Skill + Tool 加载 | `protocol_skill_loader` / `protocol_tool_registry` | `SkillSpec` / `SkillFrontmatter` / `ToolSpec` / `ToolSideEffect` | `dir_load` / `graph_compose` | skills / tools | F07 / F08 / F10（BaseTool / AgentMiddleware 类型注解） | — |
| **F02** | 智能体目录加载（dir_load 阶段） | `runtime_dir_loader` + **`cross_cutting_stage_guard`**（**review.md v2.2.2 P0-1 修复后归属**：F02 是 `cross_cutting/stage_guard.py` 首批实现方；`stage_guard.py` v0.3.0 M-9 用 `sys.addaudithook` + monkeypatch 混合方案；**v0.4.0 M-NEW-5 修复后**模板 agent.py 含完整 5 字段 AgentState + 占位符统一 `<your-...>` 形式） | `LoadedAgent` | `dir_load` | project-structure / instructions / agent-definition | F04 / F08 | F03 / F05 / F06 / F10（共用 `@cross_cutting_stage_guard_decorator`，由 F02 拥有 `stage_guard.py` 公开 API；CHK-AR-023 校验 6 阶段装饰器应用） |
| **F03** | 配置解析（config_resolve 阶段） | `runtime_config_resolver`（v0.3.0 S-1 修复：RuntimeConfig.model 改可选 + with_model；v0.3.0 m-5 修复：占位符校验） | `RuntimeConfig`（v0.3.0 schema_version v0.3.0，含 `guardrail_policy` 字段） | `config_resolve` | local-development / identity | F02（`stage_guard.py` 公开 API）+ F08 | — |
| **F05** | ReAct 主循环（main_loop 阶段） | `runtime_main_loop_dispatcher`（v0.3.0 M-3 修复：通过 primitives.langchain_types re-export LangChain 类型，不直接 import；**v0.4.0 M-4 方案 C 修复后**：reducer 函数从 primitives.state_reducers import，不在本模块定义 reducer） | `AgentState` | `main_loop` | agent-definition / evals | F02（`stage_guard_decorator`）+ F07 / F08 / F09 / F10（`primitives_state_graph_builder` 提供 CompiledStateGraph + `primitives_langchain_types` re-export + `primitives_state_reducers` 提供 **3 个唯一 reducer 函数**覆盖 4 个自定义字段，**v1.0.0 P1-4 修复**）<br>**v2.4.0 P0-1 新增**：F05 `build_doctor_probes()` API 内部硬例外单向 import `primitives_chat_model_factory` + `primitives_checkpoint_adapter`（**review.md v3.0.0 P2-3 修复补充**：2 条硬例外边 `runtime_main_loop_dispatcher → primitives_{chat_model_factory, checkpoint_adapter}`；primitives 是被动接口 `create(config)` 构造方法，不反向依赖 F05；CHK-AR-025 校验这 2 条硬例外边的单向性） | — |
| **F06** | 退出清理（exit_cleanup 阶段 + doctor 自检） | `runtime_exit_handler`（v0.3.0 S-3 修复：cleanup API 扩展 5 参 = 2 positional + 3 keyword-only；**v0.5.0 评审 v0.1.0 §二.A.2 修正**：原 prose 误写 6 参；v0.3.0 M-7 修复：worst_of 退出码仲裁；v0.3.0 S-2 修复：DoctorReport 改 RuntimeConfigSnapshot；**v0.4.0 M-NEW-4 修复**§3.6.1 cleanup 步骤失败 continue-on-failure 策略显式化） | `DoctorReport` / `EvalReport` / **`RuntimeConfigSnapshot`**（**v0.3.0 S-2 修复新增**） | `exit_cleanup` | cli / evals / doctor | F02（`stage_guard_decorator`）+ F05 / F07 / F08 / F09 / F10（`primitives_checkpoint_adapter.close()`） | — |
| **F01** | CLI 入口与子命令分发 | `cli_runner` / `cli_parser` / `cli_output_formatter`（v0.3.0 M-8 修复：init 子命令移除 --template 参数；v0.3.0 S-5 修复：dispatch 显式调用 checkpoint_adapter.create；v0.3.0 M-2 修复：增补 format_chat_message / format_*_stdout 3 个 stdout 输出 API） | （消费 F06 的 DoctorReport / F11 的 EvalReport；v0.3.0 第四批 S-5 修复：doctor dispatch 编排 probe lambda 注入 F06.run_doctor_checks） | （CLI 入口跨所有阶段；v0.3.0 S-2 修复：CLI 严禁直接发射 la.* tag，由 F02 / F03 / F05 / F06 / F10 / F11 各自按阶段归属发射） | cli | F02 / F03 / F05 / F06 / F10 | F11（**v2.4.0 P1-2 修复明确**：F01 dispatch `langagent eval` 分支 lazy import `from langagent.eval.runner import run`；F11 runner 不反向 import F01 任何符号；详见 F11 §三 header 接口契约依赖段） |
| **F11** | Eval 子系统（EvalTaskSpec + Grader + EvalReport） | **`eval_runner`**（**v2.4.0 P1-3 修复后 21st module_id 显式登记**；`langagent/eval/runner.py`）+ `eval/task_loader` + `eval/report_aggregator` + **5 graders**（**v2.4.0 P2-3 修复后显式登记**：`langagent/eval/graders/{exact_match,contains,regex,llm_judge,tool_call_match}.py`；统一接口 `grade(actual, expected, **kwargs) -> bool`；不计入 21 个 module_id 计数） | `EvalTaskSpec` / `EvalReport` / **`EvalRunResult`**（**v0.4.0 M-NEW-1 修复新增**：runner 返回类型）/ **`RuntimeConfig`**（**review.md v1.0.0 P0-3 修复**：F11 消费 F03 的 RuntimeConfig，构造 `EvalRunResult` 需 RuntimeConfig 用于 model / checkpointer 实例化） | `main_loop` / `exit_cleanup` | evals | F02（`dir_loader.load()` 加载被评测智能体）+ **F03（RuntimeConfig 类型消费；**review.md v2.4.0 P0-2 修复**：F11 runner 不内部 resolve config，由 F01 dispatch 注入）**+ F05（`main_loop_dispatcher.run_until_done()` 跑每条任务）+ F07（**v2.2.0 P2-6 修复新增**：F11 runner.publish `eval_task_started` / `eval_task_done` 事件）+ F10（`chat_model_factory.create()` 用于 llm_judge judge_model 独立实例） | F01（**接口契约依赖，无 import，v2.0.0 P1-2 修复明确**：F01 `cli_runner.parse_argv()` 输出 dict 结构 `{cli_args: dict, grader_only: str-or-None, task: str-or-None}` 通过 `eval_runner.run(agent_dir, *, config, args)` 参数传入；F11 runner 不 import F01 任何符号）+ F06（F01 dispatch eval 分支在 `eval_runner.run()` 返回后调 `exit_handler.cleanup(result.final_state, config, eval_report=...)` 写盘 + 退出码仲裁；F11 runner 不直接 import F06） |
| **F12** | V1 预留接口（6 个 schema 类型 stub） | （无对应模块；v1 仅定义类型） | `ChannelSpec` / `ChannelContext` / `SandboxSpec` / `ScheduleSpec` / `MemorySpec` / `IdentitySpec` | （v1 不触发） | channels / sandboxes / schedules / memory / identity | — | — |
| **F13** | 打包与分发（PyInstaller 单文件二进制） | （跨 cli/runtime 整合，无独立模块） | （无新 schema） | （打包阶段，非 6 阶段之一） | （MDA 无对应；宪法第 XI 条要求） | —（F13 build script 不 import 任何业务模块符号） | **打包时静态依赖**：F01（PyInstaller 入口 `langagent/__main__.py`）+ F11（**v2.2.0 P1-4 修复**：PyInstaller AST 静态分析追踪 F01 `cli_runner.py` 中 `langagent eval` 分支的 lazy import `from langagent.eval.runner import run`，**自动发现并打包 F11 runner 模块进二进制**；**不需要在 hiddenimports 列表中显式列出** `langagent.eval.runner`，详见 F13 §3.2 hiddenimports 配置）<br>**运行时依赖**：仅 F01（**review.md v3.0.0 P1-3 修复明确**：用户执行二进制后由 F01 dispatch 决定是否 lazy import F11；F13 打包阶段非 6 阶段之一，"运行时调用依赖"在此处指"用户运行二进制后的依赖"） |

> **说明 0**：F12 没有运行时依赖（仅 v1 schema 类型 stub），可与任何 feature 并行开发；为流程顺序清晰排在末尾。
> **说明 0a**（**review.md v3.0.0 P1-3 修复新增**）：F13 特殊性——打包时静态依赖 vs 运行时依赖：F13 在**打包时**静态依赖 F01/F11（PyInstaller 入口 + AST 分析），在**运行时**仅依赖 F01（用户执行二进制后由 F01 dispatch 决定是否 lazy import F11）。F13 本身是打包阶段（非 6 阶段之一），"运行时调用依赖"列的语义在 F13 行指"用户运行二进制后的依赖"。
> **说明 1**：F10、F08、F07、F09、F04 在 architecture_modules.md 中已建立 F01-F10 映射。本表完整复用，仅调整顺序。
> **说明 2**：F11、F12、F13 是顶层设计未显式编号但必须补齐的"补集" feature，对应 23 个 schema 中未被 F01-F10 显式承载的类型 + 宪法第 XI 条打包要求。

---

## 二、开发顺序（拓扑排序）

> 按 `architecture_modules.md` 依赖矩阵的 `→` 边做拓扑排序；
> 所有 `→` 边均从高层指向低层（cli / runtime / protocol / cross_cutting → primitives），无回路。

```
[F10 + F08 Phase 1 并行] → [F07] → [F08 Phase 2 + F09 并行] → [F04] → [F02] → [F03] → [F05 / F06 并行] → [F01] → [F11] → [F13]
                                                                                                        └─ [F12] 任意时机并行
```

> **review.md v2.1.0 P0-1 修复**：原 `[F02 / F03 并行]` 修订为 `[F02] → [F03]`（F03 必须排在 F02 之后）。原因：F03 `runtime_config_resolver.resolve()` 入口装饰器 `@stage_guard_decorator` 由 F02 `stage_guard.py` 提供（F02 §3.4b "F02 是 stage_guard.py 首批实现方，**作为 runtime 层公用工具模块被 F03/F05/F06 复用**"）；若 F02 / F03 并行启动，F03 TDD Red 阶段拿不到 `stage_guard_decorator` 接口。第 5 批拆为"F02 → F03"二阶段；F02 完成 §七 deliverable 中 `langagent/runtime/stage_guard.py` 后 F03 才能启动。

> **review.md v1.0.0 P0-2 修复**：原 `[F10] → [F08]` 顺序修订为 `[F10 + F08 Phase 1 并行]`。原因：F10 依赖 F08 `cross_cutting_logger.emit()` 接口发射 model_adapt/graph_compose 阶段 9 个 log tag（architecture_modules.md 依赖矩阵 primitives → cross_cutting_logger 是 →¹ 硬例外单向边）；若 F08 排在 F10 之后，F10 的测试（mock `emit()`）找不到接口。F08 Phase 1（logger + ALLOWED_TAGS **46 项** + EventBusProtocol 接口）与 F10 同批次并行，Phase 2（metrics_collector）依赖 F07 event bus 实现，移到第 3 批与 F09 并行。详见 `harness/feature/review.md` §二.P0-2 与 §三.3.2。
> F11 内部 3 相位（**v0.3.0 M-6 修复**）：Phase 1 task_loader + report_aggregator → Phase 2 5 graders → Phase 3 runner 整合（详见 F11 prompt §3.1）。

### 推荐分阶段批次（**review.md v1.0.0 P0-2 修复后**：F08 拆 Phase 1 / Phase 2，Phase 1 与 F10 在第 1 批并行）

| 批次 | feature | 阶段产物 | 可独立验证的最小命令 |
|---|---|---|---|
| **第 1 批（基座）** | **F10 + F08 Phase 1 并行** | F10：LangChain / LangGraph 原语封装 + 6 种 model_provider 工厂（无硬编码 base_url） + checkpointer 适配器 + primitives_langchain_types re-export + primitives_state_reducers + 9 个 model_adapt/graph_compose tag 发射；F08 Phase 1：cross_cutting_logger（emit + ALLOWED_TAGS **46 项** + EventBusProtocol 接口定义） | `pytest tests/test_primitives_* tests/test_logger_*` |
| **第 2 批（事件基础设施）** | F07 | Event pub/sub 总线 + Event schema + `flush(timeout=5)` + `publish_async`（实现 F08 Phase 1 的 EventBusProtocol 接口） | `pytest tests/test_event_bus_*` |
| **第 3 批（横切指标 + 安全）** | **F08 Phase 2 + F09 并行** | F08 Phase 2：cross_cutting_metrics_collector（订阅 F07 event bus）+ MetricsSnapshot 聚合；F09：AuditEntry append-only 写入 + GuardrailMiddleware（ToolSideEffect → interrupt） | `pytest tests/test_metrics_* tests/test_audit_* tests/test_guardrail_*` |
| **第 4 批（协议层）** | F04 | SkillSpec/ToolSpec 加载器（**v0.3.0 M-2 修复后**：移除 MCP 预留小节）+ dynamic import 不污染 sys.path | `pytest tests/test_skill_loader_* tests/test_tool_registry_*` |
| **第 4 批加注（F11 Phase 1，**review.md v0.1.0 R-006 修复新增**）** | **F11 Phase 1** | task_loader + report_aggregator（无运行时依赖；可与 F04 并行启动） | `pytest tests/eval/test_task_loader.py tests/eval/test_report_aggregator.py` |
| **第 5 批 a（运行时 1.a）** | **F02**（**review.md v2.1.0 P0-1 修复**：F02 先启动） | `LoadedAgent` 构造 + stage_guard 用 sys.addaudithook + monkeypatch 混合方案（`langagent/runtime/stage_guard.py` 公开 API 落地，含 `@stage_guard_decorator` + 阶段级黑名单注册表） | `pytest tests/test_dir_loader_* tests/test_stage_guard_*` |
| **第 5 批 b（运行时 1.b）** | **F03**（**review.md v2.1.0 P0-1 修复**：F03 依赖 F02 stage_guard API，必须排在 F02 之后） | `RuntimeConfig` 冻结实例（model=None）+ 占位符校验 + stage_guard 复用 F02 @stage_guard_decorator('config_resolve', ...) | `pytest tests/test_config_resolver_*` |
| **第 6 批（运行时 2）** | F05 + F06 | LangGraph ReAct 主循环跑通（通过 primitives.langchain_types re-export；reducer 从 primitives.state_reducers import）+ checkpointer 关闭 / 报告写出（含 RuntimeConfigSnapshot）+ `langagent doctor` 4 项 check（probe 工厂由 F05 `build_doctor_probes()` 提供，**review.md v1.0.0 P0-1 修复**）+ worst_of 退出码仲裁 + continue-on-failure cleanup | `pytest tests/test_main_loop_* tests/test_exit_handler_* tests/test_doctor_checks_* tests/test_exit_code_* tests/test_runtime_config_snapshot_*` |
| **第 6 批加注（F11 Phase 2，**review.md v0.1.0 R-006 修复新增**）** | **F11 Phase 2** | 5 个 graders（exact_match / contains / regex / llm_judge / tool_call_match；依赖 F08 metrics 聚合；与 F05/F06 并行） | `pytest tests/eval/test_graders/` |
| **第 7 批（CLI）** | F01 | `langagent init / run / eval / doctor` 4 子命令端到端（init 移除 --template；run dispatch 显式调 checkpoint_adapter.create + with_model；doctor 调 F05 build_doctor_probes() 注入 probe 函数） | `langagent init demo && cd demo && langagent doctor` |
| **第 8 批（评测）** | **F11 Phase 3**（**review.md v0.1.0 R-006 修复明确**：原"第 8 批 F11"实际指 Phase 3；前两相位已在更早批次完成） | `langagent eval` 端到端：eval_runner.run() 整合（依赖 F01 / F02 / F03 / F05 / F06）+ 5 种 grader 全部实现 + EvalRunResult 3 字段 frozen dataclass | `langagent eval tests/fixtures/agent-evals/` |
| **第 8 批加注（v0.3.0 M-6 修复，**review.md v0.1.0 R-006 修复后仍保留为索引**）** | F11（按相位） | 3 相位排布索引：Phase 1 → 第 4 批加注行；Phase 2 → 第 6 批加注行；Phase 3 → 第 8 批 | 见各 phase 对应验证命令 |
| **第 9 批（交付物）** | F13 | 单文件二进制 + wheels 离线包 + 版本/Commit hash（hiddenimports 含 F11 langagent.eval.runner） | `./dist/langagent --version` |
| **并行（任意时机）** | F12 | 6 个 v1 预留 schema 类型 stub | `pytest tests/test_v1_reserved_types_*` |

> **本批测试数汇总**（**review.md v2.1.0 P3-4 修复新增**，按 F01-F13 §四 prompt "TDD 测试用例先行" 段计数）：
>
> | 批次 | feature | 测试目标数（≥） |
> |---|---|---|
> | 第 1 批 | F10 + F08 Phase 1 | F10 ≥42 + F08 ≥22 = **≥64** |
> | 第 2 批 | F07 | ≥24 + ≥3 = **≥27** |
> | 第 3 批 | F08 Phase 2 + F09 | F08 Phase 2 ≥11 + F09 ≥20 = **≥31** |
> | 第 4 批 | F04 | **≥20** |
> | 第 5 批 | F02 + F03 | F02 ≥37 + F03 ≥20 = **≥57** |
> | 第 6 批 | F05 + F06 | F05 ≥33 + F06 ≥41 = **≥74** |
> | 第 7 批 | F01 | **≥39** |
> | 第 8 批 | F11 | F11 ≥30 + F11 graders ≥15 + F11 cli ≥4 = **≥49** |
> | 第 9 批 | F13 | F13 ≥5 + F13 smoke ≥6 + F13 wheels ≥3 = **≥14** |
> | 并行 | F12 | **≥15** |
> | **合计** | — | **≥390** |
>
> **注（review.md v0.1.0 R-009 修复明确）**：≥390 为规划下限估算；speckit.specify + TDD Red 阶段会按需增补；最终实际测试数通常 **≥450**。

### 关键依赖说明

- **F08 内部相位**：F08 包含 `cross_cutting_logger`（无依赖）与 `cross_cutting_metrics_collector`（依赖 F07 的 event_bus）。
  开发时分两相位：（a）先实现 logger → （b）实现 F07 后回填 metrics 子模块。F08 的 TDD 用例需分两组：纯 logger 用例可独立运行；metrics 用例需要 F07 的 stub。
- **F10 不依赖任何 feature**：是依赖关系图的最底端，唯一允许直接 import LangChain / LangGraph 的层（**v0.3.0 M-3 修复后**：runtime / cross_cutting / protocol / cli 层仅通过 `primitives.langchain_types` re-export 间接访问）。
- **F12 不进入运行时依赖图**：仅作为 schema 类型存根，跨 feature 引用极少；任何阶段需要时可即时 stub，不阻塞主线开发。
- **F11 内部 3 相位（v0.3.0 M-6 修复）**：Phase 1 (task_loader + report_aggregator) 与 F08 / F04 / F07 并行；Phase 2 (5 graders) 可分批 PR；Phase 3 (runner 整合) 最后做。
- **F02 → F03 严格顺序**（**review.md v2.1.0 P0-1 修复新增**）：F03 复用 F02 `stage_guard.py`（详见 F02 §3.4b），F02 §七 deliverable 中 `langagent/runtime/stage_guard.py` 必须在 F03 Red 阶段开始前可 import；F02 与 F03 同一批内串行（先 F02 后 F03），不可并行启动。

---

## 三、覆盖度验证（不重复不遗漏）

### 1. 模块覆盖（**21 / 21 = 100%**，**v2.4.0 P1-3 修复后 20 → 21**）

| module_id | 归属 feature |
|---|---|
| `cli_runner` | F01 |
| `cli_parser` | F01 |
| `cli_output_formatter` | F01 |
| `runtime_dir_loader` | F02 |
| `runtime_config_resolver` | F03 |
| `runtime_main_loop_dispatcher` | F05 |
| `runtime_exit_handler` | F06 |
| `protocol_event_bus` | F07 |
| `protocol_skill_loader` | F04 |
| `protocol_tool_registry` | F04 |
| `cross_cutting_logger` | F08（**review.md v0.5.0 评审 v0.1.0 §二.A.3 方案 A 修复**：本模块除日志发射外，承载 EventBusProtocol 接口定义；EventBusProtocol 接口从原独立模块 `cross_cutting_event_bus_protocol` 合并入本模块） |
| `cross_cutting_metrics_collector` | F08 |
| `cross_cutting_audit_recorder` | F09 |
| `cross_cutting_guardrail_middleware` | F09 |
| **`cross_cutting_stage_guard`** | **F02**（**review.md v2.2.2 P0-1 修复新增**：F02 首批实现 `langagent/cross_cutting/stage_guard.py`；`stage_guard.py` 从 `langagent/runtime/stage_guard.py` 移到 `langagent/cross_cutting/stage_guard.py`（**review.md v3.0.0 P2-1 修复补充**：理由是 F10 也需应用 `@stage_guard_decorator` 实施 model_adapt / graph_compose 阶段能力边界，primitives → runtime 跨层依赖违反分层约束；移到 cross_cutting 层后所有层均可单向依赖）；`@cross_cutting_stage_guard_decorator` 装饰器被 F02 / F03 / F05 / F06 / F10 共 5 个 feature 复用实施 6 阶段能力边界技术保障） |
| `primitives_chat_model_factory` | F10 |
| `primitives_state_graph_builder` | F10 |
| `primitives_checkpoint_adapter` | F10 |
| `primitives_langchain_types` | F10（v0.3.0 M-3 修复新增） |
| `primitives_state_reducers` | **F10**（**v0.4.0 M-4 方案 C 修复新增**） |
| **`eval_runner`** | **F11**（**review.md v3.0.0 P1-1 修复新增**：`langagent/eval/runner.py`，21st module_id 在 `architecture_modules.md` v2.4.0 依赖矩阵 21×21 显式登记；`cli_runner → eval_runner` 是显式登记边；跨 runtime/cli 整合模块） |

合计 **21 个模块**（**v0.3.0 M-3 + v0.4.0 M-4 方案 C + v0.5.0 评审修复 + v2.2.2 P0-1 修复 + v3.0.0 P1-1 修复**：新增 `primitives_langchain_types` + `primitives_state_reducers` + `cross_cutting_stage_guard` + `eval_runner`，17 → 18 → 19 → 20 → **21**；cross_cutting 层 **4 → 5**（v2.2.2 P0-1 修复：`cross_cutting_stage_guard` 从 runtime 层移到 cross_cutting 层）；primitives 层 4 → **5** 个；eval_runner 跨层整合模块归属 F11），每个 feature 至少 1 个模块，每个模块归属唯一 feature → **不重叠**。

### 2. Schema 覆盖（**27 / 27 = 100%**，**review.md v2.1.0 P1-4 修复后**：25 → 27；**review.md v3.0.0 P2-4 修复后**：增加"定义文件"列）

| schema_id（python_type） | 归属 feature | 定义文件（**review.md v3.0.0 P2-4 修复新增**） |
|---|---|---|
| `AgentState` | F05 | `langagent/runtime/agent_state.py` |
| `StateReducers` | **F10**（**v0.4.0 M-4 方案 C 修复新增**） | `langagent/primitives/state_reducers.py` |
| `RuntimeConfig` | F03（v0.3.0 S-1 修复：model 改可选 + with_model；**review.md v2.1.0 P1-4 修复**：增 `guardrail_policy` 字段，schema_version v0.2.0 → v0.3.0） | `langagent/runtime/config_resolver.py` |
| `RuntimeConfigSnapshot` | **F06 拥有**（**v0.3.0 S-2 修复新增**：DoctorReport 嵌套用，不含 BaseChatModel；**review.md v2.1.0 P1-4 修复**：增 `guardrail_allow_internal_endpoints` 字段，schema_version v0.1.0 → v0.2.0） | `langagent/runtime/exit_handler.py` |
| `LoadedAgent` | F02（**review.md v1.1.0 P0-2 修复后**：5 字段 `agent_dir` / `instructions` / `tool_ids` / `skill_names` / `metadata`；**已删除 `compiled_graph` 字段**；schema_version v0.2.0） | `langagent/runtime/dir_loader.py` |
| `SkillSpec` | F04（**review.md v1.1.0 P2-4 修复**：定义于 `langagent/protocol/skill_schemas.py:SkillSpec`） | `langagent/protocol/skill_schemas.py` |
| `SkillFrontmatter` | F04（**review.md v1.1.0 P2-4 修复**：定义于 `langagent/protocol/skill_schemas.py:SkillFrontmatter`） | `langagent/protocol/skill_schemas.py` |
| `ToolSpec` | F04（**review.md v1.1.0 P2-4 修复**：定义于 `langagent/protocol/tool_schemas.py:ToolSpec`） | `langagent/protocol/tool_schemas.py` |
| `ToolSideEffect` | F04（**review.md v1.1.0 P2-4 修复**：定义于 `langagent/protocol/tool_schemas.py:ToolSideEffect`） | `langagent/protocol/tool_schemas.py` |
| `MiddlewareSpec` | F10 拥有（v0.3.0 s-3 修复后：从 F04 移到 F10） | `langagent/primitives/middleware_spec.py` |
| `ChannelSpec` | F12（v1 预留） | `langagent/protocol/reserved_types/channel.py` |
| `ChannelContext` | F12（v1 预留） | `langagent/protocol/reserved_types/channel.py` |
| `SandboxSpec` | F12（v1 预留） | `langagent/protocol/reserved_types/sandbox.py` |
| `ScheduleSpec` | F12（v1 预留） | `langagent/protocol/reserved_types/schedule.py` |
| `MemorySpec` | F12（v1 预留） | `langagent/protocol/reserved_types/memory.py` |
| `IdentitySpec` | F12（v1 预留） | `langagent/protocol/reserved_types/identity.py` |
| `EvalTaskSpec` | F11（v0.3.0 M-4 修复：expected 类型扩展为 dict；schema_version v0.2.0） | `langagent/eval/task_loader.py` |
| `Span` | F08 | `langagent/cross_cutting/logger.py` |
| `Trace` | F08 | `langagent/cross_cutting/logger.py` |
| `Event` | F07 | `langagent/protocol/event_bus.py` |
| `MetricsSnapshot` | F08 | `langagent/cross_cutting/metrics_collector.py` |
| `AuditEntry` | F09 | `langagent/cross_cutting/audit_recorder.py` |
| `DoctorReport` | F06 拥有（v0.3.0 M-3 修复 + S-2 修复：runtime 改 RuntimeConfigSnapshot） | `langagent/runtime/exit_handler.py` |
| `EvalRunResult` | **F11**（**v0.4.0 M-NEW-1 修复新增**：runner.run() 返回类型；3 字段 frozen dataclass = `eval_report` / `final_state` / `exit_code`；**v0.5.0 评审 v0.1.0 §二.A.1 修复补建 schema 章节**） | `langagent/eval/runner.py` |
| `EvalReport` | F11 | `langagent/eval/report_aggregator.py` |
| **`GuardrailPolicy`** | **F09**（**review.md v2.1.0 P1-4 修复新增**：5 字段 `enabled` / `interrupt_on` / `redact_pii` / `allow_internal_endpoints` / `internal_endpoint_patterns`；承载宪法第 X 条 1 款 + 第 IV 条 4 款对齐——内网 vLLM 默认 allow） | `langagent/cross_cutting/guardrail_middleware.py` |
| **`GuardrailDecision`** | **F09**（**review.md v2.1.0 P1-4 修复新增**：5 字段 `allow` / `interrupt` / `redact` / `reason` / `is_internal_endpoint`） | `langagent/cross_cutting/guardrail_middleware.py` |

合计 **27 个类型**（**v0.3.0 S-2 修复后**：新增 RuntimeConfigSnapshot，22 → 23；**v0.4.0 M-4 方案 C 修复后**：新增 StateReducers，23 → 24；**v0.4.0 M-NEW-1 修复后**：新增 EvalRunResult，24 → 25；**review.md v2.1.0 P1-4 修复后**：新增 GuardrailPolicy + GuardrailDecision，25 → **27**；字段名 `final_state` 已统一），归属唯一 feature → **不重叠**。

### 3. 6 阶段覆盖（6 / 6 = 100%）

| stage | 归属 feature | 实现位置 |
|---|---|---|
| `dir_load` | F02 | `runtime_dir_loader.load()` |
| `config_resolve` | F03 | `runtime_config_resolver.resolve()`（产出 RuntimeConfig.model=None；v0.3.0 S-1） |
| `model_adapt` | F10 | `primitives_chat_model_factory.create()`（仅返回 BaseChatModel） |
| `graph_compose` | F10 | `primitives_state_graph_builder.build(loaded, config, checkpoint)`（checkpoint 显式传入；v0.3.0 S-5） |
| `main_loop` | F05 | `runtime_main_loop_dispatcher.dispatch()`（通过 primitives.langchain_types re-export LangChain 类型；v0.3.0 M-3） |
| `exit_cleanup` | F06 | `runtime_exit_handler.cleanup()`（含 `run_doctor_checks` 4 项 check；v0.3.0 S-3 扩展 API） |

合计 6 阶段全部分配；F10 独占 2 阶段（符合 primitives 层唯一接触 LangChain / LangGraph 的约束）。
**v0.3.0 S-5 修复**：F01 dispatch 严格按 `dir_load → config_resolve → model_adapt → graph_compose → main_loop → exit_cleanup` 编排，并显式调用 `checkpoint_adapter.create()`。

### 4. CLI 子命令覆盖（4 / 4 = 100%）

| 子命令 | 归属 feature |
|---|---|
| `langagent init <name>` | F01（编排，无 --template 参数，**v0.3.0 M-8 修复**）+ F02（`runtime_dir_loader.write_template(name)` 生成模板 + 发射 `la.lifecycle.init.start`；**review.md v3.0.0 P2-5 修复补充**：退出码 67 = `name_already_exists` 由 F02 `write_template()` 触发，当 cwd 下同名目录已存在时；workflow.md §退出码 67 指定唯一触发阶段 = `dir_load`）+ F06（`cleanup(state=None, config=None, *, init_only=True)` 极简分支 + 发射 `la.lifecycle.init.end`，**review.md v2.1.0 P1-2 修复后**：`init.end` 由 F06 在 exit_cleanup 阶段统一发射，F02 仅发 `init.start`） |
| `langagent run [agent-dir]` | F01（编排：`config.with_model(...)` + `checkpoint_adapter.create(...)` + `state_graph_builder.build(..., checkpoint)`）+ F02 + F03 + F10 + F05 + F06 |
| `langagent eval [agent-dir]` | F01（编排：`result = eval_runner.run(agent_dir, *, config, args)` → **`EvalRunResult(eval_report, final_state, exit_code)`**；**review.md v2.2.0 P1-2 + P2-1 修复**：F01 dispatch 入口 resolve config 一次，通过 keyword-only `config` 参数注入 runner；`evals/` 目录不存在 → `EvalRunResult(exit_code=66)` 由 F01 dispatch 走 cleanup 路径返回）+ F02（加载被评测智能体）+ F03（仅类型注解引用 RuntimeConfig，F11 runner 不再内部 resolve）+ F05（每条 task 跑 main_loop，**最后一条 task 的 final_state 传 F06 cleanup**）+ F11（5 种 grader 判定 + EvalReport 聚合；**v0.4.0 M-NEW-1 修复后**：runner 返回 `EvalRunResult` 而非 `int`）+ F06（最终 report 写盘） |
| `langagent doctor` | F01（编排：`DoctorReport.runtime = RuntimeConfigSnapshot.from_runtime_config(config)`，**v0.3.0 S-2**）+ F02（轻量 dir_load）+ F03 + F06（`run_doctor_checks`）+ F10 + F08 |

### 5. MDA 能力覆盖（15 / 15 = 100%）

| mda_capability | 归属 feature |
|---|---|
| agent-definition | F02 + F05 |
| cli | F01 |
| evals | F11（**review.md v1.1.0 P1-3 修复新增**：5 种 grader = `exact_match` / `contains` / `regex` / `llm_judge` / `tool_call_match`；F11 §三.3 实现） |
| identity | F12（v1 预留） |
| instructions | F02 |
| local-development | F02 + F03 |
| mcp-connectors | F04（**v0.3.0 M-2 修复后**：tool_registry 扩展点保留，但 v1 不实现；后续 v2 feature） |
| middleware | F04 + F09 |
| project-structure | F02 + F12 |
| skills | F04 |
| tools | F04 |
| sandboxes | F12（v1 预留） |
| schedules | F12（v1 预留） |
| memory | F12（v1 预留） |
| channels | F12（v1 预留） |

10 个 active 全部落到 F01-F11（agent-definition / cli / evals / instructions / local-development / mcp-connectors / middleware / project-structure / skills / tools）；**5 个 v1 预留（channels / sandboxes / schedules / memory / identity）全部落到 F12**（**review.md v2.0.0 P1-3 修复后**：原 prose "11 active + 4 个 v1 预留" 计数与表格 15 行冲突，统一为 "10 active + 5 个 v1 预留 = 15 项"）。

### 6. 退出码 + 日志标签覆盖

#### 6.1 退出码（13 个）

| 退出码 | 归属 feature | 触发场景 |
|---|---|---|
| 0 / 1 / 2 / 3 / 4 / 5 | F06 `cleanup()` `worst_of()` 仲裁 | 通用 / argparse / JSON / I/O / 字段缺失 |
| 64 / 65 / 66 / 67 / 70 / 78 | F06 + F02 / F03 / F04 / F10 各阶段 | EX_USAGE / EX_DATAERR / EX_NOINPUT / name_already_exists / EX_SOFTWARE / EX_CONFIG |
| 130 | F06 + F05 `run_until_done()` Ctrl-C 捕获 | SIGINT |

> **review.md v0.3.0 M-7 修复**：F06 提供 `worst_of(codes: list[int]) -> int` 函数实现 **13 级**优先级仲裁（**review.md v2.0.0 P1-1 修复后**：v0.5.0 changelog 新增的退出码 67 = `name_already_exists` 已补入 F06 §3.3 优先级表第 3 级；worst_of 函数自动适配）。

#### 6.2 日志标签（≥45 个，review.md v0.3.0 s-1 / s-2 / s-5 修复后归属）

| 标签分类 | 数量 | 发射方 feature（review.md v0.3.0 S-1 / S-2 / S-3 / S-4 修复明确） |
|---|---|---|
| `la.lifecycle.init.start` | 1 | F02 `runtime_dir_loader.write_template()` |
| `la.lifecycle.init.end` | 1 | F06 `runtime_exit_handler.cleanup()`（init-only cleanup 模式，**review.md v2.2.0 P1-1 修复**：`init.end` 触发阶段归属 = `exit_cleanup`，由 F06 在 init 子命令末尾 cleanup 阶段统一发射；F02 §3.5 不再发射 init.end） |
| `la.lifecycle.run.{start, turn, tool_call, tool_result, model_response}` | 5 | F05 `runtime_main_loop_dispatcher.dispatch()` |
| `la.lifecycle.eval.{start, case_done, summary}` | 3 | F11 `eval/runner.run()` / `_run_one_task()` |
| `la.lifecycle.doctor.{check, report}` | 2 | F06 `runtime_exit_handler.run_doctor_checks()` / `cleanup()` |
| `la.runtime.dir_load.{start, ok, fail}` | 3 | F02 `runtime_dir_loader.load()` |
| `la.runtime.config_resolve.{start, priority_merge, ok, fail}` | 4 | F03 `runtime_config_resolver.resolve()` |
| `la.runtime.model_adapt.{start, endpoint_probe, ok, fail}` | 4 | **F10 `primitives_chat_model_factory.create()`**（review.md v0.3.0 S-1 修复明确） |
| `la.runtime.graph_compose.{start, middleware_bind, tool_bind, ok, fail}` | 5 | **F10 `primitives_state_graph_builder.build()`**（review.md v0.3.0 S-1 修复明确） |
| `la.runtime.main_loop.{start, turn.start, turn.end, model_call, tool_call, tool_result, end}` | 7 | F05 `runtime_main_loop_dispatcher.dispatch()` |
| `la.runtime.exit_cleanup.{start, checkpointer_close, report_write, audit_flush, ok, fail}` | 6 | F06 `runtime_exit_handler.cleanup()` |
| `la.cross_cutting.guardrail.block` | 1 | F09 `cross_cutting_guardrail_middleware.evaluate()` |
| `la.cross_cutting.audit.write` | 1 | F09 `cross_cutting_audit_recorder.write()` |
| `la.cross_cutting.metrics.emit` | 1 | F08 `cross_cutting_metrics_collector.snapshot()` |
| `la.cross_cutting.event_handler_error` | 1 | F07 `protocol_event_bus.publish()` 异常隔离时（通过 F08 logger.emit） |
| `la.tool.suspicious_missing_side_effects` | 1 | F04 `protocol_tool_registry.register_all()`（**review.md v0.1.0 R-001 修复新增**：tool 静态属性警告走 logger 路径；F08 `ALLOWED_TAGS` 集合 45 → 46） |
| **合计** | **46** | **F02 / F03 / F04 / F05 / F06 / F07 / F08 / F09 / F10 / F11 共 10 个 feature 直接发射；F08 还提供 `emit()` 接口 + 白名单校验（46 项登记）** |

> **review.md v0.3.0 s-5 修复明确**：
> - **CLI 层严禁直接发射任何 `la.*` tag**（architecture_modules.md#mod-cli-parser 硬约束：`× cross_cutting_logger`）。
> - F01 仅作为入口编排，`langagent init/run/eval/doctor` 启动后用户可观测到上述 tag 由各 feature  按阶段发射；F01 dispatch 不直接 import `cross_cutting_logger`。
> - **F08 logger 是 46 项 log tag 白名单的权威契约定义方**（**review.md v3.0.0 P1-2 修复**）：`ALLOWED_TAGS` 集合 ≥**46**（**review.md v0.1.0 R-001 修复后**：原 45 项 + 新增 `la.tool.suspicious_missing_side_effects` 1 项）；F02/F03/F04/F05/F06/F07/F09/F10/F11 共 9 个 feature 是消费方，各 feature `test_*_log_tags_in_whitelist` 测试仅断言"本 feature 发射的 tag 在白名单中"，**不约束白名单本身内容**（白名单由 F08 唯一维护）。所有 10 个发射方 feature 通过 `from langagent.cross_cutting.logger import emit` 调用。
>
> **review.md v0.3.0 S-6 修复**：所有日志走 stderr（文本 + JSONL 双格式）；stdout 仅对话内容。

### 7. 宪法硬约束覆盖

| 宪法条款 | 归属 feature |
|---|---|
| 第 I 条 项目身份与边界 | F01（CLI）+ F13（打包） |
| 第 II 条 技术栈与依赖范围 | F10（primitives 层 LangChain / LangGraph 封装）+ `primitives_langchain_types`（v0.3.0 M-3 修复） |
| 第 III 条 LangSmith 剥离原则 | F10（不依赖 LangSmith）+ F08（不写 LangSmith tag）+ F13（spec excludes） |
| 第 IV 条 模型抽象层 | F10（6 种 provider，无硬编码 base_url，**v0.3.0 S-4 修复**）+ F03（model_base_url=None，**v0.3.0 M-1 修复**） |
| 第 V 条 智能体目录契约 | F02（layout 校验 + .env.example 占位符 + stage_guard monkeypatch + audit_hook 混合方案，**v0.3.0 S-6 修复**）+ F04 + F12 |
| 第 VI 条 Agent Loop 与 State | F05（main_loop dispatcher 通过 primitives.langchain_types re-export，**v0.3.0 M-3**）+ F10（StateGraph 构造） |
| 第 VII 条 Middleware 与工具规则 | F04（tool 注册 + ToolSideEffect）+ F09（guardrail middleware） |
| 第 VIII 条 TDD 刚性约束 | 所有 feature 的 prompt 都明确"先 Red 后 Green 再 Refactor" |
| 第 IX 条 质量诊断能力矩阵 | F08（tracing + monitoring + EventBusProtocol 接口）+ F11（evaluation + testing）+ F09（guardrails） |
| 第 X 条 安全与隐私 | F09（guardrail + AuditEntry 3 类事件） |
| 第 XI 条 打包与分发 | F13（PyInstaller） |
| 第 XII 条 配置与可观测契约 | F03（优先级链 + 占位符校验 **v0.3.0 m-5** + RuntimeConfig.with_model **v0.3.0 S-1**）+ F08（Span 7 字段） |
| 第 XIII 条 禁止项 | 所有 feature prompt 强制引用；v0.3.0 S-4 修复 base_url 硬编码 |
| 第 XV 条 顶层设计优先 | 每个 feature prompt 顶部"MUST 先读三份顶层设计 artefact" |

---

## 四、Feature 提示词索引

| feature_id | 文件 | 一句话定位 |
|---|---|---|
| F01 | `01_cli入口与子命令分发.md` | 把 argv 翻译成 4 个子命令并接入 6 阶段调度（v0.3.0 修复：init 无 --template；run 显式 checkpoint_adapter.create；**v0.4.0 M-NEW-3 修复**：la.cli.* → la.lifecycle.*；**v0.4.0 M-NEW-1 修复**：eval dispatch 接 EvalRunResult；**v0.3.0 M-2 修复**：stdout/stderr 语义分离 + 新增 format_chat_message / format_*_stdout 3 个 stdout API；**review.md v1.0.0 P0-1 修复**：doctor probe 工厂从 F01 移到 F05 `build_doctor_probes()`，恢复 CLI × primitives 黑名单约束） |
| F02 | `02_智能体目录加载.md` | 校验宪法第 V 条布局 + stage_guard monkeypatch+audit_hook 混合方案（v0.3.0 M-9 + S-6）+ 产出 `LoadedAgent` + **v0.4.0 M-NEW-5 模板 5 字段 AgentState 修复** + **v0.4.0 m-NEW-7 占位符统一 `<your-...>`** |
| F03 | `03_配置解析.md` | CLI > 环境变量 > .env > 内置默认 优先级链合并 + 占位符校验（v0.3.0 m-5 + **v0.4.0 m-NEW-7 统一 `<your-...>`**）+ RuntimeConfig.model=None + with_model（v0.3.0 S-1） |
| F04 | `04_protocol层skill与tool加载.md` | 扫描 skills/ 与 tools/ 产出 SkillSpec / ToolSpec（v0.3.0 M-2 移除 MCP 预留）+ **v0.4.0 m-NEW-2 未声明 SIDE_EFFECTS 警告日志** + **v0.4.0 m-NEW-3 args_schema JSON Schema Draft 7** + **v0.4.0 m-NEW-10 tool_id 异常传播路径** |
| F05 | `05_react主循环.md` | 驱动 LangGraph CompiledStateGraph 跑 ReAct（v0.3.0 M-3 通过 primitives.langchain_types re-export）+ **v0.4.0 M-4 方案 C reducer 从 primitives.state_reducers import** + **v0.4.0 M-NEW-3 log tag rename** |
| F06 | `06_退出清理.md` | 关闭 checkpointer + 写出 Span / Event / 报告 + 5 参 cleanup API（v0.3.0 S-3；**v0.5.0 评审 v0.1.0 §二.A.2 修正**：原 prose 误写 6 参）+ worst_of 仲裁（v0.3.0 M-7）+ RuntimeConfigSnapshot（v0.3.0 S-2）+ **v0.4.0 M-NEW-4 §3.6.1 步骤失败 continue-on-failure 显式化** |
| F07 | `07_event总线.md` | protocol_event_bus pub/sub + flush(timeout=5)（v0.3.0 M-5）+ publish_async（v0.3.0 m-1） |
| F08 | `08_横切层日志与指标.md` | la.* 日志走 stderr（v0.3.0 S-6 + **v0.4.0 m-NEW-8 emit() 强制 stderr**）+ MetricsSnapshot 聚合 + EventBusProtocol 接口（v0.3.0 m-2）+ **v0.4.0 M-NEW-3 log tag rename** |
| F09 | `09_横切层审计与护栏.md` | AuditEntry 写入 + ToolSideEffect → interrupt（v0.3.0 M-3 通过 primitives.langchain_types 导入 AgentMiddleware）+ **v0.4.0 m-NEW-2 未声明 SIDE_EFFECTS fail-CLOSED 默认** |
| F10 | `10_primitives层封装.md` | 6 种 model_provider（无硬编码 base_url，v0.3.0 S-4）+ StateGraph 编译 + checkpointer + primitives_langchain_types re-export（v0.3.0 M-3）+ **v0.4.0 M-4 方案 C 新增 primitives_state_reducers 模块** + **v0.4.0 M-NEW-2 硬例外单向边 primitives → cross_cutting_logger** + **v0.4.0 m-NEW-6 importlib 强化** |
| F11 | `11_eval子系统.md` | EvalTaskSpec 加载 + 5 种 grader + EvalReport（3 相位开发，v0.3.0 M-6）+ eval_runner 归属明确（v0.3.0 M-4）+ **v0.4.0 M-NEW-1 runner 返回 EvalRunResult(eval_report, final_state)** + **v0.4.0 m-NEW-1 args: dict 类型** + **v0.4.0 M-NEW-3 log tag rename** + **v0.4.0 m-NEW-9 grader_extensibility 用途澄清** |
| F12 | `12_v1预留接口.md` | 6 个 v1 预留 schema 类型 stub |
| F13 | `13_打包与分发.md` | PyInstaller 单文件二进制 + wheels 离线包 + **v0.4.0 m-NEW-5 hiddenimports 扩展 langchain_core 等基础包** |

---

## 五、变更日志

| 日期 | 版本 | 修订摘要 | 作者 |
|---|---|---|---|
| 2026-09-15 | v0.1.0 | 初版：13 个 feature 排序表 + 覆盖度验证 + 提示词索引 | 项目维护者 |
| 2026-09-15 | v0.2.0 | 修复 review.md v0.1.0 中 4 个严重问题 + 5 个中等问题 + 7 个轻微问题（详见 review.md §六）：<br>- M-1：F01 dispatch 顺序按 6 阶段编排<br>- M-2：`chat_model_factory.create()` 统一为 `BaseChatModel` 返回值；RuntimeConfig 重建由 F01 `with_model` 完成<br>- M-3：doctor 4 项 check 归 F06（方案 C），保留 13 个 feature 不变<br>- M-4：`EvalTaskSpec.expected` 扩展接受 `dict`，schema_version v0.2.0<br>- m-1：`stage_guard.py` 由 F02 首批实现，F03/F05/F06 复用<br>- m-2：`architecture_modules.md` 模块数 15 → 17<br>- m-3：`skills/` / `tools/` / `middleware/` 从必填改为布局约定可缺失<br>- m-4：F06 顶部 metadata 补加 F05 依赖与数据流说明<br>- m-5：F07 Event 总线约束措辞加 cli 层例外<br>- s-1：README 批次图简化（F08 单点出现，注释说明内部相位）<br>- s-2：README §"说明" 顺序调整，F12 特殊性前置<br>- s-3：`MiddlewareSpec` 从 F04 移到 F10<br>- s-4：README CLI 子命令覆盖表扩写依赖链<br>- s-5：F13 pyinstaller 锁定版本 + 离线安装测试<br>- s-6：workflow.md 新增 `la.cross_cutting.event_handler_error` 日志标签<br>- s-7：F02 `.env.example` 去除 `localhost`，用 `<your-...>` 占位符 | 评审者 |
| 2026-09-15 | v0.3.0 | 修复 review.md v0.1.0 中第二轮评审识别的 6 个严重 + 9 个中等 + 6 个轻微问题（详见 review.md §六）：<br>- **S-1**：module_schemas.md RuntimeConfig.model 改 `BaseChatModel \| None = None`，新增 `with_model()` / `with_model_base_url()` 方法 + 占位符校验<br>- **S-2**：module_schemas.md 新增 `RuntimeConfigSnapshot` schema（1 级章节 3 / 20）；DoctorReport.runtime 改 Snapshot；章节总数 19 → 20、类型 22 → 23<br>- **S-3**：F06 `cleanup()` API 扩展为 6 参（keyword-only doctor_report / eval_report / metrics_snapshot）<br>- **S-4**：F10 deepseek / zhipu base_url 去硬编码（改 env DEEPSEEK_BASE_URL / ZHIPUAI_BASE_URL）；F03 §3.4 表与 F02 .env.example 同步<br>- **S-5**：F01 `langagent run` dispatch 补 `checkpoint_adapter.create(config)` 步骤；F10 §3.3 / §3.1 同步 `checkpoint` 显式参数<br>- **S-6**：F08 stdout/stderr 输出修正（日志走 stderr 含文本 + JSONL；stdout 仅对话）；F08 §3.4 + §4.1 测试同步<br>- **M-1**：F03 model_base_url 内置默认改 None；openai-compatible 必填校验<br>- **M-2**：删除 F04 MCP 预留小节；v1 不实现 MCP<br>- **M-3**：F10 新增 `primitives_langchain_types` 模块（review.md v0.3.0 M-3 修复后 primitives 层 17 → 18 模块）；F05 / F08 / F09 通过该模块 re-export 导入 LangChain / LangGraph 类型<br>- **M-4**：F01 §3.1 补 `eval_runner` 归属说明（F11 实现）；architecture_modules.md 模块清单脚注新增 `eval_runner`<br>- **M-5**：F07 §3.1 关键 API 表补 `flush(timeout=5.0)`；F06 §3.3 关闭顺序第 1 步调用 `flush(timeout=5)`<br>- **M-6**：F11 内部 3 相位（Phase 1 task_loader+report_aggregator；Phase 2 5 graders；Phase 3 runner 整合）<br>- **M-7**：F06 §3.3 退出码优先级表正式化（12 级 + `worst_of` 仲裁函数 + `langagent/runtime/exit_code.py` 模块）<br>- **M-8**：F01 init 子命令删除 `--template` 参数；F02 §3.5 write_template() 不接收 template 参数<br>- **M-9**：F02 stage_guard 实现方案明确：`sys.addaudithook` + 阶段级黑名单；新增 `stage_guard_audit.py` 模块<br>- **m-1**：F07 §3.1 补 `publish_async` API<br>- **m-2**：F08 新增 `cross_cutting_event_bus_protocol` 模块；EventBusProtocol 接口定义；依赖反转<br>- **m-3**：F02 §3.5a 模板 agent.py 内容示例（明确 `agent` 变量名）<br>- **m-4**：F07 §4.1a `ALLOWED_EVENT_TYPES` 完整性测试（≥13 项含 event_handler_error）<br>- **m-5**：F03 §3.4 占位符校验（`<your-...>` 命中抛 ConfigPlaceholderError）+ §4.3 测试<br>- architecture_modules.md 模块清单：15 → 17 → 18（含 primitives_langchain_types）；依赖矩阵 18×18；模块到 Feature 映射表新增 primitives_langchain_types / primitives_state_graph_builder 依赖 langchain_types 类型注解<br>- module_schemas.md：RuntimeConfig schema_version v0.1.0 → v0.2.0；新增 RuntimeConfigSnapshot；DoctorReport 改 RuntimeConfigSnapshot；EvalReport 章节编号 19 → 20 | 评审者 |
| 2026-09-15 | v0.3.0 / review.md v0.2.0 同步 | 本轮 review.md v0.2.0 修复（7 中等 + 8 轻微），README.md 同步对齐：<br>- **M-6 同步**：§一 F11 依赖列由 `F01 / F02 / F05 / F06` 改为 `F01 / F02 / F05 / F06（**完整 F11 依赖**；Phase 1（task_loader + report_aggregator）无运行时依赖，可与 F04 / F07 / F08 并行启动）`；§二 推荐批次表第 9 批 F11 行末尾加注："**Phase 1 可提前到第 5 批启动**；Phase 2 在第 7 批；Phase 3 在第 9 批"<br>- **M-7 同步**（**v0.5.0 评审 v0.1.0 修复中删除**）：原计划在 §三.1 模块覆盖表增加 `cross_cutting_event_bus_protocol` 行；v0.5.0 评审决定合并方案 A（EventBusProtocol 接口并入 `cross_cutting_logger`），本条同步撤销<br>- **M-1 同步**（隐含）：§三.1 LoadedAgent schema 字段数 = 6 与 module_schemas.md#schema-loaded-agent 对齐（review.md v0.1.0 即已正确） | 项目维护者 |
| 2026-09-15 | v0.4.0 / review.md v0.3.0 同步 | 本轮 review.md v0.3.0 修复（5 中等 + 10 轻微），README.md 同步对齐顶层设计 v0.4.0：<br>- **M-NEW-3 同步**：§三.6.2 日志标签表 12 项 `la.cli.*` 全部 rename 为 `la.lifecycle.*`（按用户视角 CLI 生命周期重新组织命名空间）；§一 概述 + §四 提示词索引同步更新<br>- **M-NEW-2 同步**：§三.1 模块覆盖表增加 `primitives_chat_model_factory → cross_cutting_logger` + `primitives_state_graph_builder → cross_cutting_logger` 2 条硬例外单向边（review.md v0.4.0 M-NEW-2 方案 B 修复后登记；architecture_modules.md 依赖矩阵带 →¹ 标记；CHK-AR-021 校验单向性）<br>- **M-4 方案 C 同步**：§三.1 模块覆盖表增加 `primitives_state_reducers | F10`（reducer 函数从 F05 runtime 层下沉到 primitives 层）；§三.2 schema 覆盖表增加 `StateReducers`；合计行改"合计 19 个模块 + 24 个类型"<br>- **M-NEW-1 同步**：§三.4 CLI 子命令覆盖表 `langagent eval` 行增加 `EvalRunResult(eval_report, final_state, exit_code)` 返回类型；§四 提示词索引 F11 定位更新<br>- **M-NEW-4 同步**：§一 F06 概述 + §四 提示词索引 F06 定位增加"§3.6.1 步骤失败 continue-on-failure 策略显式化"标注<br>- **m-NEW-2 同步**：§四 F04 / F09 定位更新（未声明 SIDE_EFFECTS 双层防御：F04 日志层 fail-OPEN + F09 决策层 fail-CLOSED）<br>- **m-NEW-5 / m-NEW-7 / m-NEW-8 等**：§四 提示词索引 F02 / F08 / F10 / F11 / F13 定位更新<br>- **后续工作**：review.md v0.4.0 同步修复所有 v0.3.0 → v0.4.0 修复的 issue 状态 | 项目维护者 |
| 2026-09-15 | v0.5.0 / review.md v0.1.0（feature 评审）同步 | 本轮 review.md v0.1.0 评审识别 3 严重 + 10 中等 + 15 轻微，本 README.md + 顶层设计三件套同步对齐：<br>- **§二.A.1 修复**（P0）：EvalRunResult 字段统一（`eval_report` / `final_state` / `exit_code`）；字段名 `last_state` → `final_state`；F01 §3.4 行 130-132 eval dispatch 伪代码重写（走 `exit_handler.cleanup()` 统一路径）；module_schemas.md 新增 `## EvalRunResult {#schema-eval-run-result}` 章节（1 级章节 20 / 22，schema 总数 24 → **25**）；README §三.2 schema 覆盖表补 `RuntimeConfigSnapshot` + `EvalRunResult` 2 行；合计改 25<br>- **§二.A.2 修复**（P1）：F06 `cleanup()` "6 参" → "5 参（2 positional + 3 keyword-only）"（README.md:41 / 268 + F06 行 30 / 249 共 4 处统一）<br>- **§二.A.3 修复**（P0，方案 A）：`cross_cutting_event_bus_protocol` 模块删除，EventBusProtocol 接口定义合并入 `cross_cutting_logger` 模块；模块总数仍为 19（cross_cutting 层 5 → 4）；architecture_modules.md `#mod-cross-cutting-logger` 章节追加 EventBusProtocol 接口定义职责；F08 §3.1 / F07 §3.1 / F08 §5-8 同步<br>- **§三.B.1 修复**（P1）：README §三.6.2 表 `la.lifecycle.run.*` 计数 6 → 5；F05 §3.5.2 prose 6 → 5；总数 45 vs 46 算式一致<br>- **§三.B.7 修复**（P2）：F10 §3.1 + module_schemas.md §schema-state-reducers "4 个 reducer 函数" → "3 个唯一 reducer 函数覆盖 4 个自定义字段"<br>- **§三.B.8 修复**（P2）：F08 §一 "F08 不依赖任何上层" → "F08 不依赖任何业务层（cli / runtime / protocol），仅依赖 primitives 层类型注解（F10）与 F07 事件总线实现（metrics 子模块消费）"<br>- **§三.B.10 修复**（P2）：F01 §3.4 行 119 "共 13 个 tag" → "共 12 个 tag；另 1 个 la.cross_cutting.guardrail.block 由 F09 发射，F05 仅在 GraphInterrupt 时转发捕获"<br>- **§四.C-1~C-8 修复**：workflow.md metadata 表 v0.1.0 → v0.5.0 / 2026-09-14 → 2026-09-15；workflow.md §"main_loop stage_capability_violation" 命名空间归属显式声明；workflow.md 新增退出码 67 = `name_already_exists`；CHK-AR-006 数 15 → 19；cli_runner 依赖表补 `eval_runner`；module_schemas.md 章节编号同步 22/25<br>- **§四.C-9 修复**：README.md "rename" 措辞改 "v0.4.0 起 `la.lifecycle.*` 取代 v0.3.0 的 `la.cli.*` 命名空间"<br>- **§四.C-11 修复**：README.md changelog 行末尾残留的 "" 工具截断标记删除 | 评审者 |
| 2026-09-15 | v1.2.0 / review.md v1.1.0（feature 评审）同步 | 本轮 review.md v1.1.0 评审识别 6 P0 + 9 P1 + 11 P2 = 26 项问题，本 README.md + 13 份 feature prompt + 顶层设计三件套同步对齐：<br>- **P0-1 修复**：F07 §3.1 新增 `drain_events()` API + §3.3 drain 语义段 + §4.1b 6 个测试；F08 §3.1 新增 `drain_spans()` API + §3.2 schema Span 注释补 buffer + §4.1b 6 个测试；F06 §3.3 step 6 拆分 6.1-6.4 + write_reports 新增 `spans` / `events` 2 个 positional 参数 + §3.6 数据流图同步 + §3.6.1 失败处理细分。data flow 断链修复：F06 cleanup 现在能拿到累积 Span / Event 写到 `logs/<run-id>.jsonl`<br>- **P0-2 修复**（方案 B）：`LoadedAgent.compiled_graph` 字段**删除**；F02 §3.2 / F10 §3.1 / F01 §3.4 / F06 §3.2 + `module_schemas.md#schema-loaded-agent` 同步；`schema_version` v0.1.0 → **v0.2.0**；F01 dispatch 独立持 LoadedAgent + CompiledStateGraph 两个变量<br>- **P0-3 + P0-5 修复**：F07 / F08 / F09 / F10 / F11 五处 prompt header 批次标注与 README §二 推荐批次表对齐；F10 §一 依赖列补 F08 Phase 1（cross_cutting_logger.emit() + ALLOWED_TAGS + 硬例外单向边 →¹）<br>- **P0-4 修复**：F11 runner.run() 内部 RuntimeConfig 来源明确（`config = config_resolver.resolve(args['cli_args'], agent_dir)`）；F11 §三 依赖列补 F03；F11 §四 TDD 新增 `test_runner_resolves_config_from_args_cli_args_dict` + `test_runner_uses_resolved_config_for_llm_judge`<br>- **P0-6 修复**：F07 §3.4 标题"≥12 种" → "≥13 种，含 `event_handler_error`"<br>- **P1-1 修复**：F07 §六 补"不实现 `emit()` 日志发射接口（→ F08 cross_cutting_logger；F07 仅通过 `from langagent.cross_cutting.logger import emit` 调用）"<br>- **P1-2 修复**：F11 §3.2 exit_code 含义 1 款改写（澄清 F11 runner 不发 `la.cross_cutting.metrics.emit` 日志——该 tag 由 F08 metrics_collector 拥有；F11 在 task 失败时改发 `la.cross_cutting.event_handler_error` 日志）<br>- **P1-3 修复**：README §三.5 evals 行扩展"5 种 grader = exact_match / contains / regex / llm_judge / tool_call_match"<br>- **P1-4 + P2-6 修复**（合并）：F05 §3.5.2 guardrail_block 表最后一行细化"F09 直接发，F05 不重发；F05 行为分流：run 抛 HitlInterruptedError / eval 记录 guardrail_blocked=True"<br>- **P1-7 修复**：F03 §3.5 / F05 §3.4 / F06 §3.5 阶段能力边界补"F0X 阶段级黑名单引用 F02 §3.4 阶段级黑名单表"<br>- **P1-8 修复**：F08 §3.3 拆分 §3.3.1 logger 行为 + §3.3.2 tag 发射方归属表（澄清 logger 仅被动接口，不持有 tag 发射逻辑）<br>- **P1-9 修复**：F13 §3.6 标题改"LangAgent 主程序构建产物的 include / exclude 清单"；明确两类 `pyproject.toml`（主程序 vs 智能体目录）<br>- **P2-1 修复**：F02 §3.5a 模板 AgentState scratchpad 字段补 `Annotated[]` 注解（避免 mypy --strict 抓 typo）<br>- **P2-3 修复**：F08 §4.1 补 3 项脱敏测试（`test_emit_does_not_contain_password` / `_secret` / `_token`）<br>- **P2-4 修复**：README §三.2 schema 覆盖表 4 行 F04 schema 补具体文件路径（`skill_schemas.py` / `tool_schemas.py`）<br>- **P2-5 修复**：F11 §4.2 补 `test_tool_call_match_grader_runtime_validator_fallback`（schema validator 漏过时的 grader runtime 兜底）<br>- **P2-7 修复**：F06 §3.3 退出码优先级表行 7（退出码 5）备注补"5 是 schema 层面——RuntimeConfig 必填字段缺失 / 类型不匹配 schema；与 78 配置源层面区分"<br>- **P2-8 修复**：F02 §4.1 补 4 项 v1 预留目录缺失合法测试（`test_validate_layout_missing_channels_dir_returns_ok` / `_identity_file` / `_memory_file` / `_sandbox_dir`）<br>- **P2-9 修复**：F13 §3.2 hiddenimports 注释明确"F10 实际安装后通过 `pip show langchain` / `pip show langgraph` 确认实际模块路径"<br>- **P2-10 修复**：F01 §4.2 第 6 项测试改写为 `test_dispatch_eval_returns_cleanup_exit_code`（验证 dispatch 不读 `result.exit_code` 字段，统一走 cleanup 路径）<br>- **P2-11 修复**：F11 §3.3 tool_call_match 行备注补双层校验（schema validator + grader runtime validator）<br>- **顶层设计三件套同步**：workflow.md / architecture_modules.md / module_schemas.md 主版本号同步 v0.5.0/v0.4.0 → **v1.2.0**；metadata 表 / LoadedAgent 字段数 / F10 build() 描述 / cross_cutting_event_bus_protocol 删除记录全部对齐 | 评审者 || 2026-09-15 | v2.0.0 / review.md v2.0.0（feature 评审二次）同步 | 本轮 review.md v2.0.0 评审识别 1 P0 + 3 P1 + 4 P2 = 8 项问题（review.md v1.2.0 全部 26 项修复已应用基础上的二次评审），本 README.md + 顶层设计三件套 + 3 份 prompt 同步对齐：<br>- **P0-1 修复**：module_schemas.md 6 个 v1 预留 schema preamble 元数据补 "**Owning Feature: F12**" + "**Python 文件: `langagent/protocol/reserved_types/<n>.py`**"（ChannelSpec / ChannelContext / SandboxSpec / ScheduleSpec / MemorySpec / IdentitySpec 共 6 处）<br>- **P1-1 修复**：F06 §3.3 退出码优先级表补 67 = name_already_exists（priority 3，在 70 与 66 之间）；原 12 级 → 13 级；README §三.6.1 heading "12 个" → "13 个"；prose "12 级" → "13 级"<br>- **P1-2 修复**：F11 prompt §三 header 区分"接口契约依赖"（args dict schema，无 import）vs "模块 import 依赖"（F02 / F03 / F05 / F10）；README §一 F11 行补 prose 注释明确 F01 仅接口契约依赖<br>- **P1-3 修复**：README §三.5 prose "11 active + 4 个 v1 预留" → "10 active + 5 个 v1 预留 = 15 项"（与表格 15 行一致）<br>- **P2-1 修复**：F13 §一 header "第 10 批" → "第 9 批"（与 README §二 推荐批次表对齐）<br>- **P2-2 复核**：本项原报告"README changelog line 316 + line 320 末尾 '' 标记"——经核实系 read 工具输出显示截断标记（v0.5.0 §四.C-11 已修复清理），**非文件实际内容**；P2-2 撤销，无需修复<br>- **P2-3 修复**：F13 §一 header 澄清 "langagent.eval.runner 由 PyInstaller AST 静态分析自动发现（lazy import 在 function body 内被 AST 追踪），不需在 §3.2 hiddenimports 显式列出"；§3.2 spec 加注释行说明<br>- **P2-4 同步**：本 v2.0.0 changelog 行追加（即本行）<br>- **顶层设计三件套 + 3 份 prompt 同步**：module_schemas.md（v1.2.0 → v2.0.0 metadata 表同步）/ 06_退出清理.md（F06 §3.3 退出码优先级表扩 13 级）/ 11_eval子系统.md（F11 §三 header 依赖列区分两类）/ 13_打包与分发.md（F13 §一 header 批次 + hiddenimports 澄清）<br>- **README 主版本号同步 v1.2.0 → v2.0.0** | 评审者 |
| 2026-09-15 | v2.1.0 / review.md v2.1.0（feature 评审三）同步 | 本轮 review.md v2.1.0 评审识别 2 P0 + 4 P1 + 8 P2 + 4 P3 = 18 项问题，本 README.md + 13 份 feature prompt + 顶层设计三件套同步对齐：<br>- **P0-1 修复**：F02 与 F03 批次冲突 — F03 依赖 F02 `stage_guard.py` 公开 API 但 README 把两者并入第 5 批；批次图 `[F04] → [F02 / F03 并行]` → `[F04] → [F02] → [F03]`（review.md §二.P0-1 修复）；F02 §一 批次改"第 5 批 a" + F03 §一 批次改"第 5 批 b" + F03 依赖列补 F02 stage_guard 显式说明<br>- **P0-2 修复**：F05 §3.2 AgentState `scratchpad` 字段 Annotated 语法错误（多 1 个 `]` 与 1 个 `,`）— 修订为 `Annotated[dict[str, Any], replace_with_merge]` 与 F02 §3.5a 已修版本对齐；避免 LangGraph reducer 注入失败<br>- **P1-2 修复**：`la.lifecycle.init.end` 触发阶段归属对齐 — F02 §3.5 仅发射 `init.start`，`init.end` 由 F06 `cleanup()` 在 exit_cleanup 阶段统一发射；F01 init dispatch 末尾调 `exit_handler.cleanup(state=None, config=None, *, init_only=True)` 走极简分支；F06 §3.3 关闭顺序 step 10 新增 `init.end` 发射 + init-only cleanup 模式说明；F01 §八 边界段 F02/F06 行同步<br>- **P1-3 修复**：F01 eval dispatch config 来源 — F01 dispatch 入口 resolve config 一次，传 `eval_runner.run(agent_dir, *, config=config, args=args)` 与 `exit_handler.cleanup(...)`；F11 runner 签名改为 keyword-only `config` 参数（不再内部 resolve）；F11 §四 TDD 改写 `test_runner_accepts_config_as_keyword_arg` + `test_runner_uses_injected_config_for_llm_judge`<br>- **P1-4 修复**：GuardrailPolicy / GuardrailDecision 进顶层 schema 清单（25 → 27）— module_schemas.md 新增 `## GuardrailPolicy / GuardrailDecision {#schema-guardrail-policy}` 章节（1 级章节 23 / 23，承载 2 个类型）；RuntimeConfig 增 `guardrail_policy: GuardrailPolicy | None = None` 字段（schema_version v0.2.0 → v0.3.0）+ `with_guardrail_policy()` 方法；RuntimeConfigSnapshot 增 `guardrail_allow_internal_endpoints` 字段（schema_version v0.1.0 → v0.2.0）；F03 §三.4 配置项表增 1 行 + 读 env LANGAGENT_GUARDRAIL_* 注入；F09 §3.2 修订：GuardrailPolicy 不再仅作 cross_cutting 内部 Pydantic 模型，进顶层 schema；README §三.2 schema 覆盖表新增 2 行合计 27<br>- **P1-5 修复**：F06 §3.3 step 5 + 6.1 `metrics_collector.snapshot()` 重复 — 合并为单次 snapshot（输出同时用于 write_reports + worst_of 输入）；关闭顺序 11 步结构重排<br>- **P1-1 撤销**：README §三.7 第 VIII 条**已独立成行**（line 284）— review.md 原报告误判，无需修复<br>- **P2-2 修复**：F03 §三.4 `model_base_url` 优先级键名按 provider 分流（`openai-compatible` → `MODEL_BASE_URL` / `deepseek` → `DEEPSEEK_BASE_URL` / `zhipu` → `ZHIPUAI_BASE_URL` / 其它 → provider 自带）<br>- **P2-3 修复**：F08 §5 关键约束 7 项新增"被动接口约束"（logger + EventBusProtocol 是被动接口；metrics_collector 订阅是被动消费者）<br>- **P2-4 修复**：F11 §3.1 表格下方加注"5 graders 模块不计入 19 module_id 计数；与 eval_runner 同属 F11 跨 runtime/cli 整合模块"<br>- **P2-6 修复**：F13 §3.2 hiddenimports 注释修订（消除两个 `langchain.agents.middleware` 重复）<br>- **P2-8 修复**：F02 §3.4 prose 简化（原长句拆分为 3 个子句 + 缩进项目符号）<br>- **P3-1 修复**：F01 §3.5 表 `langagent doctor` 4 项全 ok / 仅 warn 行加注"warn 不影响退出码"<br>- **P3-2 修复**：F10 §六 第 6 项 prose 补充"F10 §3.3.1 9 个阶段 tag 发射走 F08 cross_cutting_logger.emit() 接口；F10 不持有 logger 实现"<br>- **P3-4 修复**：README §二 推荐批次表下方加"本批测试数汇总"表（F01 ≥39 / F02 ≥37 / F03 ≥20 / F04 ≥20 / F05 ≥33 / F06 ≥41 / F07 ≥27 / F08+Phase2 ≥31 / F09 ≥20 / F10 ≥42 / F11 ≥49 / F12 ≥15 / F13 ≥14，合计 ≥390）<br>- **顶层设计三件套同步**：module_schemas.md / architecture_modules.md / workflow.md 主版本号同步升至 v2.1.0 | 评审者 |
| 2026-09-16 | **v2.2.0 / review.md v2.2.0（feature 评审四）同步** | 本轮 review.md v2.2.0 评审识别 **6 P1 + 10 P2 + 5 P3 = 21 项问题**，**无 P0**；本 README.md + 13 份 feature prompt + 顶层设计三件套同步对齐。详见 `harness/feature/review.md` §六：<br>- **P1-1**：README §三.6.2 表 `la.lifecycle.init.end` 发射方 = F06（v2.1.0 P1-2 修复后未同步主表，本修复补）<br>- **P1-2**：README §一 F11 行 依赖列改"F11 runner 不再 resolve config"（与 F11 prompt §一 + §三.1 + §八 一致）<br>- **P1-3**：README §一 F10 行 改"硬例外单向依赖 F08 Phase 1"（消除"依赖（无）"歧义）<br>- **P1-4**：README §一 F13 行 改"PyInstaller AST 自动发现 F11 runner"（与 F13 §3.2 实装一致）<br>- **P1-5**：F11 §3.1 重复标题删除 1 个<br>- **P1-6**：F13 §3.2 excludes 列表扩展 5 个 LangSmith 集成路径<br>- **P2-1**：F01 §3.5 表 + README §三.4 表 `evals/` 不存在 → 66（与 workflow.md 对齐）<br>- **P2-2**：F01 §3.5 加 1 行引用 F06 §3.3 退出码仲裁链路<br>- **P2-3**：F03 §3.4 guardrail_policy 默认值补全 5 字段（与 module_schemas.md 一致）<br>- **P2-4**：F04 / F10 加 sys.modules 清理策略段（含 F06 进程退出兜底扫描）<br>- **P2-5**：F05 §3.4 补"读 .env 触发 guardrail.block"（与 workflow.md §四.C-6 一致）<br>- **P2-6**：F11 §一 / §3.1 / §六 增补 event_bus 接口契约（eval_task_started / eval_task_done）<br>- **P2-7**：F09 §3.4 表补 `ToolSpec.requires_approval == True` 决策行（真正 fail-CLOSED 落地点）<br>- **P2-8**：F10 §3.4 6 种 provider 统一从 `RuntimeConfig.model_base_url` 读 base_url（消除 deepseek/zhipu 与 openai-compatible 优先级不一致）<br>- **P2-9**：F01 §3.4 eval dispatch 伪代码补 args dict 显式构造（避免 F11 跨层 import F01 CliArgs）<br>- **P2-10**：F12 §4.4 补 3 项交叉验证测试（v1 预留类型与 dir_load / AgentState / yaml roundtrip 协同）<br>- **P3-1**：F01 §3.5 表 doctor 行补 skipped 状态语义（不影响 overall 退出码）<br>- **P3-2**：README changelog 行末尾残留 `(line truncated to 2000 chars)` 工具截断标记清理<br>- **P3-5**：README §二 推荐批次表 第 4 批加注行明确"F11 Phase 1 同步启动"（已隐含；v2.2.0 强化）<br>- 顶层设计三件套主版本号同步 v2.1.0 → **v2.2.0**（workflow.md / architecture_modules.md / module_schemas.md 顶部 metadata） | 评审者 |
| 2026-09-16 | **v2.2.1 / review.md（评审后修复）同步** | 本轮按 `harness/feature/review.md` §六推荐修复清单应用全部 21 项修复（2 P0 + 6 P1 + 9 P2 + 4 P3；详见 review.md）：<br>- **P0-1**：F02 §3.5 line 104 `init_completed=True` → `init_only=True`（与 F06 实际 API 严格对齐）<br>- **P0-2**：F07 §一 + F08 §一 header "批次" 字段对齐 v1.1.0 P0-3 修复（Phase 拆分明示）<br>- **P1-1**：F08 §一 line 6 依赖列改写（消除"F10（primitives 类型注解）"歧义；明示 Phase 1 无运行时依赖）<br>- **P1-2**：F05 §3.5.2 / §4.4b / 表格末行 log tag 计数 prose 统一为 13（12 自主发射 + 1 转发捕获）<br>- **P1-3**：F03 §3.2 RuntimeConfig 字段数从"12 / 13 prose 矛盾"统一为 13 + 内部分类修正（"杂项 2 字段" → "杂项 1 字段"）<br>- **P1-4**：F11 §3.2 exit_code 3 段 prose 合并为单一连贯段<br>- **P1-5**：F09 §3.4 双层防御术语统一（主链 = requires_approval=True；次要防御 = 未声明 SIDE_EFFECTS）<br>- **P1-6**：F02 §3.4 黑名单表出锚点 `{#stage-blacklist-table}` + F03 / F05 / F06 装饰器参数严格对齐（含方法名后缀 .__init__ / .load / .resolve / .create / .compile）<br>- **P2-1**：F13 §四 增 §4.5a "两类 pyproject.toml 区分验证" 4 项测试<br>- **P2-2**：F12 §四 测试目标数 ≥15 拆分为 ≥21（按 §4.1-4.4 子节）<br>- **P2-3**：F08 §3.3.0 脱敏清单改**精确字段名匹配**（避免误命中 LangChain `usage_metadata.input_tokens` 等子键）<br>- **P2-4**：README §三.4 init 行加注 `init.end` 由 F06 在 exit_cleanup 阶段统一发射<br>- **P2-5**：F08 §3.3 新增 §3.3.0 "logger 行为约束总览"段（单一索引）+ 脱敏 `_redact()` Python 实现示例<br>- **P2-6**：F09 §3.4b 增 ToolSpec.requires_approval × side_effects 真值表（5 组合）+ 4 项新增 TDD 用例<br>- **P2-7**：F03 / F05 / F06 装饰器 prose 引用 `{#stage-blacklist-table}` 锚点<br>- **P2-8**：F08 §3.3.2 改"权威源在 README §三.6.2 表"引用<br>- **P2-9**：F01 / F02 / F03 / F05 / F06 / F10 / F13 prompt 顶部"## 二、必读顶层设计 artefact"末尾增"本 feature 重点对齐的宪法条款"段（≤5 行 / feature）<br>- **P3-1**：F13 §3.2 excludes 注释补 `langchain_core.tracers.langchain` 实际语义说明<br>- **P3-2**：README 无实际截断标记需清理（仅 changelog 内提及；本条记录已完成）<br>- **P3-3**：F02 / F03 / F05 / F06 装饰器 prose 已引用 stage_guard.py 实现位置（无新动作）<br>- 不变更顶层设计三件套主版本号（v2.2.0 维持）；review.md 顶层版本号同步升 v1.0.0 → **v2.2.1** | 项目维护者 |
| 2026-09-16 | **v2.2.2 / review.md（feature 排班评审）应用修复** | 本轮按 `harness/feature/review.md`（v1.0.0）§六推荐修复清单应用全部 **6 项问题修复**（2 P0 + 3 P1 + 1 P2；详见 review.md §五）：<br>- **P0-1（方案 A'）**：`stage_guard.py` 从 `langagent/runtime/` 移到 `langagent/cross_cutting/`（新增 `cross_cutting_stage_guard` 模块；cross_cutting 层 4 → 5；模块总数 19 → 20；architecture_modules.md 矩阵 19×19 → 20×20）。F10 `chat_model_factory.create()` + `state_graph_builder.build()` 应用 `@cross_cutting_stage_guard_decorator` 包裹（model_adapt / graph_compose 阶段能力边界技术实施落地）；F03 / F05 / F06 / F02 import path 从 `langagent.runtime.stage_guard` 改为 `langagent.cross_cutting.stage_guard`；CHK-AR-023 校验 6 阶段装饰器应用<br>- **P0-2（方案 A）**：F10 §3.4a Middleware 加载协议新增步骤 5（实例化系统护栏 middleware：`cross_cutting_guardrail_middleware.build_middleware(policy=RuntimeConfig.guardrail_policy)`）；architecture_modules.md 矩阵新增 1 条硬例外单向边 `primitives_state_graph_builder → cross_cutting_guardrail_middleware`（带 →¹ 标记）；CHK-AR-024 校验；F05 §3.6 / §八 + F09 §八 prose 同步（F05 不构造 guardrail middleware，由 F10 §3.4a 步骤 5 注入）<br>- **P1-1**：F06 §3.1 `cleanup()` 签名补 `init_only: bool = False` keyword-only 参数（**5 参 → 7 参**）；F06 §3.3 line 36 / 41 prose 计数修订；F06 §四 TDD 新增 `test_cleanup_init_only_mode_emits_init_end_log`；F06 §七 deliverable 同步<br>- **P1-2**：F02 §3.4 阶段级黑名单表 `model_adapt` 行移除 `chat_model_factory.create` 项（消除列表与注脚自相矛盾）；该 op 是 model_adapt 阶段合法操作，不在黑名单<br>- **P1-3**：README.md metadata header `version: v0.0.1` → **`v2.2.2`**；`last_updated: 2026-09-15` → `2026-09-16`（P1-3 修复）<br>- **P2-3**：顶层设计三件套主版本号同步关系显式声明 —— workflow.md / architecture_modules.md 主版本号 → **v2.2.0**（独立演进：init_only cleanup 模式 + Guardrail 提升 + stage_guard 跨层迁移）；module_schemas.md 主版本号 → **v1.2.0**（独立演进：22 章 → 23 章 / 25 类型 → 27 类型）。两者修改主体不同，独立演进<br>- 顶层设计三件套主版本号同步 v2.2.0 → **v2.3.0**（新增 cross_cutting_stage_guard 模块 + 1 条 primitives → guardrail 边 + model_adapt / graph_compose 阶段能力边界技术实施 + matrix 20×20 = 400 单元格）；review.md v1.0.0 → v1.0.1（无变更，仅 changelog 同步） | 评审者 |
| 2026-09-16 | **v2.3.0 / review.md v1.0.0 评审（feature 排班）应用修复** | 本轮按 `harness/feature/review.md`（v1.0.0）§六推荐修复清单应用全部 **9 项问题修复**（2 P0 + 4 P1 + 3 P2；详见 review.md §五）：<br>- **P0-1（v1.0.0 review.md）**：F05 `build_doctor_probes()` API 需 import `primitives_chat_model_factory` + `primitives_checkpoint_adapter` 违反 F05 既有禁止依赖方向；architecture_modules.md v2.3.0 → **v2.4.0** 新增 2 条硬例外单向边（`runtime_main_loop_dispatcher → {primitives_chat_model_factory, primitives_checkpoint_adapter}`，带 →² 标记）；累计硬例外单向边 9 → **11 条**；F05 模块描述"关键 API"增 `build_doctor_probes()` + "允许的依赖方向"增 2 行；新增 **CHK-AR-025**<br>- **P0-2（v1.0.0 review.md）**：workflow.md#log-tag-la-lifecycle-init-end 发射方由 "F02 `runtime_dir_loader.write_template()` 收尾" 修订为 "F06 `runtime_exit_handler.cleanup()`（`init_only=True` 模式分支）"；workflow.md 主版本号 v2.1.0 维持（changelog 内追加修复说明即可，不需要升版）<br>- **P1-1（v1.0.0 review.md）**：ALLOWED_TAGS 45 → 46 字面量同步；README line 30 / 66 / 104 + F01 / F02 / F05 / F10 / F11 prompt + architecture_modules.md line 423 全部 "45 项" / "≥45 项" 修订为 "46 项" / "≥46 项"<br>- **P1-2（v1.0.0 review.md）**：README §一 F11 行的"依赖的 feature"单列拆为 "**模块 import 依赖**" + "**运行时调用依赖**" 2 列；表头 7 列 → 8 列；F11 行的依赖清晰区分：模块 import = F02 / F03 / F05 / F07 / F10；运行时调用 = F01 / F06。F11 prompt §六 7 条 prose 同步拆分为"模块 import 依赖" + "运行时调用依赖"两段<br>- **P1-3（v2.2.2 review.md）**：dependency matrix 20×20 → **21×21 = 441 单元格**，新增 `eval_runner` 行/列（21st module_id）；`cli_runner → eval_runner` 显式登记；`eval_runner` 行/列 与其他 20 module 全填 `–`；模块到 Feature 拆分映射表追加 `eval_runner | F11` 行；模块清单脚注 `eval_runner` 描述更新为 21st module_id 显式登记；CHK-AR-006 / CHK-AR-016 实际值同步 20 → **21**<br>- **P1-4（v1.0.0 review.md）**：F05 prompt header line 5 "**4 个自定义 reducer 函数**" 修订为 "**3 个唯一 reducer 函数覆盖 4 个自定义字段**"（与 F10 prompt + module_schemas.md §StateReducers 对齐；`replace_with_merge` 被 `todos` 与 `scratchpad` 共用）<br>- **P2-1（v1.0.0 review.md）**：F10 prompt §3.4a 步骤 5 增 1 段 "F09 `build_middleware` 接口 stub 预放"（F02 首批实现 `stage_guard.py` 时**同步预放** F09 Protocol stub 位于 `langagent/cross_cutting/guardrail_middleware.py`，归属 F09 但 F02 拥有 stub 文件预放权；F10 TDD 不阻塞）；F02 §3.4b 同步说明<br>- **P2-3（v1.0.0 review.md）**：architecture_modules.md 模块清单脚注增 5 graders 显式登记（`langagent/eval/graders/{exact_match,contains,regex,llm_judge,tool_call_match}.py`；统一接口 `grade(actual, expected, **kwargs) -> bool`；`__init__.py` 提供 `GRADER_REGISTRY` 路由表；不计入 21 个 module_id 计数；与 `eval_runner` 同属 F11 跨层整合模块）；新增 **CHK-AR-026**<br>- **架构主版本号同步**：architecture_modules.md v2.3.0 → **v2.4.0**（新增 2 条硬例外单向边 + matrix 21×21 + 5 graders 显式登记 + CHK-AR-025/026）；workflow.md v2.1.0 维持（仅字面量修订 + changelog 追加）；module_schemas.md v1.2.0 维持<br>- **README 主版本号同步 v2.2.2 → v2.3.0**；review.md v1.0.0 → **v1.0.1**（changelog 同步 + 标记本轮全部 9 项修复已应用） | 评审者（feature/review.md v1.0.0 评审应用） |
