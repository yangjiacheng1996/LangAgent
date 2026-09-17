---
doc_id: architecture_modules
version: v2.4.0
last_updated: 2026-09-16
constitution_ref: ../../.specify/memory/constitution.md
related_docs:
  - workflow.md
  - module_schemas.md
---

# architecture_modules.md — 架构模块设计文档

> 本文档是 LangAgent 顶层设计三份文档之二，按 5 层（cli / runtime / protocol / cross_cutting / primitives）划分模块，定义每个模块的职责、关键 API、依赖方向、模块间依赖矩阵、Feature 拆分映射、静态约束 CI 校验清单。
> 本文档作为 Feature 01-10+ "我该往哪一层写 / 能不能从 A 层 import B 层" 的事实来源。
>
> 与宪法第 I 条关系：本文件不发布 SDK、不暴露 importable API；纯设计文档。
> 与宪法第 II 条关系：模块以 LangChain / LangGraph 原语为基础，不依赖 MDA 代码。
> 与宪法第 V 条关系：智能体目录契约由 protocol / cross_cutting 层支撑。
>
> **v0.4.0 变更**：
> - 依赖矩阵（§"模块间依赖矩阵"）新增 2 条硬例外单向边：`primitives_chat_model_factory → cross_cutting_logger` + `primitives_state_graph_builder → cross_cutting_logger`（review.md M-NEW-2 方案 B 修复）；CHK-AR-021 校验硬例外单向性。
> - 模块清单新增 `primitives_state_reducers` 模块（review.md M-4 方案 C 修复：reducer 函数从 F05 移到 primitives 层）；5 层模块总数 18 → 19。
> - 依赖矩阵 18×18 → 19×19（361 单元格）。
>
> **v2.3.0 变更（review.md v2.2.2 P0-1 方案 A' + P0-2 修复）**：
> - 新增 `cross_cutting_stage_guard` 模块（`stage_guard.py` 从 `langagent/runtime/` 移到 `langagent/cross_cutting/`，理由：F10 也需应用 `@stage_guard_decorator` 实施 model_adapt / graph_compose 阶段能力边界，primitives → runtime 跨层依赖违反 F02 M-4-方案 C 先例）；5 层模块总数 19 → **20**；cross_cutting 层 4 → 5。
> - 依赖矩阵 19×19 → **20×20 = 400 单元格**；新增 7 条硬例外单向边（6 条 stage_guard + 1 条 guardrail_middleware），累计 9 条硬例外单向边。
> - 新增 CHK-AR-023（6 阶段装饰器应用）+ CHK-AR-024（primitives → guardrail_middleware 实例化）。
> - 模块清单 + 模块到 Feature 拆分映射表同步更新。
>
> **v1.2.0 变更（review.md v1.1.0 P0-2 修复后）**：
> - 模块清单无变化（19 个），但 `LoadedAgent` schema 在 `module_schemas.md#schema-loaded-agent` 由 6 字段减为 **5 字段**（删除 `compiled_graph`）；`runtime_dir_loader.load()` 仍返回 LoadedAgent（5 字段），F10 `primitives_state_graph_builder.build()` 仍接收 LoadedAgent 作输入但**不再**承担填充 `compiled_graph` 的责任（该字段已删）；F01 dispatch 独立持 LoadedAgent + CompiledStateGraph 两个变量。
>
> **v2.1.0 变更（review.md v2.1.0 修复后）**：
> - 模块清单无变化（19 个）；F06 `cleanup()` API 新增 keyword-only `init_only: bool = False` 参数（init-only cleanup 模式）；RuntimeConfig 新增 `guardrail_policy` 字段（**review.md v2.1.0 P1-4 修复**），由 F03 config_resolve 读 env LANGAGENT_GUARDRAIL_* 注入；其余模块依赖矩阵无变化。
>
> **v2.4.0 变更（review.md v1.0.0 / v2.2.2 P0-1 + v1.0.0 P1-3 修复后——本轮由 feature/review.md 评审识别并应用修复）**：
> - **P0-1 修复**：F05 `build_doctor_probes()` API（review.md v1.0.0 P0-1 新增）需要 import `primitives_chat_model_factory` + `primitives_checkpoint_adapter` 构造 doctor probe 函数对，违反 F05 既有禁止依赖方向。**新增 2 条硬例外单向边**：`runtime_main_loop_dispatcher → primitives_chat_model_factory` + `runtime_main_loop_dispatcher → primitives_checkpoint_adapter`（`build_doctor_probes` 是被动构造方法，primitives 不反向依赖 F05）。累计硬例外单向边 9 → **11 条**。
> - **P1-3 修复**：依赖矩阵 20×20 → **21×21 = 441 单元格**，新增 `eval_runner` 行/列（21st module_id）；`cli_runner → eval_runner` 单元格填 `→`；其他 20 module × `eval_runner` / `eval_runner` × 20 module 全填 `–`；矩阵脚注回路验证补 `eval_runner` 节点。
> - **P2-3 修复**：模块清单脚注增 5 graders 描述（`langagent/eval/graders/{exact_match,contains,regex,llm_judge,tool_call_match}.py`；不计入 21 个 module_id 计数；与 `eval_runner` 同属 F11 跨层整合模块）。
> - **新增 CHK-AR-025**（F05 → primitives 2 条硬例外单向边校验）+ **CHK-AR-026**（5 graders `grade()` 函数存在性校验）。

---

## 文档元信息

| 字段 | 值 |
|---|---|
| `doc_id` | `architecture_modules` |
| `version` | `v2.4.0`（**review.md v1.0.0 / v2.2.2 P0-1 + v1.0.0 P1-3 修复后**：F05 build_doctor_probes 2 条新硬例外单向边 + matrix 20×20 → 21×21 + 5 graders 显式登记；本文件主版本号同步 v2.3.0 → v2.4.0） |
| `last_updated` | `2026-09-16` |
| `constitution_ref` | `../../.specify/memory/constitution.md` |
| `related_docs` | `workflow.md`、`module_schemas.md` |

---

## 5 层架构总览

> 5 层英文蛇形命名严格为 `cli` / `runtime` / `protocol` / `cross_cutting` / `primitives`（FR-021 / Q3）。
> 依赖方向严格自上而下：上层可调用下层；下层不得反向依赖上层。

### `cli` 层（命令行入口）

- **职责概述 1**：解析 argv，调度 4 个核心子命令（`init` / `run` / `eval` / `doctor`），分发到 runtime 层。
- **职责概述 2**：将 RuntimeConfig.cli_args 写入 `RuntimeConfig`，不直接接触磁盘 / 模型 / LangGraph。
- **职责概述 3**：打印 CLI 提示符与最终退出码；本层不持久化任何状态。

### `runtime` 层（运行时调度）

- **职责概述 1**：实现 6 阶段调度（`dir_load` / `config_resolve` / `model_adapt` / `graph_compose` / `main_loop` / `exit_cleanup`）。
- **职责概述 2**：维护 `LoadedAgent` 与 `RuntimeConfig` 的生命周期；提供阶段间数据传递。
- **职责概述 3**：不直接 import LangChain / LangGraph 原生类型；通过 primitives 层封装。

### `protocol` 层（协议与规范）

- **职责概述 1**：定义并加载 SkillSpec / ToolSpec / MiddlewareSpec / ChannelSpec / IdentitySpec / MemorySpec / EvalTaskSpec。
- **职责概述 2**：维护 Event 总线（protocol_event_bus），为 cross_cutting 层提供事件订阅接口。
- **职责概述 3**：不实例化任何业务对象；只负责"声明"与"加载"。

### `cross_cutting` 层（横切关注点）

- **职责概述 1**：日志 / 指标 / 审计 / 护栏 4 类横切能力，对所有阶段可见。
- **职责概述 2**：通过 middleware 机制注入到 LangGraph 图；不直接修改业务节点。
- **职责概述 3**：所有写入操作（Span / Event / AuditEntry / MetricsSnapshot）均在本层完成。

### `primitives` 层（LangChain / LangGraph 原语封装）

- **职责概述 1**：封装 LangChain 原生类型（`BaseChatModel` / `BaseTool` / `AgentMiddleware`）的工厂方法。
- **职责概述 2**：封装 LangGraph 原生类型（`StateGraph` / `CompiledStateGraph` / `BaseCheckpointSaver`）的构造方法。
- **职责概述 3**：本层是 LangAgent 与 LangChain / LangGraph 的唯一接触面；其他层不得直接 import LangChain / LangGraph。

---

## 模块清单

> 5 层共 **20 个模块**（cli 3 / runtime 4 / protocol 3 / cross_cutting **5** / primitives 5），总模块数 ≥ 12（FR-022 / R-1.3；**v0.2.0 M-3 修复后**：新增 `primitives_langchain_types`，17 → 18；**v0.4.0 M-4 方案 C 修复后**：新增 `primitives_state_reducers`，18 → 19；**v0.5.0 修复（评审 v0.1.0 §二.A.3 方案 A）**：EventBusProtocol 接口定义职责合并入 `cross_cutting_logger` 模块，模块总数仍为 19；**v2.3.0 修复（review.md v2.2.2 P0-1 方案 A'）**：新增 `cross_cutting_stage_guard` 模块，19 → **20**；`stage_guard.py` 从 `langagent/runtime/stage_guard.py`（F02 runtime 内部工具）移到 `langagent/cross_cutting/stage_guard.py`（F02 拥有但归属于 cross_cutting 层），cross_cutting 层 4 → 5）。
> 每个 `module_id` 全局唯一（Q8），跨层重名时带层语义前缀（如 `cli_runner` / `runtime_dir_loader` / `cross_cutting_stage_guard`）。
> 每个模块以 `### <module_id> {#mod-<module-id>}` 显式锚点（FR-026）。
> （评审 m-2 修复：早期版本误写为 "5 层共 15 个模块（每层 3 个）"，但 runtime 层实际有 4 个模块，cross_cutting 层有 4 个模块，primitives 层 v0.4.0 后有 5 个模块；当前版本以 20 为准。）
> **外加 F11 提供的 `eval_runner`（21st module_id 跨 runtime / cli 整合模块）**：位于 `langagent/eval/runner.py`，由 F11 实现；F01 dispatch 通过 `from langagent.eval.runner import run` 形式调用（**review.md M-4 修复**）；**v2.4.0 review.md P1-3 修复后**：`eval_runner` 进入依赖矩阵 21×21 计数（21st module_id），`cli_runner → eval_runner` 是显式登记边。
> **外加 F11 提供的 5 graders（跨层整合子模块，不计入 module_id 计数）**：位于 `langagent/eval/graders/{exact_match,contains,regex,llm_judge,tool_call_match}.py`，由 F11 Phase 2 实现；统一接口 `grade(actual, expected, **kwargs) -> bool`；`__init__.py` 提供 grader 路由表 `GRADER_REGISTRY: dict[str, GradeFunction]`；不计入 21 个 module_id 计数（与 `eval_runner` 同属"跨层整合模块"），仅作 F11 内部实现细节；**v2.4.0 review.md P2-3 修复后**显式登记。

