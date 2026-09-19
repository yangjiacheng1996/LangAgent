---
doc_id: workflow
version: v2.1.0
last_updated: 2026-09-15
constitution_ref: ../../.specify/memory/constitution.md
related_docs:
  - architecture_modules.md
  - module_schemas.md
---

# workflow.md — 工作流设计文档

> 本文档是 LangAgent 顶层设计三份文档之一，定义 LangAgent 一次完整运行的工作流：
> 用户视角（CLI 生命周期）+ 系统视角（6 阶段）+ 退出码 + 日志标签 + MDA 能力对照。
> 本文档作为 Feature 01-10+ 拆分任务时"切到哪个阶段 / 返回哪个退出码 / 打哪个日志标签"的事实来源。
>
> 与宪法第 I 条关系：本文件不发布 SDK、不暴露 importable API；纯设计文档。
> 与宪法第 III 条关系：本文档不出现 LangSmith 相关字面量。
> 与宪法第 VI 条关系：6 阶段名与 AgentState schema 字段语义一致。
> 与宪法第 XI 条关系：CLI 仅 4 个核心子命令（Q5 澄清），不预留辅助接口。
>
> **v0.4.0 变更（M-NEW-3 修复后）**：12 个 `la.cli.*` tag 全部 rename 为 `la.lifecycle.*`（按用户视角的 CLI 生命周期重新组织命名空间）。5 个未注册的 `la.cli.*`（`init.template_render` / `init.fs_write` / `eval.task_start` / `doctor.start` / `doctor.end`）从 CLI 子命令描述中移除（从未在白名单登记）。`la.lifecycle.*` = 用户视角 CLI 生命周期事件（runtime / protocol 层发射）；`la.runtime.*` = 内部层视角事件；`la.cross_cutting.*` = 横切层视角事件。三层命名空间按"视角"对齐，无前缀歧义。

---

## 文档元信息

| 字段 | 值 |
|---|---|
| `doc_id` | `workflow` |
| `version` | `v2.1.0`（**review.md v2.1.0 修复后**：本文件主版本号同步 v1.2.0 → v2.1.0；`init.end` 阶段归属显式声明 + F06 cleanup API 增 init_only 参数；GuardrailPolicy 进 schema；F01 eval dispatch resolve 一次 config 路径明确） |
| `last_updated` | `2026-09-15` |
| `constitution_ref` | `../../.specify/memory/constitution.md` |
| `related_docs` | `architecture_modules.md`、`module_schemas.md` |

---

## 用户视角：CLI 生命周期

> 本节从用户（项目维护者本人）视角定义 LangAgent 的 4 个核心子命令。
> 每个子命令下挂 5 栏：输入 / 输出 / 失败模式 / 退出码 / 日志标签。
> 不为 `version` / `tui` / `serve` / `clean` 等辅助子命令预留接口（Q5 澄清）。

### `langagent init <name>`

#### 输入

- `<name>`：待创建的智能体目录名（字母开头，可含字母 / 数字 / 下划线 / 短横线）。
- 当前工作目录路径（cwd）：新智能体目录的父目录。
- 模板默认参数：可在 `~/.config/langagent/init.yaml` 中覆盖。

#### 输出

- 在 cwd 下创建名为 `<name>/` 的智能体目录。
- 目录内含宪法第 V 条规定的子目录骨架：`instructions.md`、`skills/`、`tools/`、`middleware/`、`evals/`。
- 终端打印创建摘要（创建的文件清单 + 提示下一步操作）。

#### 失败模式

- `name_invalid_format`：`<name>` 不符合命名约束 → 退出码 2（用法错误）。
- `name_already_exists`：cwd 下同名目录已存在 → 退出码 **67**（**v0.5.0 评审 v0.1.0 §四.C-7 修复**：原误用 66 = EX_NOINPUT，v0.5.0 起拆分为 67 = name_already_exists；语义更清晰）。
- `template_load_failed`：内置模板加载失败（极少触发） → 退出码 70（EX_SOFTWARE）。
- `stage_capability_violation`：阶段读取了不属于本阶段范围的配置（如 init 阶段尝试访问模型配置）→ 退出码 1（通用失败）+ `la.runtime.dir_load.fail` 日志。

#### 退出码

- 主要：0（成功）/ 2（用法错误）/ **67（name_already_exists）**。
- 次要：1 / 64 / 65 / 66 / 70 / 78 / 130。

#### 日志标签

- `la.lifecycle.init.start`：`langagent init` 入口处。
- `la.lifecycle.init.end`：`langagent init` 收尾处。
- `la.runtime.dir_load.fail`：阶段越权读取配置。

---

### `langagent run [agent-dir]`

#### 输入

- `[agent-dir]`（可选）：智能体目录绝对或相对路径；缺省取 cwd。
- 命令行 `--model` / `--checkpointer` / `--middleware` 等运行时参数。
- 环境变量（如 `OPENAI_API_KEY` / `OPENAI_BASE_URL`）。
- 智能体目录下 `.env` 文件中的键值对。

#### 输出

- 标准输出流（stdout）：模型与用户的对话内容。
- 标准错误流（stderr）：结构化日志（`la.*` 前缀）。
- 进程退出码（0 / 1 / 4 / 70 / 78 / 130 等）。
- 运行时写入 `~/.local/share/langagent/logs/<run-id>.jsonl`（事件总线持久化）。

#### 失败模式

- `agent_dir_not_found`：`[agent-dir]` 不存在 → 退出码 66（EX_NOINPUT）。
- `agent_dir_invalid_layout`：缺 `instructions.md` 或子目录缺失 → 退出码 65（EX_DATAERR）。
- `model_timeout`：模型调用超时 → 退出码 70（EX_SOFTWARE）。
- `tool_execution_error`：工具抛异常 → 退出码 1（通用失败）。
- `config_invalid`：环境变量或 .env 与 schema 不匹配 → 退出码 78（EX_CONFIG）。
- `stage_capability_violation`：`main_loop` 阶段直接读取 .env（应仅由 `config_resolve` 阶段完成）→ 退出码 1 + `la.cross_cutting.guardrail.block`（**v0.5.0 评审 v0.1.0 §四.C-6 修复说明**：main_loop 阶段的 stage_capability_violation 不走 `la.runtime.main_loop.fail` 而走 `la.cross_cutting.guardrail.block`，因为 main_loop 阶段违规检测由 F09 guardrail middleware 实施，归属 cross_cutting 命名空间；其他 5 个阶段（dir_load / config_resolve / model_adapt / graph_compose / exit_cleanup）违规均走对应 `la.runtime.{stage}.fail` tag）。

#### 退出码

- 主要：0 / 1 / 4 / 70 / 78 / 130。
- 次要：2 / 5 / 64 / 65 / 66。

#### 日志标签

