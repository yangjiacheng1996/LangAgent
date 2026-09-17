# Research: Feature 00 — 顶层设计（Top-Level Design）

**Branch**: `000-top-level-design` | **Date**: 2026-09-14 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

> 本文档是 Phase 0 调研产物。Feature 00 是纯文档 Feature——本调研不涉及"选型 / 框架 / 数据库"等代码层决策，而是为 3 份设计文档的"字段细节 / 内容蓝图 / 行数下界"等隐性决策沉淀依据。

## R-1 spec 中残留歧义的再扫描

spec.md 经过 9 轮 clarify 后，Clarifications section 共记录 9 条已澄清决策。但扫描 spec 后，仍发现以下 3 类**未在 Clarifications 中显式消除**的隐性歧义，需要本调研补全决策。

### R-1.1 阶段五栏 / CLI 五栏 / 模块四栏 / schema 四小节 的"内容模板"

**问题描述**：spec FR-011/FR-012/FR-022/FR-033 等多处要求"五栏"或"四栏"必填，但未规定每栏的具体内容模板（用 Markdown 表格？五级标题？小节？）。

**Decision**：统一采用"**Markdown 二级小节 + 项目符号列表**"形式，每栏下挂项目符号列举项；不强制使用 Markdown 表格形式（表格形式在子项超过 5 行时反而难读）。示例模板：

```markdown
### 阶段 5：main_loop {#stage-main_loop}

#### 输入
- `AgentState`（5 字段齐全）
- `runtime_config: RuntimeConfig`
- ...

#### 输出
- 更新后的 `AgentState`（含 `messages` / `todos` / `files` 等）
- ...

#### 失败模式
- `model_timeout`：模型调用超时 → 退出码 70
- `tool_execution_error`：工具执行抛异常 → 退出码 1
- ...

#### 退出码
- 主要：70（EX_SOFTWARE）
- 次要：1 / 130

#### 日志标签
- `la.runtime.main_loop.turn.start`
- `la.runtime.main_loop.turn.end`
- `la.runtime.main_loop.tool_call`
```

**Rationale**：（1）项目符号列表在项数 ≤ 10 时可读性优于表格；（2）列表项可以嵌套子列表表达"主项 / 子项"层级；（3）便于 `grep -E '^- '` 机械核验每栏非空。

**Alternatives considered**：
- **A. Markdown 表格**：5 列表格在 cell 内容长时换行难处理，弃用。
- **B. YAML frontmatter**：破坏 Markdown 可读性，且与"锚点 + 二级小节"惯例冲突，弃用。
- **C. JSON 块**：项目维护者 review 时需切换阅读模式，弃用。

### R-1.2 MDA 能力对照表 / 静态约束 CI 清单 的行数下界

**问题描述**：spec FR-015 / FR-025 要求"MDA 能力对照表"和"静态约束 CI 校验清单"两章必须存在，但未规定**最少行数 / 最少条数**，实施者可能只写 1-2 行凑数。

**Decision**：
- **MDA 能力对照表**：最少 **10 行**。每行对应 1 项 MDA 能力（参考 `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-*.md` 中列出的能力，包括 `agent-definition` / `channels` / `cli` / `deploy` / `evals` / `identity` / `instructions` / `local-development` / `mcp-connectors` / `memory` / `middleware` / `project-structure` / `quickstart` / `sandboxes` / `schedules` / `skills` / `tools` / `tutorial` / `overview`）。LangAgent 至少须覆盖 10 项；无法 1:1 对齐的 MDA 能力在 `notes` 列显式说明（如 "v1 占位" / "本项目剥离"）。
- **静态约束 CI 校验清单**：最少 **12 条**。每条以 `CHK-AR-NNN | 描述 | 实现方式` 形式书写，至少包含：
  - 3 条约束文档存在性 / 行数 / 字符编码（`wc -l` / `file` / `hexdump`）。
  - 3 条约束锚点命名空间（grep `#stage-*` / `#mod-*` / `#schema-*` / `#exit-code-*` / `#log-tag-*`）。
  - 2 条约束依赖矩阵（grep `→ / ↔ / × / –` 各符号 + 拓扑排序）。
  - 2 条约束 module_id 全局唯一性（`grep -oE 'module_id = .*' | sort -u | uniq -d`）。
  - 2 条约束与宪法一致性（`grep -E 'langsmith|LANGSMITH_|LANGCHAIN_TRACING'` 不得出现）。