### `cli_runner` {#mod-cli-runner}

> `cli` 层模块 1：CLI 入口解析与子命令分发。

#### 职责

- 主职责：解析 argv，识别 4 个核心子命令（`init` / `run` / `eval` / `doctor`），将参数写入 `RuntimeConfig.cli_args`。
- 副职责：根据子命令调用对应 `runtime_*` 模块（`runtime_dir_loader` / `runtime_main_loop_dispatcher` / `runtime_exit_handler`）；最终退出码由本模块统一返回。

#### 关键 API

- `def parse_argv(argv: list[str]) -> CliArgs`：解析 argv，返回 frozen CliArgs。
- `def dispatch(args: CliArgs, runtime: RuntimeDeps) -> int`：分发到对应 runtime 模块，返回退出码。

#### 允许的依赖方向

- → `cli_parser`（同级 cli 层，单向：cli_runner 调用 cli_parser 反向不调用）
- → `cli_output_formatter`（同级 cli 层）
- → `runtime_dir_loader`
- → `runtime_main_loop_dispatcher`
- → `runtime_exit_handler`
- → `runtime_config_resolver`

#### 禁止的依赖方向

- × `primitives_chat_model_factory`（CLI 层不得直接实例化模型；模型实例化由 runtime → model_adapt 阶段通过 primitives 层完成）
- × `protocol_skill_loader`（CLI 层不得直接加载 skill；加载由 runtime → dir_load 阶段通过 protocol 层完成）
- × `cross_cutting_audit_recorder`（CLI 层不得直接写审计；审计由 main_loop 阶段通过 cross_cutting 层完成）

---

### `cli_parser` {#mod-cli-parser}

> `cli` 层模块 2：参数 schema 定义与 argparse 封装。

#### 职责

- 主职责：定义 4 个核心子命令的 argparse schema（参数名 / 类型 / 默认值 / 帮助文本）。
- 副职责：把 argparse 结果（`argparse.Namespace`）转换为 `RuntimeConfig.cli_args` 字典；不调用 runtime 层任何模块。

#### 关键 API

- `def build_parser() -> argparse.ArgumentParser`：构造顶层 ArgumentParser。
- `def ns_to_cli_args(ns: argparse.Namespace) -> dict[str, Any]`：转换 argparse.Namespace → cli_args dict。

#### 允许的依赖方向

- → `runtime_config_resolver`（仅用于类型注解）
- ↔ 无（同层单向；cli_runner → cli_parser，cli_parser 不反向调用 cli_runner）

#### 禁止的依赖方向

- × `runtime_dir_loader` / `runtime_main_loop_dispatcher` / `runtime_exit_handler`（CLI 层不得直接驱动阶段；阶段调度由 cli_runner 负责）
- × `cross_cutting_logger`（CLI 层不得直接打日志；日志由 runtime → 各阶段通过 cross_cutting 层完成）
- × `primitives_*`（CLI 层不接触 LangChain / LangGraph 原语）

---

### `cli_output_formatter` {#mod-cli-output-formatter}

> `cli` 层模块 3：终端输出格式化与退出码打印。

#### 职责

- 主职责：把 `EvalReport` / `DoctorReport` / `Event` 流格式化为人类可读文本（彩色 / 表格 / 进度条）。
- 副职责：在 `exit_cleanup` 阶段结束时打印最终退出码；本层不写日志。

#### 关键 API

- `def format_eval_report(report: EvalReport) -> str`：EvalReport → 人类可读文本。
- `def format_doctor_report(report: DoctorReport) -> str`：DoctorReport → 人类可读文本。

#### 允许的依赖方向

- → `runtime_exit_handler`（在 exit_cleanup 阶段末尾回调）
- → `protocol_event_bus`（订阅 Event 流）

#### 禁止的依赖方向

- × `runtime_dir_loader` / `runtime_main_loop_dispatcher` / `runtime_config_resolver`（CLI 层不得直接驱动阶段）
- × `primitives_*`（CLI 层不接触 LangChain / LangGraph 原语）
- × `cross_cutting_metrics_collector`（CLI 层不得读 metrics；metrics 由 runtime → main_loop 阶段通过 cross_cutting 层写入）

---

### `runtime_dir_loader` {#mod-runtime-dir-loader}

> `runtime` 层模块 1：阶段 1 `dir_load` 的实现（宪法第 V 条目录契约）。

#### 职责

- 主职责：扫描智能体目录，验证 4 个子目录 + instructions.md，产出 `LoadedAgent.instructions` / `tool_ids` / `skill_names`（**review.md v1.1.0 P0-2 修复后**：LoadedAgent 仅 5 字段，删除 `compiled_graph`；F10 build() 返回 CompiledStateGraph 由 F01 dispatch 独立持有）。
- 副职责：失败时返回 `stage_capability_violation` 标志位（仅当读取了不该读的 `.env` 等配置时）。

#### 关键 API

- `def load(agent_dir: str) -> LoadedAgent`：扫描 + 校验 + 返回 LoadedAgent。
- `def validate_layout(agent_dir: str) -> list[str]`：返回缺失的文件 / 目录列表。

#### 允许的依赖方向

- → `cli_runner`（被 cli 层调用）
- → `protocol_skill_loader` / `protocol_tool_registry`（加载 skill / tool 元数据）
- → `cross_cutting_logger`（打日志）

#### 禁止的依赖方向

- × `cli_parser` / `cli_output_formatter`（runtime 不得反向依赖 cli 层）
- × `runtime_config_resolver`（dir_load 阶段不得解析 .env；这是 config_resolve 阶段的责任，违反会触发 `stage_capability_violation`）
- × `primitives_chat_model_factory`（runtime 不得直接实例化模型；模型实例化由 `primitives_chat_model_factory` 完成）

---

### `runtime_config_resolver` {#mod-runtime-config-resolver}

> `runtime` 层模块 2：阶段 2 `config_resolve` 的实现（宪法第 XII 条优先级链）。

#### 职责

- 主职责：按"CLI > 环境变量 > .env > 内置默认"优先级合并 4 个字段源，产出冻结的 `RuntimeConfig` 实例。
- 副职责：校验必填字段；类型不匹配时返回退出码 78（EX_CONFIG）；优先级冲突无法仲裁时返回退出码 78。

#### 关键 API

- `def resolve(cli_args: dict[str, Any], agent_dir: str) -> RuntimeConfig`：合并 4 字段源，返回 frozen RuntimeConfig。
- `def merge_priority_chain(...) -> dict[str, Any]`：内部优先级合并算法。

#### 允许的依赖方向

- → `cli_parser`（仅用于类型注解 `CliArgs`；不反向调用 cli 层；cli_args 由 cli_runner 显式传入）
- → `cross_cutting_logger`（打日志）

#### 禁止的依赖方向

- × `runtime_dir_loader`（config_resolve 阶段依赖 dir_load 阶段的产出（LoadedAgent），但不得反向调用 dir_load）
- × `primitives_chat_model_factory`（config_resolve 不得实例化模型；这是 model_adapt 阶段的责任，违反会触发 `stage_capability_violation`）
- × `cli_runner` / `cli_output_formatter`（runtime 不得反向调用 cli 层；单向依赖）

---

### `runtime_main_loop_dispatcher` {#mod-runtime-main-loop-dispatcher}

> `runtime` 层模块 3：阶段 5 `main_loop` 的实现（宪法第 VI 条 Agent Loop）。

#### 职责

- 主职责：驱动 LangGraph `CompiledStateGraph` 的 ReAct 主循环（推理→工具→观察），直至收敛 / 中断 / 错误。
- 副职责：发布 Event（`tool_call` / `model_response` / `guardrail_block`）；每轮结束更新 MetricsSnapshot。

#### 关键 API

- `def dispatch(graph: CompiledStateGraph, state: AgentState) -> AgentState`：驱动一轮 ReAct；返回更新后的 state。
- `def run_until_done(graph: CompiledStateGraph, state: AgentState) -> AgentState`：完整跑完主循环。
- `def build_doctor_probes() -> tuple[Callable[[RuntimeConfig], tuple[bool, str]], Callable[[RuntimeConfig], tuple[bool, str]]]`：**review.md v1.0.0 P0-1 修复新增**；构造 doctor 子命令用的 model / checkpointer probe 函数对；F05 是该 API 的天然归属（runtime 层依赖 primitives 是 matrix 允许的，且 F05 已是 primitives 消费方）；F01 doctor dispatch 调 `build_doctor_probes()` 后注入到 F06 `run_doctor_checks(*, model_probe_fn=, checkpoint_probe_fn=)`；F01 与 F06 都不直接 import primitives（恢复 CLI × primitives 黑名单约束）。

#### 允许的依赖方向

- → `primitives_state_graph_builder`（取得 CompiledStateGraph）
- → `primitives_chat_model_factory` + `primitives_checkpoint_adapter`（**review.md v1.0.0 P0-1 修复新增硬例外单向边**，v2.4.0 显式登记；仅限 `build_doctor_probes()` API 内部使用，primitives 不反向依赖 F05；CHK-AR-025 校验）
- → `protocol_event_bus`（发布 Event）
- → `cross_cutting_metrics_collector` / `cross_cutting_audit_recorder` / `cross_cutting_guardrail_middleware`
- → `cross_cutting_logger`

#### 禁止的依赖方向