- `la.lifecycle.run.start`：`langagent run` 入口处。
- `la.lifecycle.run.turn`：单轮 ReAct 循环（推理→工具→观察）开始。
- `la.lifecycle.run.tool_call`：模型发起 tool_call。
- `la.lifecycle.run.tool_result`：工具执行返回结果。
- `la.lifecycle.run.model_response`：模型回复。
- `la.runtime.main_loop.start`：主循环开始。
- `la.runtime.main_loop.end`：主循环结束。

---

### `langagent eval [agent-dir]`

#### 输入

- `[agent-dir]`（可选）：智能体目录绝对或相对路径；缺省取 cwd。
- `evals/` 目录下所有 `*.yaml` 文件（每个文件 = 1 个 EvalTaskSpec）。

#### 输出

- 终端打印评测总结报告（通过率 / P50 延迟 / token 用量 / 估算成本）。
- 报告持久化：`~/.local/share/langagent/reports/<agent-dir>-<timestamp>.json`（EvalReport 格式）。
- 进程退出码（0 = 全部通过；非 0 = 有失败任务）。

#### 失败模式

- `evals_dir_missing`：`evals/` 目录不存在 → 退出码 66（EX_NOINPUT）。
- `eval_yaml_parse_error`：YAML 解析失败 → 退出码 65（EX_DATAERR）。
- `eval_timeout`：单任务超时（默认 60 s） → 退出码 70（EX_SOFTWARE）。
- `eval_grader_unknown`：grader 字段值未登记到 `EvalTaskSpec.grader` Literal 中 → 退出码 78（EX_CONFIG）。
- `stage_capability_violation`：`exit_cleanup` 阶段尝试重新执行模型调用（应仅完成结果聚合）→ 退出码 1 + `la.runtime.exit_cleanup.fail`。

#### 退出码

- 主要：0 / 1 / 70 / 78 / 130。
- 次要：2 / 4 / 5 / 64 / 65 / 66。

#### 日志标签

- `la.lifecycle.eval.start`：`langagent eval` 入口处。
- `la.lifecycle.eval.case_done`：单条 eval 任务完成。
- `la.lifecycle.eval.summary`：eval 总结报告生成。

---

### `langagent doctor`

#### 输入

- `[agent-dir]`（可选）：智能体目录路径；缺省取 cwd。
- 命令行 `--checks` 参数（可选）：仅跑指定的自检项（如 `model` / `checkpointer` / `skills`）。

#### 输出

- 终端打印单项自检结果（check_name / status / detail）。
- 总体结论：`ok` / `warn` / `error`。
- 报告持久化：`~/.local/share/langagent/reports/doctor-<timestamp>.json`（DoctorReport 格式）。

#### 失败模式

- `agent_dir_not_found`：智能体目录不存在 → 退出码 66。
- `model_probe_failed`：无法连接模型 endpoint → 退出码 1。
- `config_invalid`：RuntimeConfig 字段缺失或类型不匹配 → 退出码 78。
- `stage_capability_violation`：`config_resolve` 阶段直接实例化模型（应仅由 `model_adapt` 阶段完成）→ 退出码 1 + `la.runtime.model_adapt.fail`。

#### 退出码

- 主要：0 / 1 / 2 / 78 / 130。
- 次要：4 / 5 / 64 / 65 / 66 / 70。

#### 日志标签

- `la.lifecycle.doctor.check`：单项自检执行。
- `la.lifecycle.doctor.report`：doctor 报告生成。

---

## 系统视角：6 阶段

> 本节从系统视角定义 LangAgent 一次完整运行的 6 个阶段。
> 每个阶段以 `### <stage_name> {#stage-<stage_name>}` 显式锚点形式书写（FR-016 / Q6）。
> 6 阶段名严格为：`dir_load` / `config_resolve` / `model_adapt` / `graph_compose` / `main_loop` / `exit_cleanup`。

### `dir_load` {#stage-dir_load}

> 阶段 1：加载智能体目录并验证布局（宪法第 V 条目录契约）。

#### 输入

- `agent_dir`：智能体目录路径（来自 CLI 参数或 cwd）。
- 文件系统只读权限。
- `RuntimeConfig.cli_args.agent_dir` 字段。

#### 输出

- `LoadedAgent.instructions`：从 `instructions.md` 读取的系统提示词。
- `LoadedAgent.tool_ids`：从 `tools/*.py` 中扫描得到的 tool_id 列表。
- `LoadedAgent.skill_names`：从 `skills/<name>/` 中扫描得到的 skill_name 列表。
- `RuntimeConfig.skill_dirs`：智能体目录 `skills/` 下的子目录名列表。
- 失败时：`stage_capability_violation` 标志位（只读）+ 退出码。

#### 失败模式

- `agent_dir_not_found`：目录不存在 → 退出码 66（EX_NOINPUT）。
- `agent_dir_not_a_directory`：路径指向文件而非目录 → 退出码 66。
- `agent_dir_invalid_layout`：缺 `instructions.md` 或 4 个子目录任一缺失 → 退出码 65（EX_DATAERR）。
- `instructions_read_failed`：`instructions.md` 读取失败（权限不足等） → 退出码 4（I/O 错误）。
- `stage_capability_violation`：阶段尝试解析 .env（应仅由 `config_resolve` 阶段完成）→ 退出码 1 + `la.runtime.dir_load.fail`。

#### 退出码

- 主要：0 / 1 / 4 / 66 / 130。
- 次要：2 / 5 / 64 / 65 / 70 / 78。

#### 日志标签

- `la.runtime.dir_load.start`：阶段入口。
- `la.runtime.dir_load.ok`：目录加载成功。
- `la.runtime.dir_load.fail`：目录加载失败。

---

### `config_resolve` {#stage-config_resolve}

> 阶段 2：按"CLI > 环境变量 > .env > 内置默认"优先级合并 RuntimeConfig（宪法第 XII 条）。

#### 输入

- `RuntimeConfig.cli_args`：CLI 参数字典。
- `os.environ`：环境变量快照。
- 智能体目录下 `.env` 文件解析结果。
- `RuntimeConfig.builtin_defaults`：内置默认值字典。
- `dir_load` 阶段产出的 `LoadedAgent` 句柄。

#### 输出

- `RuntimeConfig` 冻结实例（`frozen=True`，字段不可变）。
- `RuntimeConfig.model_provider` / `model_name` / `model_base_url`：模型配置。
- `RuntimeConfig.middleware_ids`：启用的 middleware 列表。
- `RuntimeConfig.checkpointer`：checkpointer 名称（'memory' / 'sqlite' / 'postgres'）。

#### 失败模式

- `priority_conflict_unresolved`：CLI 参数与环境变量冲突时无法按优先级合并 → 退出码 78（EX_CONFIG）。
- `dotenv_malformed`：`.env` 文件格式错误 → 退出码 65（EX_DATAERR）。
- `required_field_missing`：必填字段（如 `model_provider`）缺失 → 退出码 5（配置错误）。
- `type_mismatch`：字段类型与 schema 不匹配 → 退出码 78（EX_CONFIG）。
- `stage_capability_violation`：阶段实例化模型（应仅由 `model_adapt` 阶段完成）→ 退出码 1 + `la.runtime.config_resolve.fail`。