**Rationale**：10 行 MDA 对齐表保证"参考而非脱钩"；12 条 CI 清单保证"可机械核验而非口号"。

**Alternatives considered**：
- **A. 不设下界**：实施者可能 1 行凑数，与 spec 精神冲突，弃用。
- **B. 20 行 + 20 条**：超出"中等规模"阈值，对 200 行总行数预算不友好，弃用。

### R-1.3 模块 ID 候选集合的初始建议

**问题描述**：spec Key Entities "Architecture Module" 列举了 `agent_state_loader` / `cli_runner` / `main_loop_dispatcher` 等示例 module_id，但未给出完整的"初始模块 ID 候选集合"。实施者在不知道有哪些模块可填的情况下，可能在 `architecture_modules.md` 中只写 5-6 个模块就交差，导致依赖矩阵只有 5-6 行、Feature 拆分映射表也覆盖不全。

**Decision**：在 `architecture_modules.md` 实施时，每层下挂**至少 2 个模块**，总模块数 ≥ 12。初始建议集合（仅供实施者参考，可自由调整）：

| 层 | 建议 module_id（≥ 2 个） | 关联的 schema |
|---|---|---|
| `cli` | `cli_runner` / `cli_parser` | RuntimeConfig |
| `runtime` | `runtime_dir_loader` / `runtime_config_resolver` / `runtime_main_loop_dispatcher` / `runtime_exit_handler` | RuntimeConfig / AgentState |
| `protocol` | `protocol_event_bus` / `protocol_skill_loader` / `protocol_tool_registry` | Event / SkillSpec / ToolSpec |
| `cross_cutting` | `cross_cutting_logger` / `cross_cutting_metrics_collector` / `cross_cutting_audit_recorder` / `cross_cutting_guardrail_middleware` | Span / Trace / MetricsSnapshot / AuditEntry / MiddlewareSpec |
| `primitives` | `primitives_chat_model_factory` / `primitives_state_graph_builder` / `primitives_checkpoint_adapter` | RuntimeConfig / AgentState |

> 实施者**不必**全盘采纳此集合；如需增删，可自由调整 module_id 字面量，但需保证（1）全局唯一、（2）每层 ≥ 2 个、（3）总模块数 ≥ 12、（4）每个 module_id 在"模块→Feature 拆分映射表"中能找到对应 `feature_id`（`F01`..`F10+`）。

**Rationale**：12 个模块是"既能撑起 12×12=144 单元格的依赖矩阵、又不至于文档臃肿"的折衷下界。

**Alternatives considered**：
- **A. 每层仅 1 个模块（5 个总）**：依赖矩阵只 5×5=25 格，无法体现"层间禁止 / 允许"的真实差异，弃用。
- **B. 每层 ≥ 5 个模块（25 个总）**：矩阵 625 格，文档臃肿且实施工作量过大，弃用。

## R-2 LangChain / LangGraph 原生类型引用清单

为统一 `module_schemas.md` 中"与 LangChain/LangGraph 原生类型映射"小节的引用形式，本调研给出权威引用清单（基于 `harness/LangChain_doc/` / `harness/LangGraph_doc/` 本地副本）：

### R-2.1 LangChain 原生类型（仅列可能被 LangAgent schema 引用的）

| LangChain 原生类型 | 来源 | 适用 schema |
|---|---|---|
| `langchain_core.messages.BaseMessage` | `harness/LangChain_doc/` | `AgentState.messages` 元素类型 |
| `langchain_core.messages.HumanMessage` | 同上 | `AgentState.messages` 元素类型（用户消息） |
| `langchain_core.messages.AIMessage` | 同上 | `AgentState.messages` 元素类型（模型回复） |
| `langchain_core.messages.ToolMessage` | 同上 | `AgentState.messages` 元素类型（工具结果） |
| `langchain_core.messages.SystemMessage` | 同上 | `AgentState.messages` 元素类型（系统提示） |
| `langchain_core.tools.BaseTool` | 同上 | `ToolSpec.tool_impl` 类型 |
| `langchain_core.language_models.BaseChatModel` | 同上 | `RuntimeConfig.model` 类型 |
| `langchain.agents.middleware.AgentMiddleware` | 同上 | `MiddlewareSpec.middleware_impl` 类型 |

### R-2.2 LangGraph 原生类型