- × `runtime_dir_loader` / `runtime_config_resolver`（main_loop 阶段不得重新加载目录或重新解析配置）
- × `cli_*`（runtime 不得反向依赖 cli 层）
- × `cross_cutting_logger` 之外的 cross_cutting 子模块？不——cross_cutting_logger / cross_cutting_metrics_collector / cross_cutting_audit_recorder / cross_cutting_guardrail_middleware 均允许依赖
- × `primitives_chat_model_factory` / `primitives_checkpoint_adapter` 用于 `dispatch` / `run_until_done` 主路径（main_loop 阶段不得直接实例化模型；模型由 `runtime_config_resolver` 在 config_resolve 阶段完成后持有）；**例外**：`build_doctor_probes()` API 内部允许引用 primitives（review.md v1.0.0 P0-1 硬例外单向边）

---

### `runtime_exit_handler` {#mod-runtime-exit-handler}

> `runtime` 层模块 4：阶段 6 `exit_cleanup` 的实现。

#### 职责

- 主职责：关闭 checkpointer 连接，写出 DoctorReport / EvalReport / MetricsSnapshot / Span / Event / AuditEntry 到磁盘。
- 副职责：发布最终退出码；任何 I/O 异常返回退出码 4（I/O 错误）。

#### 关键 API

- `def cleanup(state: AgentState | None, config: RuntimeConfig, *, doctor_report: DoctorReport | None = None, eval_report: EvalReport | None = None, metrics_snapshot: MetricsSnapshot | None = None) -> int`：清理资源 + 写出报告 + 返回退出码（**review.md v0.3.0 S-3 修复**：6 参 keyword-only 接口，`run` 子命令仅传 `state` + `config`；`eval` 子命令传 `eval_report`；`doctor` 子命令传 `doctor_report`）。
- `def close_checkpointer(checkpointer: BaseCheckpointSaver) -> None`：关闭连接（**review.md v0.3.0 第四批 S-5 修复明确**：仅关闭由 F10 / F01 dispatch 构造的 checkpointer，不在本模块重新实例化）。
- `def run_doctor_checks(config: RuntimeConfig, loaded: LoadedAgent, *, model_probe_fn: Callable[[], tuple[bool, str]] | None = None, checkpoint_probe_fn: Callable[[], tuple[bool, str]] | None = None) -> list[DoctorCheckResult]`：4 项自检（**review.md v0.3.0 第四批 S-5 修复后**：F06 不直接调用 primitives；probe callable 由 F01 doctor dispatch 注入）。

#### 允许的依赖方向

- → 所有 runtime 模块（exit_cleanup 在 main_loop 完成后串行调用）
- → `protocol_event_bus`（订阅收尾事件）
- → `cross_cutting_audit_recorder`（刷新审计）
- → `cross_cutting_metrics_collector`（review.md v0.3.0 M-1 修复：调 `flush()` + `snapshot()` 取最终指标；仅读不写）
- → `cross_cutting_logger`

#### 禁止的依赖方向

- × `cli_*`（runtime 不得反向依赖 cli 层）
- × `primitives_chat_model_factory`（exit_cleanup 不得重新实例化模型）
- × `primitives_state_graph_builder`（exit_cleanup 不得重新编译图；仅可关闭已构造的 checkpointer）
- × `runtime_dir_loader`（exit_cleanup 不得重新加载目录）

---

### `protocol_event_bus` {#mod-protocol-event-bus}

> `protocol` 层模块 1：Event 总线（spec FR-030 `Event` / `Event 总线`）。

#### 职责

- 主职责：实现发布 / 订阅模式的事件总线；事件类型见 `module_schemas.md#schema-event`。
- 副职责：所有跨模块通信必须经过 Event 总线；直接函数调用仅允许在 `runtime_main_loop_dispatcher` 内部。

#### 关键 API

- `def publish(event: Event) -> None`：发布事件。
- `def subscribe(event_type: str, handler: Callable[[Event], None]) -> SubscriptionToken`：订阅事件类型。

#### 允许的依赖方向

- → `cross_cutting_logger`（事件总线自身打日志）
- → `cross_cutting_audit_recorder`（订阅安全相关事件）

#### 禁止的依赖方向

- × `runtime_*`（protocol 层不得依赖 runtime 层；runtime 层可调用 protocol）
- × `cli_*`（protocol 层不得依赖 cli 层）
- × `primitives_*`（protocol 层不接触 LangChain / LangGraph 原语；Event 类型由 protocol 自身定义）

---

### `protocol_skill_loader` {#mod-protocol-skill-loader}

> `protocol` 层模块 2：SkillSpec / SkillFrontmatter 加载（宪法第 V 条 skills/ 子目录）。

#### 职责

- 主职责：扫描 `skills/<name>/` 子目录，解析 `SKILL.md` 的 YAML frontmatter，产出 SkillSpec 列表。
- 副职责：版本兼容性校验（SkillFrontmatter.version 字段）；缺失字段时跳过该 skill 并打日志。

#### 关键 API

- `def load_all(skills_dir: str) -> list[SkillSpec]`：加载 skills_dir 下所有 skill。
- `def parse_frontmatter(md_path: str) -> SkillFrontmatter`：解析单个 SKILL.md frontmatter。

#### 允许的依赖方向

- → `cross_cutting_logger`（打日志）
- → `protocol_event_bus`（发布 `skill_loaded` / `skill_load_failed` 事件）

#### 禁止的依赖方向

- × `runtime_*` / `cli_*` / `primitives_*`（protocol 层不接触上层与原语层）
- × `protocol_tool_registry`（同级 protocol 层不强制依赖；通过 Event 总线解耦）

---

### `protocol_tool_registry` {#mod-protocol-tool-registry}

> `protocol` 层模块 3：ToolSpec / ToolSideEffect 注册表（宪法第 V 条 tools/ 子目录）。

#### 职责

- 主职责：扫描 `tools/<tool_name>.py`，加载 `BaseTool` 子类，构造 ToolSpec（含 side_effects 标注）。
- 副职责：在 `graph_compose` 阶段将 ToolSpec 列表注入 LangGraph 图。

#### 关键 API

- `def register_all(tools_dir: str) -> list[ToolSpec]`：扫描 + 注册。
- `def get_by_id(tool_id: str) -> ToolSpec | None`：按 tool_id 查找。

#### 允许的依赖方向

- → `primitives_chat_model_factory`（仅用于类型注解 `BaseTool`）
- → `cross_cutting_logger`
- → `protocol_event_bus`

#### 禁止的依赖方向

- × `runtime_*` / `cli_*`（protocol 不接触上层）
- × `protocol_skill_loader`（同级 protocol 不强制依赖）
- × `primitives_state_graph_builder`（tool 注册不直接构造图；图构造由 runtime → graph_compose 阶段完成）

---

### `cross_cutting_logger` {#mod-cross-cutting-logger}

> `cross_cutting` 层模块 1：结构化日志（FR-014 / R-5）；review.md v0.5.0（评审 v0.1.0 §二.A.3 方案 A 修复）合并 EventBusProtocol 接口定义职责。

#### 职责

- 主职责：以 `la.` 前缀发出结构化日志；按 `log_level`（默认 INFO）过滤。
- 副职责 1：所有阶段、所有模块均可调用本模块；唯一例外是 CLI 输出（由 `cli_output_formatter` 负责）。
- 副职责 2（**v0.5.0 新增**）：定义 `EventBusProtocol` 接口（`publish` / `subscribe` / `unsubscribe` / `flush` 4 个方法）；被 F07 `protocol_event_bus` 实现、被 F08 `cross_cutting_metrics_collector` 子模块（metrics 订阅事件总线）消费。**为何合并到本模块**（**review.md v0.1.0 R-004 修复补充权衡理由**）：
  - 两个接口都是**被动接口**（不反向依赖调用方），合并不引入分层违例。
  - 维持 19 个模块总数不变（避免 architecture_modules.md 模块计数变动）。
  - 两者都属"横切层基础设施"（logging + messaging 都是 cross_cutting concern）。
  - 拆分代价（新增 1 个 module_id + 拆分维护）大于收益（概念清晰度）。
  - 权衡结果：保持合并。本权衡理由同步登记于 F08 §一。

#### 关键 API

- `def emit(tag: str, payload: dict[str, Any]) -> None`：发出一条日志。
- `class EventBusProtocol(Protocol)`（**v0.5.0 新增**）：
  - `def publish(event: Event) -> None`：同步发布事件。
  - `def subscribe(event_type: str, handler: Callable[[Event], None]) -> Callable[[], None]`：订阅事件，返回 unsubscribe 句柄。
  - `def unsubscribe(token: Callable[[], None]) -> None`：取消订阅。
  - `def flush(timeout: float = 5.0) -> None`：阻塞等待 pending handlers 完成（超时仅记日志不抛错）。

#### 允许的依赖方向

- → （无；横切层不依赖任何上层；与 cross_cutting 同级模块可互相依赖但本模块不需要）

#### 禁止的依赖方向

- × `runtime_*` / `cli_*` / `protocol_*` / `primitives_*`（横切层不得依赖任何业务层；本模块是所有业务层的依赖对象）

#### 关键约束

- EventBusProtocol 接口定义必须先于 F07 `protocol_event_bus` 实现冻结（接口先于实现原则）；F07 严格实现本接口。
- 9 个 tag 发射方 feature（F02 / F03 / F05 / F06 / F07 / F08 / F09 / F10 / F11）通过 `from langagent.cross_cutting.logger import emit` 调用；本模块 `ALLOWED_TAGS` 集合 ≥ **46** 项校验（review.md v0.3.0 s-1 / s-2 / s-5 + v0.1.0 R-001 修复后：原 45 项 + 新增 `la.tool.suspicious_missing_side_effects` 1 项 = 46 项）。

---

### `cross_cutting_stage_guard` {#mod-cross-cutting-stage-guard}

> `cross_cutting` 层模块 5（**review.md v2.2.2 P0-1 修复新增**）：阶段能力边界装饰器（`@stage_guard_decorator`）。原位于 `langagent/runtime/stage_guard.py`（F02 内部工具模块，被 F03 / F05 / F06 复用），v2.2.2 P0-1 修复后移到 `langagent/cross_cutting/stage_guard.py`（cross_cutting 层）——理由：primitives 层 F10 也需要应用该装饰器包裹 `chat_model_factory.create()` / `state_graph_builder.build()` 实施 model_adapt / graph_compose 阶段能力边界技术保障；若保留在 runtime 层则需新增 primitives → runtime 跨层依赖（违反 F02 M-4-方案 C "避免 primitives → runtime" 先例）。移到 cross_cutting 层后：primitives / runtime / protocol / cli 各层均可单向依赖 cross_cutting_stage_guard，5 个模块（4 个 runtime + 2 个 primitives）依赖方向一致，无跨层违例。