#### 退出码

- 主要：0 / 1 / 2 / 5 / 78 / 130。
- 次要：4 / 64 / 65 / 66 / 70。

#### 日志标签

- `la.runtime.config_resolve.start`：阶段入口。
- `la.runtime.config_resolve.priority_merge`：优先级合并时。
- `la.runtime.config_resolve.ok`：配置解析成功。
- `la.runtime.config_resolve.fail`：配置解析失败。

---

### `model_adapt` {#stage-model_adapt}

> 阶段 3：根据 `RuntimeConfig.model_provider` 实例化 `BaseChatModel`（宪法第 IV 条模型抽象）。

#### 输入

- `RuntimeConfig.model_provider`：字符串（`'openai'` / `'anthropic'` / `'google'` / `'deepseek'` / `'zhipu'` / `'openai-compatible'`）。
- `RuntimeConfig.model_name`：模型名（如 `'gpt-4o'` / `'claude-3-5-sonnet'` / `'qwen3-8b'`）。
- `RuntimeConfig.model_base_url`：仅 OpenAI Compatible 后端必填。
- API key（来自环境变量；不硬编码）。

#### 输出

- `RuntimeConfig.model`：`BaseChatModel` 实例，可直接 `invoke(messages)`。
- 日志记录（初始化耗时 / 端点连通性测试结果）。

#### 失败模式

- `provider_unsupported`：`model_provider` 不在 6 个候选值之内 → 退出码 78（EX_CONFIG）。
- `endpoint_unreachable`：`model_base_url` 不可达 → 退出码 70（EX_SOFTWARE）。
- `auth_failed`：API key 无效或缺失 → 退出码 78（EX_CONFIG）。
- `model_init_timeout`：模型实例化超时 → 退出码 70（EX_SOFTWARE）。
- `stage_capability_violation`：阶段组合 LangGraph 图（应仅由 `graph_compose` 阶段完成）→ 退出码 1 + `la.runtime.model_adapt.fail`。

#### 退出码

- 主要：0 / 1 / 70 / 78 / 130。
- 次要：2 / 4 / 5 / 64 / 65 / 66。

#### 日志标签

- `la.runtime.model_adapt.start`：阶段入口。
- `la.runtime.model_adapt.endpoint_probe`：端点连通性测试。
- `la.runtime.model_adapt.ok`：模型实例化成功。
- `la.runtime.model_adapt.fail`：模型实例化失败。

---

### `graph_compose` {#stage-graph_compose}

> 阶段 4：根据 `instructions` + `tools` + `skills` + `middleware` 组合 LangGraph 图（宪法第 VI 条 Agent Loop）。

#### 输入

- `LoadedAgent.instructions` / `tool_ids` / `skill_names`。
- `RuntimeConfig.middleware_ids`：启用的 middleware 列表。
- `RuntimeConfig.model`：已实例化的 `BaseChatModel`。
- `RuntimeConfig.checkpointer`：checkpointer 实例。

#### 输出

- `LoadedAgent.compiled_graph`：`CompiledStateGraph`（不可变，编译完成后冻结）。**review.md v1.1.0 P0-2 修复后**：该字段已删除，CompiledStateGraph 由 F10 build() 返回给 F01 dispatch 独立持有；LoadedAgent schema_version v0.1.0 → v0.2.0。
- Span 记录：`graph_compose` 阶段的 trace（trace_id / span_id 写入 Span）。
- `Event` 总线发布：`graph_composed` 事件。

#### 失败模式

- `middleware_init_failed`：middleware 初始化抛异常 → 退出码 70（EX_SOFTWARE）。
- `tool_binding_failed`：工具绑定到模型失败 → 退出码 70（EX_SOFTWARE）。
- `graph_compile_failed`：LangGraph 图编译失败 → 退出码 70（EX_SOFTWARE）。
- `checkpointer_init_failed`：checkpointer 实例化失败 → 退出码 70。
- `stage_capability_violation`：阶段实例化模型（应仅由 `model_adapt` 阶段完成）→ 退出码 1 + `la.runtime.graph_compose.fail`。

#### 退出码

- 主要：0 / 1 / 70 / 130。
- 次要：2 / 4 / 5 / 64 / 65 / 66 / 78。

#### 日志标签

- `la.runtime.graph_compose.start`：阶段入口。
- `la.runtime.graph_compose.middleware_bind`：middleware 绑定时。
- `la.runtime.graph_compose.tool_bind`：工具绑定时。
- `la.runtime.graph_compose.ok`：图组合成功。
- `la.runtime.graph_compose.fail`：图组合失败。

---

### `main_loop` {#stage-main_loop}

> 阶段 5：执行 ReAct 主循环（推理→工具→观察）直至用户中断或任务完成（宪法第 VI 条）。

#### 输入

- `LoadedAgent.compiled_graph`：编译后的 LangGraph 图。**review.md v1.1.0 P0-2 修复后**：该字段已删除，运行时 CompiledStateGraph 由 F10 build() 返回给 F01 dispatch 独立持有（见 stage 4 graph_compose 输出）。
- `AgentState`：初始 State（含 `messages` / `todos` / `files` / `context` / `scratchpad` 5 字段，FR-037 / Q1）。
- 用户输入：CLI 提示符 / IM 通道消息 / 评测任务输入。

#### 输出

- `AgentState.messages`：追加的 AIMessage / ToolMessage。
- `AgentState.todos` / `files` / `context` / `scratchpad`：按 reducer 规则更新。
- `MetricsSnapshot`：每轮结束更新。
- `Event` 总线发布：`tool_call` / `model_response` / `guardrail_block` 等事件。
- `AuditEntry`：guardrail 触发时写入。

#### 失败模式

- `model_timeout`：单次模型调用超时 → 退出码 70（EX_SOFTWARE）。
- `tool_execution_error`：工具抛异常 → 退出码 1（通用失败）。
- `guardrail_block`：guardrail middleware 拦截（如工具 `requires_approval=True` 且未审批，或 strict 模式下任何工具调用）→ 退出码 1 + `AuditEntry.category=unauthorized_tool`。
- `hitl_interrupted`：human-in-the-loop interrupt 触发（user 取消）→ 退出码 130（SIGINT）。
- `token_limit_exceeded`：累计 token 用量超阈值 → 退出码 70（EX_SOFTWARE）。
- `stage_capability_violation`：阶段读取 .env（应仅由 `config_resolve` 阶段完成）→ 退出码 1 + `la.cross_cutting.guardrail.block`。

#### 退出码

- 主要：0 / 1 / 70 / 130。
- 次要：3 / 4 / 5 / 64 / 65 / 66 / 78。

#### 日志标签

- `la.runtime.main_loop.start`：主循环开始。
- `la.runtime.main_loop.turn.start`：单轮 ReAct 循环开始。
- `la.runtime.main_loop.turn.end`：单轮 ReAct 循环结束。
- `la.runtime.main_loop.model_call`：模型调用。
- `la.runtime.main_loop.tool_call`：工具调用。
- `la.runtime.main_loop.tool_result`：工具结果。
- `la.runtime.main_loop.end`：主循环结束。
- `la.cross_cutting.guardrail.block`：护栏拦截。
- `la.cross_cutting.metrics.emit`：指标快照发布。