| LangGraph 原生类型 | 来源 | 适用 schema |
|---|---|---|
| `langgraph.graph.StateGraph` | `harness/LangGraph_doc/` | `LoadedAgent.graph_builder` 类型 |
| `langgraph.graph.CompiledStateGraph` | 同上 | `LoadedAgent.compiled_graph` 类型 |
| `langgraph.checkpoint.BaseCheckpointSaver` | 同上 | `RuntimeConfig.checkpointer` 类型 |
| `langgraph.types.Command` | 同上 | `AgentState.context` 元素类型（human-in-the-loop） |
| `langgraph.types.interrupt` | 同上 | `MiddlewareSpec.hitl_interrupts` 元素类型 |

> 实施者在 `module_schemas.md` 的"与 LangChain/LangGraph 原生类型映射"小节中，**必须使用上表列出的权威名称**（如 `BaseMessage` 而非 `LangChainMessage`），便于 TDD 测试中用 `isinstance(obj, BaseMessage)` 断言。

## R-3 退出码 12 个集合的来源溯源

为 `workflow.md` 实施时"退出码 → 含义 → 触发阶段"表提供权威来源：

| 退出码 | 名称 | 含义 | 触发阶段 | 来源 |
|---|---|---|---|---|
| 0 | `EXIT_SUCCESS` | 成功 | 所有阶段 | POSIX 标准 |
| 1 | `EXIT_FAILURE` | 通用失败 | 所有阶段 | POSIX 标准 |
| 2 | (shell) | 用法错误 | `dir_load` / `config_resolve` | shell 惯例 / Python `argparse` 错误 |
| 3 | (custom) | 数据错误 | `config_resolve` / `main_loop` | 自定义 |
| 4 | (custom) | I/O 错误 | `dir_load` / `exit_cleanup` | 自定义（POSIX `errno` EIO=5 不可直接复用） |
| 5 | (custom) | 配置错误 | `config_resolve` | 自定义（POSIX 同名退出码语义不同，需明确） |
| 64 | `EX_USAGE` | 命令用法错误 | `dir_load` | sysexits.h |
| 65 | `EX_DATAERR` | 数据格式错误 | `config_resolve` | sysexits.h |
| 66 | `EX_NOINPUT` | 缺少输入文件 | `dir_load` | sysexits.h |
| 70 | `EX_SOFTWARE` | 内部软件错误 | `main_loop` | sysexits.h |
| 78 | `EX_CONFIG` | 配置错误 | `config_resolve` | sysexits.h |
| 130 | (SIGINT) | Ctrl-C 中断 | 所有阶段 | shell 惯例（128 + SIGINT=2） |

> **注意**：上表中 2 / 3 / 4 / 5 这 4 个"自定义"码与 POSIX / sysexits 不完全对齐，是 LangAgent 自行约定的语义；实施时须在 `workflow.md` 的退出码表中**显式标注**"自定义"4 字，避免与 sysexits 读者混淆。

## R-4 阶段六栏 / CLI 五栏的"行数下界"建议

为防止实施者写"五栏"时只填 1-2 行凑数，本调研给出每栏的最少行数下界：

| 文档 | 章节 | 每栏最少行数（项数） |
|---|---|---|
| `workflow.md` | 6 阶段 × 5 栏 | 阶段 1（`dir_load`）/ 阶段 4（`graph_compose`）/ 阶段 6（`exit_cleanup`）每栏 ≥ 3 项；阶段 2/3/5 每栏 ≥ 5 项。 |
| `workflow.md` | 4 CLI 子命令 × 5 栏 | `init` 每栏 ≥ 5 项；`run` 每栏 ≥ 5 项；`eval` 每栏 ≥ 3 项；`doctor` 每栏 ≥ 5 项。 |
| `architecture_modules.md` | N 模块 × 4 栏 | 任意模块的任意栏不得为空（≥ 1 项）；"职责"栏 ≥ 2 项（主职责 + 副职责；spec FR-022 精修后已去掉"建议"措辞，与同句其他 3 项强制语气一致）；"关键 API"栏 ≥ 1 项；"允许的依赖方向"栏 ≥ 1 项；"禁止的依赖方向"栏 ≥ 1 项。 |
| `module_schemas.md` | 19 一级章节 × 4 二级小节 | 19 个非合并章节各 4 个二级小节；3 个合并章节各 6 个二级小节（FR-033 / Q9 澄清）。 |

> 实施者不达下界即触发 checklist CHK113 / CHK122 / CHK133 的"机械 + 人工" review 项失败。