#### 职责

- 主职责：实现 6 阶段能力边界的 runtime enforcement；提供 `@stage_guard_decorator(stage_name, *, monkeypatch_blacklist=None, audit_event_blacklist=None)` 装饰器，进入时 push 黑名单（monkeypatch + audit_hook），退出时 pop 恢复原始方法。
- 副职责 1：定义 `StageCapabilityViolationError` 异常（命中黑名单时抛出）；monkeypatch 子系统（`Monkeystack`）+ audit_hook 子系统（基于 `sys.addaudithook` 拦截 `open` / `import` / `compile` / `exec` 4 类内置事件）。
- 副职责 2：维护 6 阶段黑名单注册表（**权威源**；F02 §3.4 `{#stage-blacklist-table}` 锚点指向）；6 阶段 = `dir_load` / `config_resolve` / `model_adapt` / `graph_compose` / `main_loop` / `exit_cleanup`。

#### 关键 API

```python
class StageCapabilityViolationError(Exception):
    """命中阶段黑名单时抛出；F06 cleanup 阶段 worst_of 仲裁退出码 1。"""
    pass

def stage_guard_decorator(
    stage_name: str,
    *,
    monkeypatch_blacklist: list[type] | None = None,
    audit_event_blacklist: list[str] | None = None,
) -> Callable:
    """阶段装饰器；进入时 push 黑名单，退出时 pop 并恢复原始方法。"""
    ...

class Monkeystack:
    """monkeypatch 子系统栈；key = class, value = original method。"""
    ...

class AuditHookManager:
    """audit_hook 子系统；register/unregister 控制 sys.addaudithook 生命周期。"""
    ...

# 6 阶段黑名单注册表（权威源；与 F02 §3.4 `{#stage-blacklist-table}` 字面量同步）
STAGE_BLACKLIST_TABLE: dict[str, dict[str, list[type | str]]] = {
    "dir_load": {
        "monkeypatch": [BaseChatModel.__init__, StateGraph.compile, RuntimeConfigResolver.resolve],
        "audit_event": ["open"],
    },
    "config_resolve": {
        "monkeypatch": [BaseChatModel.__init__, RuntimeDirLoader.load, chat_model_factory.create],
        "audit_event": [],
    },
    "model_adapt": {
        "monkeypatch": [RuntimeDirLoader.load, RuntimeConfigResolver.resolve],
        # **注**：chat_model_factory.create 不在黑名单——是 model_adapt 阶段合法操作
        "audit_event": [],
    },
    "graph_compose": {
        "monkeypatch": [BaseChatModel.__init__, chat_model_factory.create, RuntimeDirLoader.load],
        "audit_event": [],
    },
    "main_loop": {
        "monkeypatch": [RuntimeDirLoader.load, RuntimeConfigResolver.resolve, BaseChatModel.__init__, chat_model_factory.create],
        "audit_event": ["open"],  # 拦截 open(.env)
    },
    "exit_cleanup": {
        "monkeypatch": [BaseChatModel.invoke, RuntimeDirLoader.load, RuntimeConfigResolver.resolve, chat_model_factory.create, BaseCheckpointSaver.__init__, StateGraph.compile],
        "audit_event": [],
    },
}
```

#### 允许的依赖方向

- → （无；横切层不依赖任何上层；与 cross_cutting 同级模块可互相依赖但本模块不需要）

#### 禁止的依赖方向

- × `runtime_*` / `cli_*` / `protocol_*` / `primitives_*`（横切层不得依赖任何业务层；本模块是所有业务层的依赖对象）

#### 关键约束

- 6 阶段装饰器应用方（**review.md v2.2.2 P0-1 修复新增**）：F02 `runtime_dir_loader.load()` / F03 `runtime_config_resolver.resolve()` / F10 `chat_model_factory.create()` / F10 `state_graph_builder.build()` / F05 `main_loop_dispatcher.run_until_done()` / F06 `exit_handler.cleanup()`；**6 个函数全部必须应用 `@stage_guard_decorator` 包裹**；CHK-AR-023 校验（grep AST 装饰器应用）。
- **打包归 F02（review.md v0.2.0 m-1 + v2.2.2 P0-1 修复后）**：F02 是 stage_guard_decorator + StageCapabilityViolationError + Monkeystack + AuditHookManager 4 个公开 API 的首批实现方；F02 §七 deliverable 中 `langagent/cross_cutting/stage_guard.py` 公开 API 落地；F03 / F05 / F06 / F10 通过 `from langagent.cross_cutting.stage_guard import stage_guard_decorator` 调用。
- **依赖方向约束（review.md v2.2.2 P0-1 修复后）**：`runtime_* → cross_cutting_stage_guard`（4 条边：runtime_dir_loader / runtime_config_resolver / runtime_main_loop_dispatcher / runtime_exit_handler）+ `primitives_* → cross_cutting_stage_guard`（2 条边：primitives_chat_model_factory / primitives_state_graph_builder）；**全部 6 条边都是合法单向边**（primitives / runtime → cross_cutting 基础设施；matrix 已登记）；**CHK-AR-023** 校验 6 阶段装饰器应用。

---

### `cross_cutting_metrics_collector` {#mod-cross-cutting-metrics-collector}

> `cross_cutting` 层模块 2：指标快照 MetricsSnapshot 收集（宪法第 IX 条 Monitoring）。

#### 职责

- 主职责：按时间窗口聚合 latency / error_rate / token_usage / cost_usd，产出 MetricsSnapshot。
- 副职责：在 `main_loop` 阶段每轮结束更新；在 `exit_cleanup` 阶段写出最终快照。

#### 关键 API

- `def record_latency(operation: str, ms: float) -> None`：记录单次操作延迟。
- `def snapshot(window_start: datetime, window_end: datetime) -> MetricsSnapshot`：聚合当前窗口。

#### 允许的依赖方向

- → `cross_cutting_logger`
- → `protocol_event_bus`（订阅 tool_call / model_response 事件）

#### 禁止的依赖方向

- × `runtime_*` / `cli_*` / `protocol_*` / `primitives_*`（横切层不依赖业务层）

---

### `cross_cutting_audit_recorder` {#mod-cross-cutting-audit-recorder}

> `cross_cutting` 层模块 3：审计条目 AuditEntry 写入（宪法第 IX 条 Guardrails + 宪法第 X 条）。

#### 职责

- 主职责：当 guardrail 拦截 / PII 泄露 / 越权 tool 调用 / prompt injection 时，写入 AuditEntry。
- 副职责：审计仅追加（append-only），不修改；脱敏后存储。

#### 关键 API

- `def write(entry: AuditEntry) -> None`：写入一条审计。
- `def query(category: str, since: datetime) -> list[AuditEntry]`：按类别 + 时间窗口查询。

#### 允许的依赖方向

- → `cross_cutting_logger`
- → `protocol_event_bus`（订阅所有安全相关事件）

#### 禁止的依赖方向

- × `runtime_*` / `cli_*` / `protocol_*` / `primitives_*`（横切层不依赖业务层）

---

### `cross_cutting_guardrail_middleware` {#mod-cross-cutting-guardrail-middleware}

> `cross_cutting` 层模块 4：护栏 middleware（宪法第 IX 条 Guardrails）。

#### 职责

- 主职责：根据 ToolSideEffect 标注决定是否触发 human-in-the-loop interrupt；拦截越权 tool 调用。
- 副职责：通过 LangChain `AgentMiddleware` 协议注入到 LangGraph 图；不修改业务节点。

#### 关键 API

- `def build_middleware(policy: GuardrailPolicy) -> AgentMiddleware`：构造 middleware 实例。
- `def evaluate(side_effects: list[ToolSideEffect]) -> GuardrailDecision`：决策。

#### 允许的依赖方向

- → `primitives_chat_model_factory`（用于类型注解 `AgentMiddleware`）
- → `cross_cutting_audit_recorder`（拦截时写审计）
- → `cross_cutting_logger`
- → `protocol_event_bus`

#### 禁止的依赖方向

- × `runtime_*` / `cli_*` / `protocol_skill_loader` / `protocol_tool_registry`（横切层不依赖业务层；primitives 例外，因为需要 LangChain 类型）
- × `cross_cutting_metrics_collector`（同级 cross_cutting 模块不强制依赖；本模块只调 audit_recorder）

---

### `primitives_chat_model_factory` {#mod-primitives-chat-model-factory}

> `primitives` 层模块 1：LangChain `BaseChatModel` 工厂（宪法第 IV 条模型抽象）。

#### 职责

- 主职责：根据 `RuntimeConfig.model_provider` / `model_name` / `model_base_url` 实例化 `BaseChatModel`。
- 副职责：本模块是 LangAgent 与 LangChain 的唯一接触面；其他层不得直接 import LangChain。

#### 关键 API

- `def create(config: RuntimeConfig) -> BaseChatModel`：实例化模型。

#### 允许的依赖方向

- → （无；primitives 层是依赖关系的最底层）

#### 禁止的依赖方向

- × `runtime_*` / `cli_*` / `protocol_*` / `cross_cutting_*`（primitives 层不依赖任何上层）

---

### `primitives_state_graph_builder` {#mod-primitives-state-graph-builder}

> `primitives` 层模块 2：LangGraph `StateGraph` 构造器（宪法第 VI 条 Agent Loop）。

#### 职责

- 主职责：根据 `AgentState` schema + `tool_ids` + `middleware_ids` + `checkpointer` 构造 `CompiledStateGraph`。
- 副职责：本模块是 LangAgent 与 LangGraph 的唯一接触面；其他层不得直接 import LangGraph。

#### 关键 API

- `def build(loaded_agent: LoadedAgent, config: RuntimeConfig, checkpoint: BaseCheckpointSaver) -> CompiledStateGraph`：构造并编译图（review.md v0.3.0 S-5 / M-3 修复：`checkpoint` 显式作为必传参数，由 F01 dispatch 在 `langagent run` 编排中先调 `checkpoint_adapter.create(config)` 后传入；本模块不再隐式创建 checkpointer；**review.md v1.1.0 P0-2 修复后**：loaded_agent 仅 5 字段不含 compiled_graph；build() 返回值由 F01 dispatch 独立持有，不回填到 LoadedAgent）。

#### 允许的依赖方向

- → （无；primitives 层是依赖关系的最底层）

#### 禁止的依赖方向

- × `runtime_*` / `cli_*` / `protocol_*` / `cross_cutting_*`（primitives 层不依赖任何上层）

---

### `primitives_checkpoint_adapter` {#mod-primitives-checkpoint-adapter}

> `primitives` 层模块 3：LangGraph `BaseCheckpointSaver` 适配器（宪法第 VI 条持久化）。

#### 职责

- 主职责：根据 `RuntimeConfig.checkpointer` 字段（'memory' / 'sqlite' / 'postgres'）实例化 `BaseCheckpointSaver`。
- 副职责：在 `runtime_exit_handler` 关闭连接时清理临时文件 / 释放连接池。

#### 关键 API

- `def create(config: RuntimeConfig) -> BaseCheckpointSaver`：实例化 checkpointer。
- `def close(saver: BaseCheckpointSaver) -> None`：关闭连接。

#### 允许的依赖方向

- → （无；primitives 层是依赖关系的最底层）

#### 禁止的依赖方向

- × `runtime_*` / `cli_*` / `protocol_*` / `cross_cutting_*`（primitives 层不依赖任何上层）

---

### `primitives_langchain_types` {#mod-primitives-langchain-types}

> `primitives` 层模块 4（**review.md v0.2.0 M-3 修复新增**）：LangChain / LangGraph 原生类型集中 re-export 出口。

#### 职责

- 主职责：集中 re-export LangChain / LangGraph 原生类型（`add_messages` / `BaseMessage` / `HumanMessage` / `AIMessage` / `SystemMessage` / `ToolMessage` / `AgentMiddleware` / `StateGraph` / `CompiledStateGraph` / `BaseCheckpointSaver` / `BaseTool` / `@tool` / `interrupt` 等），让 runtime / cross_cutting / protocol 层模块只能通过本模块 import，不直接 `from langchain` / `from langgraph`。
- 副职责：保证分层约束——`primitives` 层是 LangAgent 与 LangChain / LangGraph 的唯一接触面；其他层不得直接 import LangChain / LangGraph。

#### 关键 API

- `__all__`：列出所有 re-export 类型与函数；`__getattr__` 透传 langchain / langgraph 原生导入。
- 不新增运行时逻辑；纯类型与函数引用。

#### 允许的依赖方向

- → （仅依赖 LangChain / LangGraph 原生包；本模块位于 primitives 层最底层）

#### 禁止的依赖方向

- × `runtime_*` / `cli_*` / `protocol_*` / `cross_cutting_*`（primitives 层不依赖任何上层）

> **review.md M-3 修复后**：本模块是分层约束的核心支撑。测试用 `grep -E '^(from|import) (langchain|langgraph)' langagent/{runtime,cross_cutting,protocol,cli}/*.py` 应无输出（CI 校验）。

---

### `primitives_state_reducers` {#mod-primitives-state-reducers}

> `primitives` 层模块 5（**review.md v0.4.0 M-4 方案 C 修复新增**）：AgentState 5 字段自定义 reducer 函数集合；与 `primitives_langchain_types` 同级，承载 LangGraph `Annotated[..., reducer]` 协议扩展。

#### 职责

- 主职责：定义 **3 个唯一 reducer 函数**（`replace_with_merge` / `merge_dict` / `overwrite_or_merge`），覆盖 `AgentState` 的 4 个自定义字段（`todos` / `files` / `context` / `scratchpad`；`replace_with_merge` 被 `todos` 与 `scratchpad` 共用）；`messages` 字段的 `add_messages` reducer 由 `primitives_langchain_types` re-export LangGraph 内置提供，不在本模块。
- 副职责：保证 reducer 函数作为 LangGraph 原语扩展放在 primitives 层（与 `primitives_langchain_types` 同级）；F05 AgentState TypedDict 通过 `from langagent.primitives.state_reducers import ...` 单向依赖 primitives；F10 `primitives_state_graph_builder.build()` 同样通过 primitives 层自给自足注入 reducer，无分层冲突。

#### 关键 API

```python
# 3 个唯一 reducer 函数（pure function；签名见 module_schemas.md#schema-state-reducers）
def replace_with_merge(current: list[dict[str, Any]] | None, update: list[dict[str, Any]] | None) -> list[dict[str, Any]]: ...
def merge_dict(current: dict[str, dict[str, Any]] | None, update: dict[str, dict[str, Any]] | None) -> dict[str, dict[str, Any]]: ...
def overwrite_or_merge(current: dict[str, Any] | None, update: dict[str, Any] | None, *, mode: Literal['overwrite', 'merge_with_prior'] = 'merge_with_prior') -> dict[str, Any]: ...
# messages 字段的 add_messages reducer 由 primitives_langchain_types re-export，不在本模块
```

#### 允许的依赖方向

- → （无；纯函数定义，不依赖任何具体实现；与 `primitives_langchain_types` 同级，间接依赖 LangGraph 内置 reducer 协议）

#### 禁止的依赖方向

- × `runtime_*` / `cli_*` / `protocol_*` / `cross_cutting_*`（primitives 层不依赖任何上层）

> **review.md M-4 方案 C 修复后**：reducer 函数下沉到 primitives 层消除 primitives → runtime 反向依赖违例；与 `primitives_langchain_types` 共同构成"primitives 层是 LangChain / LangGraph 原语 + 原语扩展的唯一接触面"语义。F05 §三.2 AgentState TypedDict 改为 `from langagent.primitives.state_reducers import replace_with_merge, merge_dict, overwrite_or_merge`；F05 不再持有 reducer 函数实现（仅持有 TypedDict 定义）。
>
> **review.md v1.0.0 P1-4 修复**：模块实际承载 **3 个唯一 reducer 函数**（不是 4 个），覆盖 AgentState 的 4 个自定义字段——`replace_with_merge` 被 `todos` 与 `scratchpad` 共用，`merge_dict` 仅 `files`，`overwrite_or_merge` 仅 `context`。`messages` 字段的 `add_messages` reducer 由 LangGraph 内置提供，不在本模块。`module_schemas.md#schema-state-reducers` 与 `F10 §三.1` 已统一为 3 个；本节同步修正。

---

## 模块间依赖矩阵

> 完整对称方阵，**21 × 21 = 441 单元格**（**review.md v0.2.0 M-3 修复后 18 × 18**；**v0.4.0 M-4 方案 C 修复后新增 `primitives_state_reducers`，18 → 19**；**v0.4.0 M-NEW-2 方案 B 修复后新增 2 条硬例外单向边**；**v2.3.0 review.md v2.2.2 P0-1 修复后新增 `cross_cutting_stage_guard` 模块，19 → 20；新增 6 条 runtime_*/primitives_* → cross_cutting_stage_guard 边 + 1 条 primitives_state_graph_builder → cross_cutting_guardrail_middleware 边（P0-2 修复）**；**v2.4.0 review.md v1.0.0 P0-1 + v2.2.2 P1-3 修复后新增 `eval_runner` 行/列，20 → 21；新增 2 条 `runtime_main_loop_dispatcher → {primitives_chat_model_factory, primitives_checkpoint_adapter}` 硬例外单向边**）；每行每列每个单元格必须填满一个符号（不留空白、不留 NA）。
> 4 符号语义（Q7）：`→` 强单向允许依赖；`↔` 双向允许依赖；`×` 明确禁止依赖；`–` 无依赖关系（对角线亦为 `–`）。
> 自反对角线一律为 `–`。
> `→` 与 `↔` 的边集合（即"允许依赖"边）必须无回路（构造有向图跑拓扑排序验证）。
> **硬例外单向边（v0.4.0 M-NEW-2 修复后 + v2.3.0 P0-1/P0-2 + v2.4.0 P0-1 修复后共 11 条）**：
>   - `primitives_chat_model_factory → cross_cutting_logger` + `primitives_state_graph_builder → cross_cutting_logger`（v0.4.0 M-NEW-2，2 条）：primitives 层调用 cross_cutting logger 的 `emit()` 接口发射 model_adapt / graph_compose 阶段 9 个 tag；logger 是被动接口，不反向依赖 primitives；CHK-AR-021 校验单向性
>   - `runtime_dir_loader` / `runtime_config_resolver` / `runtime_main_loop_dispatcher` / `runtime_exit_handler` / `primitives_chat_model_factory` / `primitives_state_graph_builder` → `cross_cutting_stage_guard`（v2.3.0 P0-1，6 条）：4 个 runtime + 2 个 primitives 模块应用 `@stage_guard_decorator` 包裹 6 阶段入口函数实施阶段能力边界；stage_guard_decorator 是被动接口，不反向依赖调用方；CHK-AR-023 校验 6 阶段装饰器应用
>   - `primitives_state_graph_builder → cross_cutting_guardrail_middleware`（v2.3.0 P0-2，1 条）：F10 §3.4a 步骤 5 实例化系统护栏 middleware；guardrail_middleware 是被动接口（`build_middleware(policy)` 构造方法），不反向依赖 F10；CHK-AR-024 校验单向性
>   - `runtime_main_loop_dispatcher → primitives_chat_model_factory` + `runtime_main_loop_dispatcher → primitives_checkpoint_adapter`（v2.4.0 P0-1，2 条）：F05 `build_doctor_probes()` API 内部 import primitives 实例化 BaseChatModel / BaseCheckpointSaver 后包装为 probe 函数对；primitives 是被动接口（`create(config)` 构造方法），不反向依赖 F05；CHK-AR-025 校验 F05 `langagent/runtime/main_loop_dispatcher.py` 中两个 import 路径

| module ↓ \ module → | cli_runner | cli_parser | cli_output_formatter | runtime_dir_loader | runtime_config_resolver | runtime_main_loop_dispatcher | runtime_exit_handler | protocol_event_bus | protocol_skill_loader | protocol_tool_registry | cross_cutting_logger | cross_cutting_metrics_collector | cross_cutting_audit_recorder | cross_cutting_guardrail_middleware | cross_cutting_stage_guard | primitives_chat_model_factory | primitives_state_graph_builder | primitives_checkpoint_adapter | primitives_langchain_types | primitives_state_reducers | eval_runner |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cli_runner | – | → | → | → | → | → | → | – | – | – | – | – | – | – | – | – | – | – | – | – | → |
| cli_parser | – | – | – | – | → | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| cli_output_formatter | – | – | – | – | – | – | → | → | – | – | – | – | – | – | – | – | – | – | – | – | – |
| runtime_dir_loader | – | – | – | – | – | – | – | – | → | → | → | – | – | – | **→¹** | – | – | – | – | – | – |
| runtime_config_resolver | – | – | – | – | – | – | – | – | – | – | → | – | – | – | **→¹** | – | – | – | – | – | – |
| runtime_main_loop_dispatcher | – | – | – | – | – | – | – | → | – | – | → | → | → | → | **→¹** | **→²** | → | **→²** | – | → | – |
| runtime_exit_handler | – | – | – | – | – | – | – | → | – | – | → | → | → | – | **→¹** | – | – | – | → | – | – |
| protocol_event_bus | – | – | – | – | – | – | – | – | – | – | → | – | – | – | – | – | – | – | – | – | – |
| protocol_skill_loader | – | – | – | – | – | – | – | → | – | – | → | – | – | – | – | – | – | – | – | – | – |
| protocol_tool_registry | – | – | – | – | – | – | – | → | – | – | → | – | – | – | – | – | → | – | – | – | – |
| cross_cutting_logger | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| cross_cutting_metrics_collector | – | – | – | – | – | – | – | → | – | – | → | – | – | – | – | – | – | – | – | – | – |
| cross_cutting_audit_recorder | – | – | – | – | – | – | – | → | – | – | → | – | – | – | – | – | – | – | – | – | – |
| cross_cutting_guardrail_middleware | – | – | – | – | – | – | – | → | – | – | → | – | → | – | – | – | → | – | – | – | – |
| cross_cutting_stage_guard | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| primitives_chat_model_factory | – | – | – | – | – | – | – | – | – | – | **→¹** | – | – | – | **→¹** | – | – | – | – | – | – |
| primitives_state_graph_builder | – | – | – | – | – | – | – | – | – | – | **→¹** | – | – | **→²** | **→¹** | – | – | – | – | – | – |
| primitives_checkpoint_adapter | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| primitives_langchain_types | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| primitives_state_reducers | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |
| eval_runner | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – |

> ¹ **硬例外单向边 v0.4.0 M-NEW-2 + v2.3.0 P0-1（共 8 条）**：`primitives_chat_model_factory → cross_cutting_logger` + `primitives_state_graph_builder → cross_cutting_logger`（v0.4.0 M-NEW-2 方案 B，2 条；logger 是被动接口）；`runtime_dir_loader` / `runtime_config_resolver` / `runtime_main_loop_dispatcher` / `runtime_exit_handler` / `primitives_chat_model_factory` / `primitives_state_graph_builder` → `cross_cutting_stage_guard`（v2.3.0 P0-1，6 条；stage_guard_decorator 是被动接口）。CHK-AR-021 + CHK-AR-023 校验单向性。
>
> ² **硬例外单向边 v2.3.0 P0-2 + v2.4.0 P0-1（共 3 条）**：`primitives_state_graph_builder → cross_cutting_guardrail_middleware`（v2.3.0 P0-2，1 条；F10 §3.4a 步骤 5 实例化系统护栏 middleware；guardrail_middleware `build_middleware(policy)` 是被动构造方法）；`runtime_main_loop_dispatcher → primitives_chat_model_factory` + `runtime_main_loop_dispatcher → primitives_checkpoint_adapter`（v2.4.0 P0-1，2 条；F05 `build_doctor_probes()` API 内部 import primitives 实例化后包装为 probe 函数对；primitives `create(config)` 是被动构造方法）。CHK-AR-024 + CHK-AR-025 校验单向性（`cross_cutting_guardrail_middleware` / `primitives_chat_model_factory` / `primitives_checkpoint_adapter` 不得反向依赖 F05 / F10）。
>
> **回路验证**：上述矩阵中所有 `→` 边的集合 = {cli → runtime, cli → protocol, cli → eval_runner (v2.4.0 P1-3), runtime → protocol, runtime → cross_cutting, runtime → primitives, runtime → cross_cutting_stage_guard (v2.3.0 P0-1), runtime → primitives_state_reducers (F05 AgentState import), runtime → primitives_chat_model_factory + primitives_checkpoint_adapter (v2.4.0 P0-1 hard-exception 2), protocol → cross_cutting, cross_cutting_guardrail_middleware → primitives (类型注解), primitives_* → cross_cutting_logger (v0.4.0 硬例外 2 条), primitives_* / runtime_* → cross_cutting_stage_guard (v2.3.0 P0-1 硬例外 6 条), primitives_state_graph_builder → cross_cutting_guardrail_middleware (v2.3.0 P0-2 硬例外 1 条)}。构造有向图跑拓扑排序：cli → {runtime, eval_runner}；cli → eval_runner → (无下游，无反向边回到 cli/runtime/primitives/cross_cutting，eval_runner 节点不参与反向依赖图)；runtime → {protocol, cross_cutting, primitives, primitives_state_reducers, cross_cutting_stage_guard, primitives_chat_model_factory, primitives_checkpoint_adapter}；cross_cutting_stage_guard → (无下游)；eval_runner 不被任何 module 依赖（除 cli_runner 主动调用），无回路。
> **依赖方向约束**：所有 `→` 边均从高层指向低层（cli / runtime / protocol / cross_cutting → primitives / primitives_state_reducers / cross_cutting_stage_guard / eval_runner）；cross_cutting 自身不依赖任何业务层（除 primitives 类型注解外）。**11 条硬例外单向边**（2 条 logger + 6 条 stage_guard + 1 条 guardrail_middleware + 2 条 F05 build_doctor_probes）全部已登记并校验。

---

## 模块到 Feature 拆分映射表

> 列：`module_id` / `feature_id` / `职责` / `依赖的下游模块`。
> `feature_id` 取值 `F01`..`F10+`；**不得出现 `F00`**（FR-024）。

| module_id | feature_id | 职责 | 依赖的下游模块 |
|---|---|---|---|
| `cli_runner` | F01 | CLI 入口解析与子命令分发 | `cli_parser`、`runtime_dir_loader`、`runtime_main_loop_dispatcher`、`runtime_exit_handler`、`runtime_config_resolver`、**`eval_runner`**（**v0.5.0 评审 v0.1.0 §四.C-5 修复新增 + v2.4.0 P1-3 修复后 21st module_id 显式登记**：F11 跨 runtime/cli 整合模块，`langagent eval` 子命令 dispatch 委托；F01 `from langagent.eval.runner import run`） |
| `cli_parser` | F01 | argparse schema 定义与转换 | `cli_runner`、`runtime_config_resolver` |
| `cli_output_formatter` | F01 | 终端输出格式化 | `runtime_exit_handler`、`protocol_event_bus` |
| `runtime_dir_loader` | F02 | 智能体目录加载（阶段 1 `dir_load`） | `protocol_skill_loader`、`protocol_tool_registry`、`cross_cutting_logger`、**`cross_cutting_stage_guard`**（**v2.3.0 P0-1 修复后**：F02 `runtime_dir_loader.load()` 应用 `@stage_guard_decorator('dir_load')` 实施阶段能力边界） |
| `runtime_config_resolver` | F03 | 配置解析（阶段 2 `config_resolve`） | `cli_parser`、`cross_cutting_logger`、**`cross_cutting_stage_guard`**（**v2.3.0 P0-1 修复后**：F03 `runtime_config_resolver.resolve()` 应用装饰器） |
| `runtime_main_loop_dispatcher` | F05 | 主循环调度（阶段 5 `main_loop`） | `primitives_state_graph_builder`、`protocol_event_bus`、`cross_cutting_metrics_collector`、`cross_cutting_audit_recorder`、`cross_cutting_guardrail_middleware`、`cross_cutting_logger`、**`cross_cutting_stage_guard`**（**v2.3.0 P0-1 修复后**：F05 `main_loop_dispatcher.run_until_done()` 应用装饰器）、**`primitives_chat_model_factory` + `primitives_checkpoint_adapter`**（**v2.4.0 P0-1 修复后 2 条硬例外单向边**：F05 `build_doctor_probes()` API 内部 import；仅限 `build_doctor_probes` 函数体；CHK-AR-025 校验） |
| `runtime_exit_handler` | F06 | 退出清理（阶段 6 `exit_cleanup`） | 所有 runtime 模块、`protocol_event_bus`、`cross_cutting_audit_recorder`、`cross_cutting_metrics_collector`、`cross_cutting_logger`、**`cross_cutting_stage_guard`**（**v2.3.0 P0-1 修复后**：F06 `exit_handler.cleanup()` 应用装饰器） |
| `protocol_event_bus` | F07 | Event 总线 | `cross_cutting_logger`、`cross_cutting_audit_recorder` |
| `protocol_skill_loader` | F04 | SkillSpec 加载 | `cross_cutting_logger`、`protocol_event_bus` |
| `protocol_tool_registry` | F04 | ToolSpec 注册 | `primitives_chat_model_factory`（类型注解）、`cross_cutting_logger`、`protocol_event_bus` |
| `cross_cutting_logger` | F08 | 结构化日志 | （无） |
| `cross_cutting_metrics_collector` | F08 | MetricsSnapshot 收集 | `cross_cutting_logger`、`protocol_event_bus` |
| `cross_cutting_audit_recorder` | F09 | AuditEntry 写入 | `cross_cutting_logger`、`protocol_event_bus` |
| `cross_cutting_guardrail_middleware` | F09 | 护栏 middleware | `primitives_chat_model_factory`（类型注解）、`cross_cutting_audit_recorder`、`cross_cutting_logger`、`protocol_event_bus` |
| `cross_cutting_stage_guard` | **F02**（**v2.3.0 P0-1 修复后**：F02 首批实现 `langagent/cross_cutting/stage_guard.py` 公开 API，被 F02/F03/F05/F06/F10 复用） | 阶段能力边界装饰器 | （无；横切层基础设施） |
| `primitives_chat_model_factory` | F10 | BaseChatModel 工厂 | `cross_cutting_logger`（**v0.4.0 M-NEW-2 修复后硬例外单向边**，发射 4 个 model_adapt tag）、**`cross_cutting_stage_guard`**（**v2.3.0 P0-1 修复后硬例外单向边**：`chat_model_factory.create()` 入口应用 `@stage_guard_decorator('model_adapt')`） |
| `primitives_state_graph_builder` | F10 | CompiledStateGraph 构造 | `primitives_langchain_types`（类型注解）、`primitives_state_reducers`（v0.4.0 M-4 方案 C 修复后注入 reducer）、`cross_cutting_logger`（**v0.4.0 M-NEW-2 修复后硬例外单向边**，发射 5 个 graph_compose tag）、**`cross_cutting_guardrail_middleware`**（**v2.3.0 P0-2 修复后硬例外单向边**：F10 §3.4a 步骤 5 实例化系统护栏）、**`cross_cutting_stage_guard`**（**v2.3.0 P0-1 修复后硬例外单向边**：`state_graph_builder.build()` 入口应用 `@stage_guard_decorator('graph_compose')`） |
| `primitives_checkpoint_adapter` | F10 | BaseCheckpointSaver 适配 | （无） |
| `primitives_langchain_types` | F10 | LangChain / LangGraph 原生类型 re-export | （无；仅 import langchain / langgraph） |
| `primitives_state_reducers` | **F10**（**v0.4.0 M-4 方案 C 修复新增**） | AgentState 5 字段自定义 reducer 函数集合 | （无；纯函数定义） |
| **`eval_runner`**（**v2.4.0 P1-3 修复后 21st module_id**） | **F11**（**v2.4.0 P1-3 修复后**：F11 拥有 `langagent/eval/runner.py`；F01 dispatch `from langagent.eval.runner import run`） | `langagent eval` 子命令整合入口 | `cli_runner`（**F01 dispatch 显式 import**；runner 不 import cli 层任何符号） |

---

## 静态约束 CI 校验清单

> 至少 12 条（FR-025 / R-1.2）；每条以 `CHK-AR-NNN | 描述 | 实现方式（grep / ripgrep / AST）` 形式书写。
> 实现方式列不得包含"人工"二字。

- `CHK-AR-001 | workflow.md 行数 ≥ 200 | grep -cE '^' workflow.md 输出 ≥ 200`
- `CHK-AR-002 | architecture_modules.md 行数 ≥ 200 | grep -cE '^' architecture_modules.md 输出 ≥ 200`
- `CHK-AR-003 | module_schemas.md 行数 ≥ 200 | grep -cE '^' module_schemas.md 输出 ≥ 200`
- `CHK-AR-004 | 3 份文档均为 UTF-8 编码且无 BOM 且 LF 行尾 | file --mime-encoding workflow.md architecture_modules.md module_schemas.md 输出均为 utf-8；head -c 3 <file> | xxd 不含 efbbbf；grep -q $'\r' <file> 输出非 0`
- `CHK-AR-005 | 阶段锚点命名空间符合 FR-041 | grep -cE '\{#stage-(dir_load|config_resolve|model_adapt|graph_compose|main_loop|exit_cleanup)\}' workflow.md 输出 = 6`
- `CHK-AR-006 | 模块锚点命名空间符合 FR-041 | grep -cE '\{#mod-[a-z][a-z0-9-]+\}' architecture_modules.md 输出 = 21`（**review.md v0.5.0 §四.C-4 修复**：原值 15 已过期；v0.4.0 M-4 方案 C 修复后模块总数 18 → 19；v0.5.0 评审 v0.1.0 §二.A.3 方案 A 修复后 EventBusProtocol 接口合并入 logger，模块总数仍为 19；**v2.3.0 review.md v2.2.2 P0-1 修复后新增 `cross_cutting_stage_guard`，19 → 20**；**v2.4.0 review.md v1.0.0 P1-3 修复后新增 `eval_runner`，20 → 21**）
- `CHK-AR-007 | schema 锚点命名空间符合 FR-041 | grep -cE '\{#schema-(agent-state|state-reducers|runtime-config|loaded-agent|middleware-spec|channel-spec|channel-context|sandbox-spec|schedule-spec|memory-spec|identity-spec|eval-task-spec|event|metrics-snapshot|audit-entry|doctor-report|eval-report|eval-run-result|skill-spec-frontmatter|tool-spec-side-effect|span-trace|runtime-config-snapshot)\}' module_schemas.md 输出 ≥ 22`（**review.md v0.5.0 §二.A.1 修复**：新增 `eval-run-result` 锚点；总数 21 → 22）
- `CHK-AR-008 | 退出码锚点命名空间符合 FR-041 | grep -cE '\{#exit-code-[0-9]+\}' workflow.md 输出 = 13`（**review.md v0.5.0 §四.C-7 修复**：原 12 已过期；新增退出码 67 = name_already_exists）
- `CHK-AR-009 | 日志标签锚点命名空间符合 FR-041 | grep -cE '\{#log-tag-la-[a-z0-9-]+\}' workflow.md 输出 ≥ 15`
- `CHK-AR-010 | 依赖矩阵 4 符号完整且无回路 | python3 脚本提取矩阵 → 拓扑排序 → 输出无回路`
- `CHK-AR-011 | 依赖矩阵对角线均为 `–` | grep -E '^cli_runner.*cli_runner.*–' 验证对角线符号`
- `CHK-AR-012 | module_id 全局唯一 | grep -oE '\{#mod-[a-z][a-z0-9-]+\}' architecture_modules.md | sort | uniq -d 输出为空`
- `CHK-AR-013 | 跨 3 份文档无 LangSmith 闭源依赖（langsmith / LANGSMITH_* / LANGCHAIN_TRACING_* / LANGCHAIN_API_KEY 等） | 实施者按 quickstart.md QS-1.3 LangSmith 扫描脚本输出为空`
- `CHK-AR-014 | 跨 3 份文档无硬编码密钥 / 内网 IP / 绝对路径（具体模式清单见 spec.md SC-004） | 实施者按 quickstart.md QS-1.3 硬编码扫描脚本输出为空`
- `CHK-AR-015 | 跨 3 份文档不出现 FR-043 / SC-005 占位词列表（详见 spec.md FR-043 字面量清单） | 实施者按 quickstart.md QS-1.3 占位词扫描脚本输出为空`
- `CHK-AR-016 | module_id 总数 ≥ 12 | grep -cE '\{#mod-[a-z][a-z0-9-]+\}' architecture_modules.md 输出 ≥ 12`（**review.md v0.2.0 修复后实际值 = 18**；**v0.4.0 M-4 方案 C 修复后新增 `primitives_state_reducers`，实际值 = 19**；**v0.5.0 评审 v0.1.0 §二.A.3 方案 A 修复后 EventBusProtocol 接口合并入 cross_cutting_logger，模块总数仍为 19；**v2.3.0 review.md v2.2.2 P0-1 修复后新增 `cross_cutting_stage_guard`，19 → 20；**v2.4.0 review.md v1.0.0 P1-3 修复后新增 `eval_runner`，20 → 21**）
- `CHK-AR-017 | 每层 module_id 数量 ≥ 2 | python3 脚本按 5 层分组统计 → 每层 ≥ 2`（**v2.3.0 P0-1 修复后**：cross_cutting 层 4 → 5；其它 4 层数量不变：cli 3 / runtime 4 / protocol 3 / primitives 5）
- `CHK-AR-018 | 跨 3 份文档阶段名 / 退出码 / 日志标签字面量完全一致（SC-003）| python3 脚本构造 3 张字面量表交叉比对 → 输出一致`
- `CHK-AR-019 | feature_id 列不含 F00 | grep -E 'F00' architecture_modules.md 中"模块到 Feature 拆分映射表"小节输出为空`
- `CHK-AR-020 | 3 份文档之间无死链（SC-002）| python3 脚本扫描 `](#...)` 与 `](...md#...)` 引用 → 全部可解析`
- `CHK-AR-021 | primitives_* → cross_cutting_logger 硬例外单向边约束（review.md v0.4.0 M-NEW-2 方案 B 修复新增）| grep -E '^cross_cutting_logger.*primitives_(chat_model_factory|state_graph_builder)' architecture_modules.md 矩阵应为空（反向禁止依赖）；正向 `primitives_.* → cross_cutting_logger` 已在矩阵中显式登记（带 →¹ 标记）`
- `CHK-AR-022 | AgentState reducer 函数位于 primitives 层（review.md v0.4.0 M-4 方案 C 修复新增）| grep -E 'def (replace_with_merge|merge_dict|overwrite_or_merge)' langagent/runtime/agent_state.py 应为空（reducer 不在 runtime 层）；grep -E 'def (replace_with_merge|merge_dict|overwrite_or_merge)' langagent/primitives/state_reducers.py 应至少 3 个匹配`
- `CHK-AR-023 | 6 阶段装饰器应用约束（review.md v2.2.2 P0-1 修复新增）| grep -E '@cross_cutting_stage_guard_decorator\("(dir_load|config_resolve|model_adapt|graph_compose|main_loop|exit_cleanup)"' langagent/runtime/dir_loader.py langagent/runtime/config_resolver.py langagent/runtime/main_loop_dispatcher.py langagent/runtime/exit_handler.py langagent/primitives/chat_model_factory.py langagent/primitives/state_graph_builder.py 应至少各 1 个匹配（共 6 个函数入口）；grep -E '^from langagent\.cross_cutting\.stage_guard' langagent/runtime/*.py langagent/primitives/*.py 应至少 6 个匹配（import 语句）`
- `CHK-AR-024 | primitives_state_graph_builder 实例化系统护栏 middleware 约束（review.md v2.2.2 P0-2 修复新增）| grep -E 'from langagent\.cross_cutting\.guardrail_middleware import build_middleware' langagent/primitives/state_graph_builder.py 应至少 1 个匹配；grep -E 'build_middleware\(policy=RuntimeConfig\.guardrail_policy\)' langagent/primitives/state_graph_builder.py 应至少 1 个匹配；反向 `cross_cutting_guardrail_middleware → primitives` 应为空（grep -E '^from langagent\.primitives' langagent/cross_cutting/guardrail_middleware.py 应为空）`
- `CHK-AR-025 | F05 build_doctor_probes 2 条硬例外单向边约束（review.md v1.0.0 P0-1 + v2.4.0 修复新增）| grep -E '^from langagent\.primitives\.chat_model_factory import' langagent/runtime/main_loop_dispatcher.py 应至少 1 个匹配（`build_doctor_probes()` 内部 import）；grep -E '^from langagent\.primitives\.checkpoint_adapter import' langagent/runtime/main_loop_dispatcher.py 应至少 1 个匹配；反向 `primitives_chat_model_factory → runtime_main_loop_dispatcher` 与 `primitives_checkpoint_adapter → runtime_main_loop_dispatcher` 应为空（grep -E '^from langagent\.runtime\.main_loop_dispatcher' langagent/primitives/chat_model_factory.py langagent/primitives/checkpoint_adapter.py 应为空）`
- `CHK-AR-026 | F11 5 graders `grade()` 函数存在性约束（review.md v2.4.0 P2-3 修复新增）| grep -E '^def grade\(' langagent/eval/graders/exact_match.py langagent/eval/graders/contains.py langagent/eval/graders/regex.py langagent/eval/graders/llm_judge.py langagent/eval/graders/tool_call_match.py 应至少各 1 个匹配（共 5 个 grader 入口）；grep -E '^GRADER_REGISTRY' langagent/eval/graders/__init__.py 应至少 1 个匹配（路由表登记）`

---

## 交叉引用

> 本节列出 architecture_modules.md 对其它 2 份设计文档的相对路径 + 锚点引用（FR-040 / FR-041）。
> 不带 `./` 前缀、不带 `../` 前缀（FR-040）。

### 引用 workflow.md

- 阶段锚点示例：`workflow.md#stage-dir_load`（目录加载阶段）。
- 阶段锚点示例：`workflow.md#stage-main_loop`（主循环阶段）。
- 退出码锚点示例：`workflow.md#exit-code-70`（EX_SOFTWARE）。
- 日志标签锚点示例：`workflow.md#log-tag-la-runtime-main-loop-start`。

### 引用 module_schemas.md

- Schema 锚点示例：`module_schemas.md#schema-agent-state`（AgentState 5 字段 reducer）。
- Schema 锚点示例：`module_schemas.md#schema-runtime-config`（RuntimeConfig 优先级链）。
- Schema 锚点示例：`module_schemas.md#schema-tool-spec-side-effect`（ToolSideEffect 7 枚举）。
- Schema 锚点示例：`module_schemas.md#schema-span-trace`（Span / Trace 合并章节）。

### 引用宪法

- `../../.specify/memory/constitution.md#第-I-条`（项目身份与边界）。
- `../../.specify/memory/constitution.md#第-II-条`（技术栈与依赖范围）。
- `../../.specify/memory/constitution.md#第-XIII-条`（禁止项）。

---

## 变更日志

| 日期 | 版本 | 修订摘要 | 作者 |
|---|---|---|---|
| 2026-09-14 | v0.1.0 | Feature 00 初版 | 项目维护者 |
| 2026-09-15 | v0.2.0 | review.md M-3 / M-4 修复：<br>- 新增 `primitives_langchain_types` 模块（review.md M-3 修复）；5 层模块总数 17 → 18<br>- `primitives_state_graph_builder` 增加 `primitives_langchain_types` 依赖方向（类型注解）<br>- 模块清单脚注新增 `eval_runner`（跨 runtime/cli 整合模块，由 F11 提供，不计入 18 个 module_id 计数）<br>- 依赖矩阵 17×17 → 18×18（324 单元格） | 评审者 |
| 2026-09-15 | v0.3.0 | review.md 全部 21 个 issue 在 v0.3.0 修复完成后再次校核；版本号与 feature/README.md v0.3.0 同步对齐 | 评审者 |
| 2026-09-15 | v0.4.0 | review.md v0.3.0 M-NEW-2 / M-4 方案 C 修复：<br>- **M-NEW-2 方案 B**：依赖矩阵登记 2 条硬例外单向边 `primitives_chat_model_factory → cross_cutting_logger` + `primitives_state_graph_builder → cross_cutting_logger`（带 →¹ 标记）；新增 CHK-AR-021 校验硬例外单向性<br>- **M-4 方案 C**：新增 `primitives_state_reducers` 模块（reducer 函数从 F05 runtime 层下沉到 primitives 层）；5 层模块总数 18 → 19；primitives 层 4 → 5 个；依赖矩阵 18×18 → 19×19（361 单元格）；新增 CHK-AR-022 校验 reducer 函数位于 primitives 层<br>- 模块到 Feature 拆分映射表追加 `primitives_state_reducers | F10` 行；`primitives_chat_model_factory` / `primitives_state_graph_builder` 行的"依赖的下游模块"列补充硬例外边 + primitives_state_reducers 依赖<br>- CHK-AR-016 实际值同步 18 → 19 | 评审者 |
| 2026-09-16 | v2.3.0 | review.md v2.2.2 P0-1 方案 A' + P0-2 修复：<br>- **P0-1 方案 A'（review.md v2.2.2）**：`stage_guard.py` 从 `langagent/runtime/stage_guard.py`（F02 内部工具）移到 `langagent/cross_cutting/stage_guard.py`；新增 `cross_cutting_stage_guard` 模块（cross_cutting 层 4 → 5）；5 层模块总数 19 → **20**；依赖矩阵 19×19 → **20×20 = 400 单元格**；新增 6 条硬例外单向边（`runtime_dir_loader` / `runtime_config_resolver` / `runtime_main_loop_dispatcher` / `runtime_exit_handler` / `primitives_chat_model_factory` / `primitives_state_graph_builder` → `cross_cutting_stage_guard`）；6 阶段入口函数（`load` / `resolve` / `create` / `build` / `run_until_done` / `cleanup`）应用 `@cross_cutting_stage_guard_decorator` 实施 model_adapt / graph_compose 阶段能力边界技术保障；新增 CHK-AR-023 校验装饰器应用<br>- **P0-2 修复**：新增 1 条硬例外单向边 `primitives_state_graph_builder → cross_cutting_guardrail_middleware`（带 →² 标记）；F10 §3.4a 步骤 5 实例化系统护栏 middleware；新增 CHK-AR-024 校验单向性<br>- **依赖矩阵硬例外单向边累计 9 条**：2 条 logger + 6 条 stage_guard + 1 条 guardrail_middleware<br>- 模块到 Feature 拆分映射表新增 `cross_cutting_stage_guard | F02` 行；4 个 runtime + 2 个 primitives 行的"依赖的下游模块"列补充 `cross_cutting_stage_guard`；`primitives_state_graph_builder` 行额外补充 `cross_cutting_guardrail_middleware`<br>- CHK-AR-006 实际值同步 19 → **20**；CHK-AR-016 实际值同步 19 → **20**；CHK-AR-017 cross_cutting 层数量 4 → 5<br>- v1.1.0 P0-2 修复同步：`LoadedAgent` 5 字段无 `compiled_graph`（schema_version v0.2.0）—— 模块清单无变化（19 → 20 增量由 P0-1 引入），但 schema 在 `module_schemas.md` 同步；模块到 Feature 拆分映射表无新增/移除行<br>- **本文件主版本号同步 v2.1.0 → v2.3.0**（独立演进路径：module_schemas.md 主版本号独立演进 v1.2.0；详见 README.md §五 changelog v2.2.2 行 P2-3 修复） | 评审者 |
| 2026-09-16 | **v2.4.0** | review.md v1.0.0 / v2.2.2 P0-1 + v1.0.0 P1-3 + v2.4.0 P2-3 修复（**本轮由 feature/review.md 评审识别并应用**）：<br>- **P0-1 修复（v1.0.0 review.md）**：F05 `build_doctor_probes()` API（v1.0.0 P0-1 新增）需要 import `primitives_chat_model_factory` + `primitives_checkpoint_adapter` 构造 doctor probe 函数对，违反 F05 既有禁止依赖方向。**新增 2 条硬例外单向边**（带 →² 标记）：`runtime_main_loop_dispatcher → primitives_chat_model_factory` + `runtime_main_loop_dispatcher → primitives_checkpoint_adapter`；`build_doctor_probes` 是被动构造方法，primitives 不反向依赖 F05；新增 CHK-AR-025 校验单向性<br>- **P1-3 修复（v2.2.2 review.md）**：`eval_runner` 从"跨层整合模块脚注"升级为 21st 显式 module_id（与 `eval_runner` 行/列进入依赖矩阵；`cli_runner → eval_runner` 显式登记边；其他 20 module × `eval_runner` / `eval_runner` × 20 module 全填 `–`）；依赖矩阵 20×20 → **21×21 = 441 单元格**；模块到 Feature 拆分映射表追加 `eval_runner | F11` 行；`cli_runner` 行的"依赖的下游模块"列 `eval_runner` 描述对齐 v2.4.0 显式 module 归属；模块清单脚注 `eval_runner` 描述更新为 21st module_id 显式登记<br>- **P2-3 修复**：模块清单脚注增 5 graders 描述（`langagent/eval/graders/{exact_match,contains,regex,llm_judge,tool_call_match}.py`；统一接口 `grade(actual, expected, **kwargs) -> bool`；`__init__.py` 提供 `GRADER_REGISTRY` 路由表；不计入 21 个 module_id 计数；与 `eval_runner` 同属 F11 跨层整合模块）；新增 CHK-AR-026 校验 5 graders `grade()` 函数存在性 + `GRADER_REGISTRY` 路由表登记<br>- **依赖矩阵硬例外单向边累计 11 条**：2 条 logger + 6 条 stage_guard + 1 条 guardrail_middleware + 2 条 F05 build_doctor_probes<br>- **F05 模块描述**"关键 API"增 `build_doctor_probes()` 一行（review.md v1.0.0 P0-1）；"允许的依赖方向"增 2 行 primitives_chat_model_factory + primitives_checkpoint_adapter（带 v2.4.0 硬例外说明）；"禁止的依赖方向"对 primitives_chat_model_factory / primitives_checkpoint_adapter 加 `build_doctor_probes` 例外说明<br>- CHK-AR-006 实际值同步 20 → **21**；CHK-AR-016 实际值同步 20 → **21**；新增 CHK-AR-025 + CHK-AR-026<br>- **本文件主版本号同步 v2.3.0 → v2.4.0** | 评审者（feature/review.md 评审应用） |