---

### `exit_cleanup` {#stage-exit_cleanup}

> 阶段 6：清理资源、关闭 checkpointer、写出最终报告（DoctorReport / EvalReport / MetricsSnapshot）。

#### 输入

- 主循环结束时的 `AgentState` 最终状态。
- `RuntimeConfig`：完整配置快照。
- 运行时累积的 `MetricsSnapshot` / `AuditEntry` / `Event` / `Span`。

#### 输出

- 关闭 checkpointer 连接（如 sqlite / postgres）。
- 写出 `~/.local/share/langagent/reports/<run-id>.jsonl`（含 Span / Event / AuditEntry）。
- 写出 `DoctorReport` / `EvalReport` / `MetricsSnapshot`。
- 进程退出码（最终返回给 shell）。

#### 失败模式

- `report_write_failed`：报告写入失败（磁盘满 / 权限不足）→ 退出码 4（I/O 错误）。
- `checkpointer_close_failed`：checkpointer 关闭抛异常 → 退出码 1（通用失败）。
- `audit_flush_failed`：审计日志刷新失败 → 退出码 4（I/O 错误）。
- `stage_capability_violation`：阶段重新执行模型调用（应仅在 `main_loop` 完成）→ 退出码 1 + `la.runtime.exit_cleanup.fail`。

#### 退出码

- 主要：0 / 1 / 4 / 130。
- 次要：2 / 5 / 64 / 65 / 66 / 70 / 78。

#### 日志标签

- `la.runtime.exit_cleanup.start`：阶段入口。
- `la.runtime.exit_cleanup.checkpointer_close`：checkpointer 关闭。
- `la.runtime.exit_cleanup.report_write`：报告写入。
- `la.runtime.exit_cleanup.audit_flush`：审计日志刷新。
- `la.runtime.exit_cleanup.ok`：退出清理成功。
- `la.runtime.exit_cleanup.fail`：退出清理失败。
- `la.cross_cutting.audit.write`：审计写入。

---

## 退出码表

> **v0.5.0 修复（review.md v0.1.0 §四.C-7）**：原 12 行扩展为 **13 行**，新增退出码 **67** = `name_already_exists`；原退出码 66 在 v0.5.0 起仅表示"用户提供的输入文件 / 目录不存在"（EX_NOINPUT），不再兼任"目标名称已存在"。
> 每个退出码对应恰好 1 行；触发阶段列允许多阶段映射（Q10：多阶段以 `/` 分隔或"所有阶段"统称；总行数 = 13）。

### `退出码 0` {#exit-code-0}

- **语义**：成功（`EXIT_SUCCESS`，POSIX 标准）。
- **触发条件**：6 个阶段中任一阶段执行完毕且无错误。
- **典型场景**：所有阶段按预期完成；`main_loop` 正常收敛（用户输入处理完毕 / 模型自发停止 / eval 全部通过）。

### `退出码 1` {#exit-code-1}

- **语义**：通用失败（`EXIT_FAILURE`，POSIX 标准）。
- **触发条件**：未归入 2/3/4/5/64/65/66/70/78/130 的失败；或 `stage_capability_violation`。
- **典型场景**：tool 执行异常；runtime 内部断言失败；guardrail 拦截。

### `退出码 2` {#exit-code-2}

- **语义**：用法错误（shell 惯例）。
- **触发条件**：CLI 参数解析失败（argparse 错误）；参数值与 schema 不匹配。
- **典型场景**：`langagent run --unknown-flag`；`<name>` 不符合命名约束。

### `退出码 3` {#exit-code-3}

- **语义**：数据错误（自定义）。
- **触发条件**：模型返回内容格式错误（JSON parse 失败）；state 字段类型校验失败。
- **典型场景**：工具返回的 JSON 无法解析为 ToolMessage。

### `退出码 4` {#exit-code-4}

- **语义**：I/O 错误（自定义）。
- **触发条件**：磁盘满 / 权限不足 / 文件不存在（与 66 区分：66 用于"用户提供的输入文件"，4 用于"运行时输出文件"）。
- **典型场景**：`~/.local/share/langagent/logs/` 写失败；checkpoint 文件读失败。

### `退出码 5` {#exit-code-5}

- **语义**：配置错误（自定义）。
- **触发条件**：RuntimeConfig 必填字段缺失；类型不匹配（区别于 78：5 是 schema 层面，78 是配置源层面）。
- **典型场景**：`RuntimeConfig.model_provider` 为 None。

### `退出码 64` {#exit-code-64}

- **语义**：`EX_USAGE`（sysexits.h）。
- **触发条件**：命令行用法错误（语义层面，如 `langagent init <name>` 时 `<name>` 为空字符串）。
- **典型场景**：与退出码 2 的区别——2 是 argparse 解析错误（机械），64 是语义层用法错误（人工可读）。

### `退出码 65` {#exit-code-65}

- **语义**：`EX_DATAERR`（sysexits.h）。
- **触发条件**：输入数据格式错误（如 .env / YAML / Markdown frontmatter 解析失败）。
- **典型场景**：`evals/*.yaml` YAML 解析失败；`skills/<name>/SKILL.md` frontmatter 字段缺失。

### `退出码 66` {#exit-code-66}

- **语义**：`EX_NOINPUT`（sysexits.h）。
- **触发条件**：用户提供的输入文件 / 目录不存在。
- **典型场景**：智能体目录不存在；`evals/` 目录不存在。

### `退出码 67` {#exit-code-67}

- **语义**：`EX_CANTCREAT` 语义扩展（sysexits.h 无对应，LangAgent 自定义；**review.md v0.1.0 §四.C-7 修复新增**：原 66 双语义拆分为 66 = not found + 67 = already_exists）。
- **触发条件**：用户操作的目标资源已存在，无法创建 / 覆盖。
- **典型场景**：`langagent init <name>` 时 `<name>` 目录已存在（与 66 区分：66 用于"输入不存在"，67 用于"目标已存在无法创建"）。
- **唯一触发阶段**：`dir_load`（F02 `runtime_dir_loader.write_template()`）。

### `退出码 70` {#exit-code-70}

- **语义**：`EX_SOFTWARE`（sysexits.h）。
- **触发条件**：内部软件错误（不可恢复）。
- **典型场景**：模型 endpoint 不可达；图编译失败；middleware 初始化异常。

### `退出码 78` {#exit-code-78}

- **语义**：`EX_CONFIG`（sysexits.h）。
- **触发条件**：配置源错误（如 .env 与 schema 冲突；优先级链无法合并）。
- **典型场景**：CLI 参数与环境变量冲突无法仲裁；API key 缺失。

### `退出码 130` {#exit-code-130}