## R-5 默认日志标签集合的初始建议

为 `workflow.md` 实施时"日志标签 → 含义 → 触发阶段"表提供初始建议（仅供实施者参考，可自由调整）：

| 日志标签 | 含义 | 触发阶段 |
|---|---|---|
| `la.cli.init.start` | `langagent init` 开始 | `dir_load` |
| `la.cli.init.end` | `langagent init` 结束 | `exit_cleanup` |
| `la.cli.run.start` | `langagent run` 开始 | `main_loop` |
| `la.cli.run.turn` | 单轮 ReAct 循环（推理→工具→观察）| `main_loop` |
| `la.cli.run.tool_call` | 模型发起 tool_call | `main_loop` |
| `la.cli.run.tool_result` | 工具执行返回结果 | `main_loop` |
| `la.cli.eval.start` | `langagent eval` 开始 | `dir_load` |
| `la.cli.eval.case_done` | 单条 eval 任务完成 | `exit_cleanup` |
| `la.cli.eval.summary` | eval 总结报告 | `exit_cleanup` |
| `la.cli.doctor.check` | `langagent doctor` 单项自检 | `config_resolve` |
| `la.cli.doctor.report` | doctor 报告生成 | `exit_cleanup` |
| `la.runtime.dir_load.ok` | 目录加载成功 | `dir_load` |
| `la.runtime.dir_load.fail` | 目录加载失败 | `dir_load` |
| `la.runtime.config_resolve.ok` | 配置解析成功 | `config_resolve` |
| `la.runtime.config_resolve.fail` | 配置解析失败 | `config_resolve` |
| `la.runtime.model_adapt.ok` | 模型实例化成功 | `model_adapt` |
| `la.runtime.model_adapt.fail` | 模型实例化失败 | `model_adapt` |
| `la.runtime.graph_compose.ok` | 图组合成功 | `graph_compose` |
| `la.runtime.graph_compose.fail` | 图组合失败 | `graph_compose` |
| `la.runtime.main_loop.start` | 主循环开始 | `main_loop` |
| `la.runtime.main_loop.end` | 主循环结束 | `main_loop` |
| `la.runtime.exit_cleanup.ok` | 退出清理成功 | `exit_cleanup` |
| `la.runtime.exit_cleanup.fail` | 退出清理失败 | `exit_cleanup` |
| `la.cross_cutting.guardrail.block` | 护栏拦截 | `main_loop` |
| `la.cross_cutting.audit.write` | 审计写入 | `exit_cleanup` |

> 实施者**至少**须包含上表 25 项中 ≥ 15 项，可自由增删但需保证（1）每阶段 ≥ 3 个标签；（2）`la.` 前缀；（3）每个标签的阶段归属与 FR-016 阶段锚点严格对应。

## R-6 已识别的歧义与本调研的处理

| 编号 | 歧义 | 本调研处理位置 |
|---|---|---|
| R-1.1 | 五栏 / 四栏的内容模板 | R-1.1 |
| R-1.2 | MDA 对照表 / 静态约束 CI 清单的行数下界 | R-1.2 |
| R-1.3 | 模块 ID 候选集合的初始建议 | R-1.3 |
| R-2 | LangChain / LangGraph 原生类型引用清单 | R-2.1 / R-2.2 |
| R-3 | 退出码 12 集合的来源溯源 | R-3 |
| R-4 | 阶段 / CLI / 模块 / schema 行的"行数下界" | R-4 |
| R-5 | 默认日志标签集合的初始建议 | R-5 |

## R-7 调研结论

本调研共沉淀 7 项决策 / 5 张参考表，全部为 3 份文档的实施提供"内容蓝图"。实施者按本调研 + plan.md + data-model.md + contracts/*.contract.md 落盘 3 份文档时，不应再产生"自由发挥后撞墙"的情形。

> **Phase 0 完成标志**：`harness/LangChain_doc/` / `harness/LangGraph_doc/` / `harness/Managed_deep_agents/` 三处本地副本均已通读并形成 R-2 / R-3 引用表；spec 9 轮 clarify 之外的 3 类隐性歧义（R-1.1 / R-1.2 / R-1.3）已全部给出决策；MDA 能力对照表 / 静态约束 CI 清单 / 模块 ID 候选集合 / 退出码溯源 / 日志标签初始集合均已沉淀为可机械核验的参考清单。

进入 Phase 1（设计 + 契约）。