- **语义**：SIGINT（128 + 2，shell 惯例）。
- **触发条件**：用户在任意阶段按 Ctrl-C。
- **典型场景**：用户在 `main_loop` 中断；在 `langagent doctor` 中断；在 `model_adapt` 等待时中断。

> **总结**：退出码 2 / 3 / 4 / 5 这 4 个"自定义"码与 POSIX / sysexits 不完全对齐，是 LangAgent 自行约定的语义；详见 [research.md R-3](../../specs/000-top-level-design/research.md)。
> 多阶段映射语义：该退出码在所列任一阶段触发时即返回（Q10）。
> 与宪法第 XIII 条关系：本表无 LangSmith 相关退出码；任何 LangSmith 触发的失败按通用退出码 1 处理。

---

## 日志标签表

> 至少 15 行（FR-014 硬下限）；前 25 项参考 [research.md R-5](../../specs/000-top-level-design/research.md) 初始集合；实施者可在 25 项范围内增减，但须保证每阶段 ≥ 3 个标签 + `la.` 前缀 + 锚点规范。
> 表中"锚点"列即下文 45 个 `##` 二级章节的显式锚点（FR-016）。
> 锚点形式：点号替换为短横线（FR-016 / FR-041）。
> **v0.4.0 命名空间约定（M-NEW-3 修复）**：`la.lifecycle.*` = 用户视角 CLI 生命周期事件；`la.runtime.*` = 内部运行时层事件；`la.cross_cutting.*` = 横切层事件。前缀 = 视角，不再 = 发射方所在层。

### `la.lifecycle.init.start` {#log-tag-la-lifecycle-init-start}

- **含义**：`langagent init` 入口处发出。
- **触发阶段**：`dir_load`。
- **典型时机**：CLI 解析完成、即将进入智能体目录扫描前。
- **发射方（review.md v0.3.0 S-2 / 第三批修复）**：F02 `runtime_dir_loader.write_template()` 入口。

### `la.lifecycle.init.end` {#log-tag-la-lifecycle-init-end}

- **含义**：`langagent init` 收尾处发出。
- **触发阶段**：`exit_cleanup`。
- **典型时机**：目录骨架创建完毕、模板文件全部落盘后。
- **发射方（review.md v2.1.0 P1-2 修复明确 + review.md v3.0.0 P2-5 修复归属纠正）**：F09 `runtime_exit_handler.cleanup()`（`init_only=True` 模式分支；F10 init dispatch 末尾调 `exit_handler.cleanup(state=None, config=None, *, init_only=True)` 走极简分支；F09 §3.3 step 10 发射 `la.lifecycle.init.end`）。**F06 §3.5 `write_template()` 收尾不再发射 `init.end`**，仅发 `init.start`。

### `la.lifecycle.run.start` {#log-tag-la-lifecycle-run-start}

- **含义**：`langagent run` 入口处发出。
- **触发阶段**：`main_loop`。
- **典型时机**：AgentState 初始化完成、首次模型调用前。
- **发射方（review.md v0.3.0 S-3 修复）**：F05 `runtime_main_loop_dispatcher.run_until_done()` 入口。

### `la.lifecycle.run.turn` {#log-tag-la-lifecycle-run-turn}

- **含义**：单轮 ReAct 循环（推理→工具→观察）。
- **触发阶段**：`main_loop`。
- **典型时机**：每轮 ReAct 入口；用于 metrics 按轮统计延迟。
- **发射方**：F05 `dispatch()` 入口（每轮）。

### `la.lifecycle.run.tool_call` {#log-tag-la-lifecycle-run-tool-call}

- **含义**：模型发起 tool_call。
- **触发阶段**：`main_loop`。
- **典型时机**：`AIMessage.tool_calls` 非空时。
- **发射方**：F05 `dispatch()` 解析 `AIMessage.tool_calls` 后。

### `la.lifecycle.run.tool_result` {#log-tag-la-lifecycle-run-tool-result}

- **含义**：工具执行返回结果。
- **触发阶段**：`main_loop`。
- **典型时机**：`ToolMessage` 追加到 `AgentState.messages` 前。
- **发射方**：F05 `dispatch()` `tools_execute` 节点收尾。

### `la.lifecycle.run.model_response` {#log-tag-la-lifecycle-run-model-response}

- **含义**：模型回复（review.md v0.3.0 s-1 修复后新增）。
- **触发阶段**：`main_loop`。
- **典型时机**：`AIMessage` 追加到 `AgentState.messages` 前（含 `usage_metadata` 给 metrics）。
- **发射方**：F05 `model_call` 节点收尾。

### `la.lifecycle.eval.start` {#log-tag-la-lifecycle-eval-start}

- **含义**：`langagent eval` 入口处发出。
- **触发阶段**：`dir_load`。
- **典型时机**：`evals/` 目录扫描完成、EvalTaskSpec 列表组装完成后。
- **发射方（review.md v0.3.0 S-4 修复）**：F11 `eval/runner.run()` 入口（evals/ 加载完成后）。

### `la.lifecycle.eval.case_done` {#log-tag-la-lifecycle-eval-case-done}

- **含义**：单条 eval 任务完成。
- **触发阶段**：`exit_cleanup`。
- **典型时机**：单条 EvalTaskSpec 的 grader 返回 pass/fail 后。
- **发射方**：F11 `eval/runner._run_one_task()` 收尾。

### `la.lifecycle.eval.summary` {#log-tag-la-lifecycle-eval-summary}

- **含义**：eval 总结报告生成。
- **触发阶段**：`exit_cleanup`。
- **典型时机**：所有 task 处理完毕，EvalReport 写入磁盘前。
- **发射方**：F11 `eval/runner.run()` 收尾（EvalReport 写入磁盘前）。

### `la.lifecycle.doctor.check` {#log-tag-la-lifecycle-doctor-check}

- **含义**：`langagent doctor` 单项自检执行。
- **触发阶段**：`config_resolve`。
- **典型时机**：每项 check（model / checkpointer / skills / instructions）执行时。
- **发射方（review.md v0.3.0 S-2 修复）**：F06 `runtime_exit_handler.run_doctor_checks()` 子方法。

### `la.lifecycle.doctor.report` {#log-tag-la-lifecycle-doctor-report}

- **含义**：doctor 报告生成。
- **触发阶段**：`exit_cleanup`。
- **典型时机**：所有 check 完成后 DoctorReport 写入磁盘前。
- **发射方**：F06 `runtime_exit_handler.cleanup()` 写盘前。

### `la.runtime.dir_load.start` {#log-tag-la-runtime-dir-load-start}

- **含义**：目录加载阶段开始（review.md v0.3.0 s-1 修复后新增）。
- **触发阶段**：`dir_load`。
- **典型时机**：`runtime_dir_loader.load()` 入口。
- **发射方**：F02 `runtime_dir_loader.load()` 入口。

### `la.runtime.dir_load.ok` {#log-tag-la-runtime-dir-load-ok}

- **含义**：目录加载成功。
- **触发阶段**：`dir_load`。
- **典型时机**：宪法第 V 条 4 子目录 + instructions.md 全部校验通过。
- **发射方**：F02 `runtime_dir_loader.load()` 成功返回前。

### `la.runtime.dir_load.fail` {#log-tag-la-runtime-dir-load-fail}

- **含义**：目录加载失败。
- **触发阶段**：`dir_load`。
- **典型时机**：目录不存在 / 布局无效 / instructions.md 读取失败 / stage_guard 黑名单命中。
- **发射方**：F02 `runtime_dir_loader.load()` 异常路径 + F02 `stage_guard.py` 越权拦截时。

### `la.runtime.config_resolve.start` {#log-tag-la-runtime-config-resolve-start}

- **含义**：配置解析阶段开始（review.md v0.3.0 s-1 修复后新增）。
- **触发阶段**：`config_resolve`。
- **典型时机**：`runtime_config_resolver.resolve()` 入口。
- **发射方**：F03 `runtime_config_resolver.resolve()` 入口。

### `la.runtime.config_resolve.priority_merge` {#log-tag-la-runtime-config-resolve-priority-merge}

- **含义**：优先级合并时发出（review.md v0.3.0 s-1 修复后新增）。
- **触发阶段**：`config_resolve`。
- **典型时机**：每完成一个配置项的 4 源优先级合并时。
- **发射方**：F03 `merge_priority_chain()` 每字段合并后。

### `la.runtime.config_resolve.ok` {#log-tag-la-runtime-config-resolve-ok}

- **含义**：配置解析成功。
- **触发阶段**：`config_resolve`。
- **典型时机**：RuntimeConfig 12 字段优先级链合并完毕、Pydantic 校验通过。
- **发射方**：F03 `runtime_config_resolver.resolve()` 成功返回前。

### `la.runtime.config_resolve.fail` {#log-tag-la-runtime-config-resolve-fail}

- **含义**：配置解析失败。
- **触发阶段**：`config_resolve`。
- **典型时机**：必填字段缺失 / 类型不匹配 / 优先级冲突无法仲裁 / 占位符命中。
- **发射方**：F03 异常路径 + F02 `stage_guard.py` 越权拦截时。

### `la.runtime.model_adapt.start` {#log-tag-la-runtime-model-adapt-start}

- **含义**：模型实例化阶段开始（review.md v0.3.0 S-1 / s-1 修复后新增）。
- **触发阶段**：`model_adapt`。
- **典型时机**：`primitives_chat_model_factory.create()` 入口。
- **发射方（review.md v0.3.0 S-1 修复明确）**：F10 `primitives_chat_model_factory.create()` 入口。

### `la.runtime.model_adapt.endpoint_probe` {#log-tag-la-runtime-model-adapt-endpoint-probe}

- **含义**：端点连通性测试（review.md v0.3.0 s-1 修复后新增）。
- **触发阶段**：`model_adapt`。
- **典型时机**：`create()` 内部发起到 endpoint 的最小连通性探测（如 OpenAI protocol 的 `/models` 列表）。
- **发射方**：F10 `primitives_chat_model_factory.create()` 探测前后。

### `la.runtime.model_adapt.ok` {#log-tag-la-runtime-model-adapt-ok}

- **含义**：模型实例化成功。
- **触发阶段**：`model_adapt`。
- **典型时机**：`BaseChatModel` 实例化 + endpoint 连通性测试通过。
- **发射方**：F10 `primitives_chat_model_factory.create()` 成功返回前。

### `la.runtime.model_adapt.fail` {#log-tag-la-runtime-model-adapt-fail}

- **含义**：模型实例化失败。
- **触发阶段**：`model_adapt`。
- **典型时机**：endpoint 不可达 / API key 无效 / provider 不支持。
- **发射方**：F10 `primitives_chat_model_factory.create()` 异常路径。

### `la.runtime.graph_compose.start` {#log-tag-la-runtime-graph-compose-start}

- **含义**：图组合阶段开始（review.md v0.3.0 S-1 / s-1 修复后新增）。
- **触发阶段**：`graph_compose`。
- **典型时机**：`primitives_state_graph_builder.build()` 入口。
- **发射方（review.md v0.3.0 S-1 修复明确）**：F10 `primitives_state_graph_builder.build()` 入口。

### `la.runtime.graph_compose.middleware_bind` {#log-tag-la-runtime-graph-compose-middleware-bind}

- **含义**：middleware 绑定时（review.md v0.3.0 s-1 修复后新增）。
- **触发阶段**：`graph_compose`。
- **典型时机**：`build()` 注入 AgentMiddleware 实例前后。
- **发射方**：F10 `primitives_state_graph_builder.build()` middleware 加载步骤。

### `la.runtime.graph_compose.tool_bind` {#log-tag-la-runtime-graph-compose-tool-bind}

- **含义**：工具绑定到模型时（review.md v0.3.0 s-1 修复后新增）。
- **触发阶段**：`graph_compose`。
- **典型时机**：`build()` 注入 BaseTool 实例前后。
- **发射方**：F10 `primitives_state_graph_builder.build()` tool 加载步骤。

### `la.runtime.graph_compose.ok` {#log-tag-la-runtime-graph-compose-ok}

- **含义**：图组合成功。
- **触发阶段**：`graph_compose`。
- **典型时机**：middleware 绑定 + tool 绑定 + checkpointer 接入 + compile 全部成功。
- **发射方**：F10 `primitives_state_graph_builder.build()` 成功返回前。

### `la.runtime.graph_compose.fail` {#log-tag-la-runtime-graph-compose-fail}

- **含义**：图组合失败。
- **触发阶段**：`graph_compose`。
- **典型时机**：middleware 初始化异常 / tool 绑定失败 / checkpointer 接入失败。
- **发射方**：F10 `primitives_state_graph_builder.build()` 异常路径。

### `la.runtime.main_loop.start` {#log-tag-la-runtime-main-loop-start}

- **含义**：主循环开始。
- **触发阶段**：`main_loop`。
- **典型时机**：首次 ReAct 轮入口。
- **发射方**：F05 `runtime_main_loop_dispatcher.run_until_done()` 入口。

### `la.runtime.main_loop.turn.start` {#log-tag-la-runtime-main-loop-turn-start}

- **含义**：单轮 ReAct 循环开始（review.md v0.3.0 s-1 修复后新增）。
- **触发阶段**：`main_loop`。
- **典型时机**：每轮 dispatch 入口。
- **发射方**：F05 `dispatch()` 入口。

### `la.runtime.main_loop.turn.end` {#log-tag-la-runtime-main-loop-turn-end}

- **含义**：单轮 ReAct 循环结束（review.md v0.3.0 s-1 修复后新增）。
- **触发阶段**：`main_loop`。
- **典型时机**：每轮 dispatch 收尾（含 AIMessage 追加 + reducer 收敛）。
- **发射方**：F05 `dispatch()` 收尾。

### `la.runtime.main_loop.model_call` {#log-tag-la-runtime-main-loop-model-call}

- **含义**：模型调用（review.md v0.3.0 s-1 修复后新增）。
- **触发阶段**：`main_loop`。
- **典型时机**：`model_call` 节点发起到 BaseChatModel.invoke 的前后。
- **发射方**：F05 `model_call` 节点。

### `la.runtime.main_loop.tool_call` {#log-tag-la-runtime-main-loop-tool-call}

- **含义**：工具调用（review.md v0.3.0 s-1 修复后新增；与 `la.lifecycle.run.tool_call` 区别：`lifecycle` 前缀为用户视角 CLI 生命周期层，`runtime` 前缀为内部运行时层）。
- **触发阶段**：`main_loop`。
- **典型时机**：`tools_execute` 节点执行单个 tool_call 的前后。
- **发射方**：F05 `tools_execute` 节点。

### `la.runtime.main_loop.tool_result` {#log-tag-la-runtime-main-loop-tool-result}

- **含义**：工具结果（review.md v0.3.0 s-1 修复后新增）。
- **触发阶段**：`main_loop`。
- **典型时机**：`tools_execute` 节点产出 `ToolMessage` 后。
- **发射方**：F05 `tools_execute` 节点。

### `la.runtime.main_loop.end` {#log-tag-la-runtime-main-loop-end}

- **含义**：主循环结束。
- **触发阶段**：`main_loop`。
- **典型时机**：用户中断 / 任务完成 / 终止条件触发后。
- **发射方**：F05 `runtime_main_loop_dispatcher.run_until_done()` 收尾。

### `la.runtime.exit_cleanup.start` {#log-tag-la-runtime-exit-cleanup-start}

- **含义**：退出清理阶段开始（review.md v0.3.0 s-1 修复后新增）。
- **触发阶段**：`exit_cleanup`。
- **典型时机**：`runtime_exit_handler.cleanup()` 入口。
- **发射方**：F06 `runtime_exit_handler.cleanup()` 入口。

### `la.runtime.exit_cleanup.checkpointer_close` {#log-tag-la-runtime-exit-cleanup-checkpointer-close}

- **含义**：checkpointer 关闭（review.md v0.3.0 s-1 修复后新增）。
- **触发阶段**：`exit_cleanup`。
- **典型时机**：`primitives_checkpoint_adapter.close()` 前后。
- **发射方**：F06 cleanup 顺序第 4 步。

### `la.runtime.exit_cleanup.report_write` {#log-tag-la-runtime-exit-cleanup-report-write}

- **含义**：报告写入（review.md v0.3.0 s-1 修复后新增）。
- **触发阶段**：`exit_cleanup`。
- **典型时机**：`DoctorReport` / `EvalReport` / `MetricsSnapshot` 写入磁盘前后。
- **发射方**：F06 `write_reports()` 入口 / 出口。

### `la.runtime.exit_cleanup.audit_flush` {#log-tag-la-runtime-exit-cleanup-audit-flush}

- **含义**：审计日志刷新（review.md v0.3.0 s-1 修复后新增）。
- **触发阶段**：`exit_cleanup`。
- **典型时机**：`cross_cutting_audit_recorder.flush()` 前后。
- **发射方**：F06 cleanup 顺序第 3 步。

### `la.runtime.exit_cleanup.ok` {#log-tag-la-runtime-exit-cleanup-ok}

- **含义**：退出清理成功。
- **触发阶段**：`exit_cleanup`。
- **典型时机**：checkpointer 关闭 + 报告写入 + 审计刷新全部完成。
- **发射方**：F06 cleanup 顺序第 7 步。

### `la.runtime.exit_cleanup.fail` {#log-tag-la-runtime-exit-cleanup-fail}

- **含义**：退出清理失败。
- **触发阶段**：`exit_cleanup`。
- **典型时机**：checkpointer 关闭异常 / 报告写入失败 / 审计刷新失败。
- **发射方**：F06 cleanup 任意步骤异常时。

### `la.cross_cutting.guardrail.block` {#log-tag-la-cross-cutting-guardrail-block}

- **含义**：护栏拦截。
- **触发阶段**：`main_loop`。
- **典型时机**：middleware 检测到工具调用需要审批（工具级 `requires_approval=True` 或全局 mode 要求拦截）。
- **发射方**：F04 `cross_cutting_guardrail_middleware.evaluate()` 决定 interrupt 时。

### `la.cross_cutting.audit.write` {#log-tag-la-cross-cutting-audit-write}

- **含义**：审计写入。
- **触发阶段**：`exit_cleanup`。
- **典型时机**：AuditEntry 写入 `~/.local/share/langagent/audit.jsonl`。
- **发射方**：F09 `cross_cutting_audit_recorder.write()` 入口。

### `la.cross_cutting.metrics.emit` {#log-tag-la-cross-cutting-metrics-emit}

- **含义**：指标快照发布（review.md v0.3.0 s-1 修复后新增）。
- **触发阶段**：`main_loop`。
- **典型时机**：F08 `cross_cutting_metrics_collector.snapshot()` 产出 MetricsSnapshot 时。
- **发射方**：F08 `cross_cutting_metrics_collector.snapshot()` 出口。

### `la.cross_cutting.event_handler_error` {#log-tag-la-cross-cutting-event-handler-error}

- **含义**：Event 总线订阅 handler 抛异常被错误隔离吞掉时发出（评审 s-6 修复后新增）。
- **触发阶段**：`main_loop`（任何阶段 handler 异常都触发）。
- **典型时机**：F07 `protocol_event_bus.publish()` 调用订阅者 handler 时，handler 抛异常被隔离 → 发此 tag + payload 含 `event_type` / `handler_module` / `error_type` / `error_message`。
- **来源依据**：F07 prompt §4.1 `test_publish_handler_error_isolated` 测试要求 logger 收到 `event_handler_error` 日志。
- **扩展接口登记**：本 tag 属于 §"扩展接口约定"（仿照 EvalTaskSpec / AuditEntry 的 `*_extensibility` 模式）登记的扩展位；未来 Event 总线自身的错误类别可在 `la.cross_cutting.event_handler_error.*` 前缀下扩展。
- **发射方**：F07 `protocol_event_bus.publish()` handler 异常隔离时（通过 F08 logger.emit 接口）。

> 与宪法第 XIII 条关系：所有标签以 `la.` 前缀开头；不出现 LangSmith 镜像名 / 环境变量名。
> 覆盖范围（review.md v0.3.0 M-4 / s-1 修复后）：6 个阶段中 `dir_load` 3 个 / `config_resolve` 4 个 / `model_adapt` 4 个 / `graph_compose` 5 个 / `main_loop` 7 个 / `exit_cleanup` 6 个；加上 lifecycle.* / cross_cutting.* 横切标签，**标签总数 = 45 个**（原 26 个 + review.md v0.3.0 s-1 修复后增补 19 个 stage-internal 标签 + v0.4.0 M-NEW-3 修复后 `la.cli.*` 12 个 rename 为 `la.lifecycle.*`）。
> 锚点形式：点号替换为短横线（FR-016 / FR-041）。
> 发射方约束：所有 `la.lifecycle.*` / `la.runtime.*` / `la.cross_cutting.*` / `la.tool.*` 标签的发射方严格在 runtime / protocol / cross_cutting 层（按 workflow.md 触发阶段归属）；CLI 层（`langagent/cli/`）严禁 `import cross_cutting_logger` 或直接调用 `.emit()`（architecture_modules.md#mod-cli-parser 硬约束）。

---

## MDA 能力对照表

> 至少 10 行（FR-015 / R-1.2）；每行对应 `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-*.md` 中 1 份 MDA 文档作为 `mda_source_path`。
> `langagent_equivalent_stage` 取值限于 6 阶段之一（`dir_load` / `config_resolve` / `model_adapt` / `graph_compose` / `main_loop` / `exit_cleanup`）。

| mda_capability | mda_source_path | langagent_equivalent_stage | notes |
|---|---|---|---|
| agent-definition | `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-agent-definition.md` | `dir_load` / `graph_compose` | MDA 用 `agent.md` 描述智能体；LangAgent 用宪法第 V 条的目录布局 |
| cli | `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-cli.md` | `dir_load` / `exit_cleanup` | MDA CLI 入口与 LangAgent `init` / `run` / `eval` / `doctor` 4 子命令对应 |
| evals | `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-evals.md` | `main_loop` / `exit_cleanup` | MDA evals 用 LangSmith Evaluator；LangAgent 用本地 EvalTaskSpec + EvalReport |
| identity | `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-identity.md` | `config_resolve` | 身份验证规范对应 IdentitySpec；本项目不依赖 LangSmith auth |
| instructions | `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-instructions.md` | `dir_load` | 系统提示词加载对应 LoadedAgent.instructions |
| local-development | `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-local-development.md` | `dir_load` / `config_resolve` | 本地开发环境配置；LangAgent 对应 RuntimeConfig 优先级链 |
| mcp-connectors | `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-mcp-connectors.md` | `graph_compose` | MCP 连接器注册对应 ToolSpec 加载 |
| middleware | `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-middleware.md` | `graph_compose` | 中间件规范对应 MiddlewareSpec |
| project-structure | `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-project-structure.md` | `dir_load` | 智能体目录结构与宪法第 V 条对齐 |
| skills | `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-skills.md` | `dir_load` / `graph_compose` | 技能加载对应 SkillSpec / SkillFrontmatter |
| tools | `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-tools.md` | `dir_load` / `graph_compose` | 工具注册对应 ToolSpec |
| sandboxes | `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-sandboxes.md` | （v1 预留接口） | MDA 提供 docker / firecracker；LangAgent SandboxSpec 预留接口，v1 不实现 |
| schedules | `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-schedules.md` | （v1 预留接口） | MDA 提供 cron 调度；LangAgent ScheduleSpec 预留接口，v1 不实现 |
| memory | `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-memory.md` | （v1 预留接口） | MDA 提供 long-term memory；LangAgent MemorySpec 预留接口，v1 不实现 |
| channels | `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-channels.md` | （v1 预留接口） | MDA 提供 Slack / 飞书 通道；LangAgent ChannelSpec 预留接口，v1 不实现 |

> 与宪法第 III 条关系：本表无 LangSmith 引用；如需提及 LangSmith，措辞为反例。
> 与宪法第 IV 条关系：LangAgent 模型抽象层与 MDA 一致（`model_provider` 候选值集合）。
> 与宪法第 V 条关系：智能体目录契约与 MDA project-structure 对齐。

---

## 交叉引用

> 本节列出 workflow.md 对其它 2 份设计文档的相对路径 + 锚点引用（FR-040 / FR-041）。
> 不带 `./` 前缀、不带 `../` 前缀（FR-040）。

### 引用 architecture_modules.md

- 模块锚点示例：`architecture_modules.md#mod-cli-runner`（CLI 入口）。
- 模块锚点示例：`architecture_modules.md#mod-runtime-main-loop-dispatcher`（主循环调度）。
- 模块锚点示例：`architecture_modules.md#mod-protocol-tool-registry`（工具注册表）。
- 模块锚点示例：`architecture_modules.md#mod-cross-cutting-guardrail-middleware`（护栏拦截）。
- 模块锚点示例：`architecture_modules.md#mod-primitives-state-reducers`（State reducer 函数集合，M-4 方案 C 新增）。

### 引用 module_schemas.md

- Schema 锚点示例：`module_schemas.md#schema-agent-state`（AgentState 5 字段 reducer 规则；reducer 实现位于 primitives 层）。
- Schema 锚点示例：`module_schemas.md#schema-runtime-config`（RuntimeConfig 优先级链）。
- Schema 锚点示例：`module_schemas.md#schema-tool-spec`（ToolSpec 工具规范定义）。
- Schema 锚点示例：`module_schemas.md#schema-audit-entry`（AuditEntry 3 个安全事件类别）。

### 引用宪法

- `../../.specify/memory/constitution.md#第-VI-条`（Agent Loop 与 State）。
- `../../.specify/memory/constitution.md#第-XI-条`（打包与分发）。
- `../../.specify/memory/constitution.md#第-XII-条`（配置与可观测契约）。

### 引用本文档日志标签（v0.4.0 后）

- 日志标签锚点示例：`workflow.md#log-tag-la-lifecycle-run-start`（用户视角 CLI 生命周期事件）。
- 日志标签锚点示例：`workflow.md#log-tag-la-runtime-main-loop-turn-start`（内部运行时层事件）。
- 日志标签锚点示例：`workflow.md#log-tag-la-cross-cutting-event-handler-error`（横切层事件）。
- 锚点命名空间格式：`#log-tag-la-{lifecycle|runtime|cross_cutting}-{...}`，点号替换为短横线（FR-016 / FR-041）。

---

## 变更日志

| 日期 | 版本 | 修订摘要 | 作者 |
|---|---|---|---|
| 2026-09-14 | v0.1.0 | Feature 00 初版 | 项目维护者 |
| 2026-09-15 | v0.4.0 | review.md v0.3.0 M-NEW-3 修复：12 个 `la.cli.*` tag 全部 rename 为 `la.lifecycle.*`；5 个未注册 tag（`init.template_render` / `init.fs_write` / `eval.task_start` / `doctor.start` / `doctor.end`）从 CLI 子命令描述中移除；锚点同步更新（`#log-tag-la-cli-*` → `#log-tag-la-lifecycle-*`） | 项目维护者 |
| 2026-09-16 | v2.1.0 字面量同步 | **feature/review.md 评审 P0-2 修复**：`#log-tag-la-lifecycle-init-end` 发射方字面量由 "F02 `runtime_dir_loader.write_template()` 收尾" 修订为 "F06 `runtime_exit_handler.cleanup()`（`init_only=True` 模式分支）"；F02 §3.5 `write_template()` 收尾不再发射 `init.end`（仅发 `init.start`）。主版本号 v2.1.0 维持（changelog 内 P1-2 修复说明即可，不需要升版） | 评审者（feature/review.md 评审应用） |
