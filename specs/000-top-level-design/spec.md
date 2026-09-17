# Feature Specification: Feature 00 — 顶层设计（Top-Level Design）

**Feature Branch**: `000-top-level-design`
**Created**: 2026-09-14
**Status**: Draft
**Input**: User description: "请基于已有的项目宪法与参考文档（harness/LangChain_doc/、harness/LangGraph_doc/、harness/Managed_deep_agents/），为 LangAgent 项目生成 Feature 00：顶层设计（Top-Level Design）。"

> 本规范的"用户"专指后续 Feature（01-10+）的设计者与实现者，即项目维护者本人。所有 User Story、Functional Requirements、Success Criteria 皆从此视角书写，**不**指代终端用户。

---

## Clarifications

### Session 2026-09-14

- Q: 关于 AgentState 必填字段集合，规范与宪法第 VI 条不一致——宪法要求 5 字段（messages / todos / files / context / scratchpad），但 FR-037 只列了 4 个（漏了 context）。该以哪一份为准？ → A: 以宪法第 VI 条为准（5 字段），FR-037 补上 context 并给出 reducer 规则；context 字段 reducer 从 overwrite / merge_with_prior 集合中选取，不得使用 add_messages 风格追加式 reducer。
- Q: module_schemas.md 中"19 项 schema"应如何计数？FR-032 列举了 21 行，但用户原始输入与 FR-031/FR-032 都说"19 项"。 → A: 19 个一级章节，把 3 对天然耦合的 schema 合并为 3 个一级章节——`Span` / `Trace` 合并为 1 章节（标题 `Span / Trace`，锚点 `schema-span-trace`），`SkillSpec` / `SkillFrontmatter` 合并为 1 章节（标题 `SkillSpec / SkillFrontmatter`，锚点 `schema-skill-spec-frontmatter`），`ToolSpec` / `ToolSideEffect` 合并为 1 章节（标题 `ToolSpec / ToolSideEffect`，锚点 `schema-tool-spec-side-effect`）；合计 19 个一级章节、22 个类型；`Schema 总目录`表共 19 行，但每行的"承载类型数"列须显式标注为 1 或 2。
- Q: 模块 ID（module_id）与 schema ID（schema_id）应使用哪种字面形式？FR-021 用蛇形（`cli` / `runtime`），FR-032 章节标题用 PascalCase（`AgentState` / `Span / Trace`），FR-041 锚点用短横线（`#schema-agent-state`）。三种形式混用。 → A: 章节标题（Markdown `# 标题`）保留 PascalCase 形式以贴近 LangChain / LangGraph 原生类型名；所有 ID（`module_id` / `schema_id` / `feature_id` / `layer_name` / `stage_id`）一律使用英文蛇形小写（如 `agent_state` / `main_loop` / `cli` / `tool_spec_side_effect`）；所有锚点（`#mod-...` / `#schema-...` / `#stage-...` / `#log-tag-...` / `#exit-code-...`）一律使用短横线（kebab-case），即将蛇形 ID 中的下划线替换为短横线。3 份文档中任何表格、依赖矩阵、Feature 拆分映射表、交叉引用都必须使用这一约定，不得混用。
- Q: 退出码集合如何定稿？`{0, 1, 2, 3, 4, 5, 64, 65, 66, 70, 78, 130}` 是我基于 sysexits.h + POSIX + SIGINT 自行拼出的 12 个码。 → A: 保持当前 12 个退出码集合；`workflow.md` 实施时必须以一张"退出码 → 含义 → 触发阶段"表显式列出 12 行映射，不得漏码。0=成功 / 1=通用失败 / 2=用法错误 / 3=数据错误 / 4=I/O 错误 / 5=配置错误 / 64=EX_USAGE / 65=EX_DATAERR / 66=EX_NOINPUT / 70=EX_SOFTWARE / 78=EX_CONFIG / 130=SIGINT。
- Q: workflow.md "用户视角：CLI 生命周期"应覆盖哪些子命令？宪法第 XI 条 2 款说"至少包括" 4 个，但 MDA 还提供 `version` / `tui` / `serve` / `clean` 等辅助子命令。 → A: 保持 4 个核心子命令（`init` / `run` / `eval` / `doctor`），辅助子命令（`version` / `tui` / `serve` / `clean` 等）由后续 Feature 在其 spec 阶段按需追加；本 Feature 不为辅助子命令预留接口（区别于 channels / schedules / sandbox / long_term_memory 这 4 项 v1 占位能力——后者在宪法第 V 条与第 IX 条已有强语义，CLI 辅助子命令则否）。
- Q: workflow.md 阶段锚点形式，FR-016 写 `## dir_load`（锚点 `#dir_load`），FR-041 上一轮澄清后改成 `#stage-dir_load`（带前缀），两份约束形式不一致。 → A: 以 FR-041 为准（带 `stage-` 前缀），FR-016 同步更新；workflow.md 实施时以 `## dir_load {#stage-dir_load}` 显式锚点形式书写，6 个阶段锚点严格为 `#stage-dir_load` / `#stage-config_resolve` / `#stage-model_adapt` / `#stage-graph_compose` / `#stage-main_loop` / `#stage-exit_cleanup`。
- Q: `architecture_modules.md` 模块间依赖矩阵 4 个符号（→ / ↔ / × / –）的语义应如何定义？FR-023 列出符号但未定义含义。 → A: 4 符号严格区分——`→` 强单向允许依赖（行模块可调用列模块，反之不可）；`↔` 双向允许依赖（互为接口、可互相调用）；`×` 明确禁止依赖（与"禁止的依赖方向"小节互为冗余声明，便于矩阵一眼可读）；`–` 无依赖关系（默认，对角线亦用 `–`）。矩阵为完整对称方阵（`A → B` 与 `B → A` 是两个独立单元格，各自显式填符号），每行每列必须填满一个符号，不留空白也不留 NA；自反对角线一律为 `–`。
- Q: module_id 是否必须全局唯一？5 层之间可能存在同名模块（如 `cli` 层有 `runner`，`runtime` 层也有 `runner`）。 → A: 强制全局唯一，冲突时改名（如 `cli_runner` / `runtime_runner`）。理由：依赖矩阵、Feature 拆分映射表、锚点命名空间（`#mod-<module-id>`）均假设主键唯一；跨层重名会令交叉引用歧义。
- Q: 合并章节（如 `Span / Trace` / `SkillSpec / SkillFrontmatter` / `ToolSpec / ToolSideEffect`）内 2 个类型如何组织？FR-033 要求 4 个二级小节，但未说明 2 个类型是共用还是拆分。 → A: 前 2 个二级小节（`Python 类型签名` / `磁盘格式与 schema_version`）共用一套（2 个类型通常属于同一领域、磁盘格式相同），后 2 个二级小节（`与 LangChain/LangGraph 原生类型映射` / `reducer 与不可变约束`）按类型拆为两套并列子小节（字段级映射与不可变约束必须按类型分）。具体地：合并章节下挂"Python 类型签名"与"磁盘格式与 schema_version"两个共用小节，再挂"<类型 A> 与 LangChain/LangGraph 原生类型映射" + "<类型 A> reducer 与不可变约束" + "<类型 B> 与 LangChain/LangGraph 原生类型映射" + "<类型 B> reducer 与不可变约束" 四套并列小节——合并章节下共 6 个二级小节。
- Q: FR-013 退出码表中"触发阶段"列是否允许一个退出码对应多个阶段？例如退出码 2 同时在 `dir_load` 与 `config_resolve` 两个阶段触发，退出码 130 在所有 6 个阶段触发。 → A: 允许多阶段映射。workflow.md 中"退出码 → 含义 → 触发阶段"三列映射表的"触发阶段"列可填 1 个或多个阶段名；多阶段时以 `/` 分隔（如 `dir_load / config_resolve`），或以"所有阶段"统称 6 个阶段。但退出码表的**总行数仍须严格为 12 行**——每个退出码对应表中恰好 1 行，触发阶段数量不影响行数。语义为"该退出码在所列任一阶段触发时即返回"。本表与 FR-016 阶段锚点（`#stage-<id>`）严格一一对应；阶段名集合不变（`dir_load` / `config_resolve` / `model_adapt` / `graph_compose` / `main_loop` / `exit_cleanup`）。
- Q: tasks.md T044 (EvalTaskSpec grader 5 项) 与 T048 (AuditEntry category 4 类) 引入了 <field>_extensibility 字段 + "扩展接口约定"小节的新构造，以替代 FR-043 禁止的 ... 占位符。该构造是否合法？spec 是否应明文授权？ → A: 合法且建议授权。spec.md FR-043 末尾追加 (a) 子条款，明示两条路径——路径 1（推荐）：schema 章节末尾追加"扩展接口约定"二级小节 + <字段名>_extensibility 字段（如 grader_extensibility: list[str] = []）；路径 2（fallback）：直接枚举所有当前取值（Literal），不预留扩展字段。两条路径均不得以 ... 占位。
- Q: spec.md Edge Case E-2 仅在 schema_version 演进时强制要求 migrators 字段，但 v0.1.0 无任何演进发生。migrators 字段在 v0.1.0 应预声明（空列表）还是省略？ → A: v0.1.0 可省略。理由：v0.1.0 是初始版本，无历史 schema_version 可迁，强行预声明空 migrators: list[Migrator] = [] 会污染 schema 字段表而无实际收益；待 schema_version 从 v0.1.0 演进至 v0.2.0 或更高且字段变更时，必须按 E-2 补 migrators 字段并写明迁移动作。E-2 末尾追加 1 句"v0.1.0 处理"澄清。

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 工作流文档（workflow.md）作为阶段切分依据 (Priority: P1)

我作为后续 Feature 的设计者，手中必须有一份**无歧义**的工作流文档，其中以 6 阶段 + CLI 生命周期两个视角定义了 LangAgent 一次完整运行的所有执行单元、失败模式、退出码与日志标签。这份文档是 Feature 01-10+ 拆分任务时"切到哪个阶段"的事实来源；没有它，我无法判断一项新能力该挂在哪个阶段、应该返回哪个退出码、应该打哪个日志标签。

**Why this priority**：6 阶段是 Feature 01-10+ 共同依赖的时间线骨架；CLI 生命周期定义了用户与 LangAgent 的所有交互面。缺一份，Feature 01-10+ 之间会出现阶段命名不一致、退出码冲突、日志标签拼写漂移，进而让 TDD 测试与运行时错误排查都失锚。

**Independent Test**：可独立验证——从 `harness/top_level_design/workflow.md` 中抽取 6 阶段名、退出码集合、日志标签集合，作为字符串字面量构造 3 张对照表（`expected_stages.txt` / `expected_exit_codes.txt` / `expected_log_tags.txt`），人工 / 脚本核验"3 张表互相对齐"且"全部小节齐全"。该测试不依赖任何代码实现。

**Acceptance Scenarios**：

1. **Given** 项目维护者已批准 Feature 00 spec，**When** 实施者按本规范在 `harness/top_level_design/workflow.md` 落盘，**Then** 文档必须包含"用户视角：CLI 生命周期"和"系统视角：6 阶段"两个一级章节，且 6 阶段名严格使用 `dir_load` / `config_resolve` / `model_adapt` / `graph_compose` / `main_loop` / `exit_cleanup`。
2. **Given** workflow.md 描述任一阶段，**When** 我作为后续 Feature 设计者查阅该阶段的"输入 / 输出 / 失败模式 / 退出码 / 日志标签"五栏，**Then** 五栏均不得为空，且退出码必须从 `{0, 1, 2, 3, 4, 5, 64, 65, 66, 70, 78, 130}` 集合中选取。
3. **Given** workflow.md 中出现 "MDA 能力对照表" 章节，**When** 我查阅该表，**Then** 表中每一行必须可追溯到 `harness/Managed_deep_agents/langsmith/python/` 中**至少一份**MDA 文档作为 `source` 字段的相对路径。
4. **Given** workflow.md 任一处提及某个模块或 schema，**When** 我用相对路径跳转 `architecture_modules.md#<module-id>` 或 `module_schemas.md#<schema-id>`，**Then** 目标锚点必须真实存在。
5. **Given** workflow.md 引用宪法第 N 条作为依据，**When** 我查阅引用处，**Then** 引用必须形如 `第 X 条`（中文+阿拉伯数字），不得使用模糊措辞（如"宪法规定"）替代。

---

### User Story 2 — 架构模块文档（architecture_modules.md）作为边界与依赖依据 (Priority: P1)

我作为后续 Feature 的设计者，必须有一份按 5 层划分（CLI / runtime / protocol / middleware+guardrails+observability / LangChain+LangGraph 原语）的架构文档，明确每个模块的职责、关键 API、**允许**与**禁止**的依赖方向、模块间依赖矩阵、模块到 Feature 的拆分映射，以及静态约束 CI 校验清单。这份文档是 Feature 01-10+ "我该往哪一层写"以及"我能不能从 A 层 import B 层"的事实来源；没有它，模块边界会随实现逐步崩塌，单元测试与集成测试的边界也会随之失锚。

**Why this priority**：5 层架构与依赖方向是宪法第 I、II、III、IV 条的工程化落地。5 层之间一旦越界（如 runtime 层反向依赖 CLI 层、或业务节点绕过 middleware 直连 provider），宪法第 II、III、XIII 条将同时失守，TDD 红绿重构循环也会因"测试不知道边界在哪"而失锚。

**Independent Test**：可独立验证——从 `harness/top_level_design/architecture_modules.md` 抽取所有模块 ID 与 `allowed_dependencies` 字段，构造一份邻接表，遍历后用 `grep` / `ripgrep` 在 `harness/top_level_design/` 三份文档之间做静态交叉引用核验，确认"任意模块的依赖方向都不违反矩阵"。

**Acceptance Scenarios**：

1. **Given** architecture_modules.md 已落盘，**When** 我作为后续 Feature 设计者查阅其"5 层架构总览"章节，**Then** 5 层名称必须严格使用 `cli` / `runtime` / `protocol` / `cross_cutting` / `primitives` 五个英文蛇形命名，且每层下挂的模块数 ≥ 2，总模块数 ≥ 12。
2. **Given** 任一模块条目，**When** 我查阅该模块的"允许的依赖方向 / 禁止的依赖方向"两栏，**Then** 两栏均不得为空，且"禁止的依赖方向"中必须显式列出来自其它层的禁止 import。
3. **Given** architecture_modules.md 给出"模块间依赖矩阵"，**When** 我把矩阵渲染成有向图，**Then** 图中不得存在回路（cycle），且任意自下层指向上层的边都必须出现在"禁止的依赖方向"清单中并以注释说明豁免理由（若存在豁免）。
4. **Given** architecture_modules.md 给出"模块到 Feature 的拆分映射表"，**When** 我查阅表中每一行，**Then** 每行必须包含 `module_id` / `feature_id`（形如 `F01`...`F10+`）/ `职责` / `依赖的下游模块` 四列，且 `feature_id` 不得出现 `F00`（F00 即本 Feature 自身）。
5. **Given** architecture_modules.md 给出"静态约束 CI 校验清单"，**When** 我把清单逐条跑过，**Then** 每条必须可由 `grep` / `ripgrep` / 抽象语法树扫描脚本机械实现，不得依赖人工判断。
6. **Given** architecture_modules.md 任一处提及某个 schema，**When** 我跳转到 `module_schemas.md#<schema-id>`，**Then** 目标锚点必须真实存在。

---

### User Story 3 — 模块 schema 文档（module_schemas.md）作为类型契约依据 (Priority: P1)

我作为后续 Feature 的设计者，必须有一份定义模块间**内存类型签名 + 磁盘格式 + schema_version + 与 LangChain/LangGraph 原生类型映射**的 schema 文档，覆盖 AgentState、RuntimeConfig、LoadedAgent、SkillSpec/SkillFrontmatter、ToolSpec/ToolSideEffect、MiddlewareSpec、ChannelSpec、ChannelContext、SandboxSpec、ScheduleSpec、MemorySpec、IdentitySpec、EvalTaskSpec、Span/Trace、Event、MetricsSnapshot、AuditEntry、DoctorReport、EvalReport 共 19 项。这份文档是 Feature 01-10+ 编写 TDD 失败用例时"我要造什么对象、字段是什么、序列化到磁盘长什么样"的事实来源；没有它，跨 Feature 的类型契约会发散，TDD 的"红"会变成"无法断言红"。

**Why this priority**：类型契约是宪法第 VI、IX、X、XII 条在数据层面的体现。AgentState 字段集合与 reducer 规则是 LangGraph 编译态的输入，schema_version 与磁盘格式决定"老 checkpoint 能否被新二进制加载"这一可分发性问题。19 项 schema 缺一则对应 Feature 在 TDD 阶段会因字段名漂移而无法断言。

**Independent Test**：可独立验证——从 `harness/top_level_design/module_schemas.md` 抽取所有 schema 名与字段，构造（a）`expected_schemas.txt`（必须包含 19 项）、（b）`expected_required_fields.json`（每项必填字段清单）、（c）`expected_disk_format.txt`（每项磁盘格式）。三份清单机械核验"集合 = 19"且"每项必填字段非空"且"每项磁盘格式非占位"。

**Acceptance Scenarios**：

1. **Given** module_schemas.md 已落盘，**When** 我作为后续 Feature 设计者查阅其"Schema 总目录"章节，**Then** 必须严格包含 19 个一级章节（承载 22 个类型），且每个一级章节的标题与本规范 FR-032 列举的命名**逐字**一致。
2. **Given** 任一 schema 条目，**When** 我查阅其"Python 类型签名"小节，**Then** 必须显式标注为 `TypedDict` / `Pydantic BaseModel` / `dataclass(frozen=True)` 三选一，且字段类型必须用 `typing` 标注（如 `list[ToolSpec]` / `dict[str, Any]`），不得使用 `Any` 模糊化必填字段。
3. **Given** AgentState schema 条目，**When** 我查阅其"reducer 规则"小节，**Then** 必须显式给出 `messages` / `todos` / `files` / `context` / `scratchpad` 5 个字段的 reducer 规则；`messages` 字段默认 `add_messages`（可自定义）；`context` 字段 reducer 仅限 `overwrite` / `merge_with_prior`（因属会话级元数据）；`files` / `todos` / `scratchpad` 字段均不得使用无脑覆盖式 reducer。
4. **Given** 任一 schema 条目，**When** 我查阅其"磁盘格式 / schema_version"小节，**Then** 磁盘格式必须从 `JSON` / `JSONL` / `YAML` / `TOML` / `MessagePack` / `Parquet` 集合中选取，schema_version 字段必须存在且必须符合 `^v\d+\.\d+\.\d+$` 正则。
5. **Given** 任一 schema 条目，**When** 我查阅其"与 LangChain/LangGraph 原生类型映射"小节，**Then** 映射表至少包含 `langchain_native` 与 `langgraph_native` 两列，若某列不适用则填 `N/A` 并加注释，不得省略。
6. **Given** module_schemas.md 任一处提及某个阶段名或日志标签，**When** 我跳转到 `workflow.md#<stage-id>` 或 `workflow.md#<log-tag-id>`，**Then** 目标锚点必须真实存在。

---

### Edge Cases

- **E-1 阶段间越权调用**：若 workflow.md 中某阶段读取了它本来不该读取的配置（如 `main_loop` 阶段读 `.env`），文档必须在该阶段的"失败模式"小节显式列出一条 `stage_capability_violation` 模式，并引用 architecture_modules.md 中对应模块的"禁止的依赖方向"作为依据。
- **E-2 schema 字段跨版本漂移**：若 module_schemas.md 中某 schema 在 `schema_version` 演进时变更字段，文档必须显式给出 `migrators` 字段（迁移动作说明），不得只追加版本号不写迁移规则。
- **E-2 v0.1.0 处理（来自 Clarification Q12）**：由于当前无任何 schema 演进，migrators 字段在 v0.1.0 可省略；若后续升 schema_version 且字段变更，必须按 E-2 主条款补 migrators 字段并写明迁移动作。
- **E-3 通道 / 调度 / 沙箱 / 长期记忆为 v1 占位**：workflow.md、architecture_modules.md、module_schemas.md 中若提及 channels / schedules / sandbox / long_term_memory，必须以 `v1 预留接口，不实现` 的统一措辞标注，且 module_schemas.md 仍须给出 schema 定义（仅 schema，不含实现），由后续 Feature 启用。
- **E-4 概念命名漂移**：3 份文档之间若对同名概念（阶段名 / 退出码 / 日志标签 / 字段名）出现不同字面量，Success Criteria SC-003 必须把这种情况判定为不通过；文档必须以本文档列出的命名表为准重新对齐。
- **E-5 绝对路径 / 内网 IP / 硬编码密钥潜入**：若任一文档示例中出现 `/Users/...` / `/home/<user>/...` / `C:\...` / `192.168.x.x` / `10.x.x.x` / `172.16-31.x.x` / `sk-...` / `LANGSMITH_API_KEY=...` / `OPENAI_API_KEY=sk-...` 之类硬编码，Success Criteria SC-004 必须判定为不通过；示例必须改为 `path/to/...` / `internal.example` / `<redacted>` 等占位写法。
- **E-6 文档间锚点死链**：若任一文档中以相对路径 + 锚点形式引用了另一份文档的章节，但目标文档中该锚点不存在，Success Criteria SC-002 必须判定为不通过；锚点命名空间必须以本规范 E 节"交叉引用规则"为准。
- **E-7 宪法与文档冲突**：若 3 份文档任一处与宪法第 I-XIV 条冲突（如"允许 import LangSmith"、"硬编码 provider"），Success Criteria SC-006 必须判定为不通过；文档必须显式标注 `与宪法第 N 条冲突，已以宪法为准修正` 的注释。

---

## Requirements *(mandatory)*

### Functional Requirements

#### 文档存在性

- **FR-001**：Feature 00 必须在仓库根的 `harness/top_level_design/` 目录下**落盘** 3 份 Markdown 设计文档，文件名严格为 `workflow.md` / `architecture_modules.md` / `module_schemas.md`（全小写、下划线分隔、`md` 后缀）。
- **FR-002**：3 份文档每份的行数必须 ≥ 200 行（空行计入；不含任何"自动生成头"元数据）。
- **FR-003**：3 份文档的字符编码必须为 UTF-8，行尾必须为 LF；不得出现 BOM。

#### workflow.md 必备小节（User Story 1 落地）

- **FR-010**：workflow.md 顶层必须包含"文档元信息"小节，至少含 `doc_id` / `version` / `last_updated` / `constitution_ref` / `related_docs` 五字段，`related_docs` 必须以相对路径列出 `architecture_modules.md` 与 `module_schemas.md`。
- **FR-011**：workflow.md 必须包含"用户视角：CLI 生命周期"一级章节；下挂的 CLI 子命令固定为 `init` / `run` / `eval` / `doctor` 4 个（不预留辅助子命令接口；如需新增，由后续 Feature 在其 spec 阶段追加并修订本规范），每个子命令必须给出来自用户、来自项目维护者两个视角的输入 / 输出 / 失败模式 / 退出码 / 日志标签五栏。每个 CLI 子命令的 5 栏每栏 ≥ **3 项**（与 research R-4 下界对齐），不得少于 3 项；栏内每项至少 1 句话说明。本规范中『项』特指项目符号列表项（即 Markdown `- ...` 列表条目），每项至少 1 句话说明；不得以段落或编号列表替代。
- **FR-012**：workflow.md 必须包含"系统视角：6 阶段"一级章节，6 阶段名严格为 `dir_load` / `config_resolve` / `model_adapt` / `graph_compose` / `main_loop` / `exit_cleanup`（英文蛇形命名，不允许中文别名）。每个阶段必须给出五栏：`输入` / `输出` / `失败模式` / `退出码` / `日志标签`，五栏均不得为空。每个阶段的 5 栏每栏 ≥ **3 项**（与 research R-4 下界对齐），不得少于 3 项。本规范中『项』特指项目符号列表项（即 Markdown `- ...` 列表条目），每项至少 1 句话说明；不得以段落或编号列表替代。每个阶段的"失败模式"小节必须显式列出 `stage_capability_violation` 模式（即"阶段读取了不属于本阶段范围的配置 / 文件 / 状态"，对应 Edge Case E-1），不得遗漏；该模式即使在当前实现中不触发，也必须以 fail-safe 文档形式存在。
- **FR-013**：退出码集合固定为 12 个 `{0, 1, 2, 3, 4, 5, 64, 65, 66, 70, 78, 130}`，workflow.md 中必须以一张统一表格显式列出"退出码 → 含义 → 触发阶段"三列映射，**共 12 行不得漏码**；具体语义绑定为：0=成功 / 1=通用失败 / 2=用法错误 / 3=数据错误 / 4=I/O 错误 / 5=配置错误 / 64=EX_USAGE / 65=EX_DATAERR / 66=EX_NOINPUT / 70=EX_SOFTWARE / 78=EX_CONFIG / 130=SIGINT。
- **FR-014**：日志标签集合必须以 `la.` 前缀开头（如 `la.cli.init.start` / `la.runtime.main_loop.turn`），且在 workflow.md 中以一张统一表格显式列出"日志标签 → 含义 → 触发阶段"映射。日志标签表至少 **15 行**（硬下限），不得少于 15 行；如希望充分覆盖可参考 research R-5 给出的 25 项初始集合，但 R-5 不作为强制目标。
- **FR-015**：workflow.md 必须包含"MDA 能力对照表"一级章节，表中每一行必须含 `mda_capability` / `mda_source_path` / `langagent_equivalent_stage` / `notes` 四列，`mda_source_path` 必须为 `harness/Managed_deep_agents/langsmith/python/<file>.md` 形式的相对路径。MDA 能力对照表至少 **10 行**，每行对应 `harness/Managed_deep_agents/langsmith/python/managed-deep-agents-*.md` 中 1 份 MDA 文档作为 `mda_source_path`。
- **FR-016**：workflow.md 中每个阶段、退出码、日志标签必须拥有**显式锚点**（以 `## <标题> {#<锚点>}` 形式书写，禁止依赖 Markdown 自动生成的锚点）；6 个阶段锚点严格为 `#stage-dir_load` / `#stage-config_resolve` / `#stage-model_adapt` / `#stage-graph_compose` / `#stage-main_loop` / `#stage-exit_cleanup`；12 个退出码锚点严格为 `#exit-code-0` / `#exit-code-1` / ... / `#exit-code-130`；日志标签锚点形如 `#log-tag-la-cli-init-start`（点号替换为短横线）。`#stage-*` 前缀的引入是为了避免与模块锚点（`#mod-*`）和 schema 锚点（`#schema-*`）撞名。

#### architecture_modules.md 必备小节（User Story 2 落地）

- **FR-020**：architecture_modules.md 顶层必须包含"文档元信息"小节，字段集合同 FR-010。
- **FR-021**：architecture_modules.md 必须包含"5 层架构总览"一级章节，5 层英文蛇形命名严格为 `cli` / `runtime` / `protocol` / `cross_cutting` / `primitives`。
- **FR-022**：每一层下挂**至少 2 个模块**（与 research R-1.3 对齐；理由：避免 5×5 矩阵过小、无法体现层间差异；总模块数 ≥ 12）；每个模块必须给出来自`职责` / `关键 API`（WHAT 视角，不写实现）/ `允许的依赖方向` / `禁止的依赖方向` 四栏。`module_id` 必须在 5 层之间**全局唯一**（不同层出现同名模块时，必须改名为 `cli_runner` / `runtime_runner` 这种带层语义前缀的形式），不得在不同层下重名；冲突检测可在静态约束 CI 校验清单（FR-025）中以 `CHK-AR-NNN | module_id 全局唯一性 | grep + sort + uniq -d` 形式实现。每个模块的 4 栏每栏 ≥ **1 项**（不得为空）：'职责'栏 ≥ **2 项**（主职责 + 副职责）；'关键 API' ≥ 1 项；'允许的依赖方向' ≥ 1 项；'禁止的依赖方向' ≥ 1 项（与 research R-1.3 对齐）。
- **FR-023**：architecture_modules.md 必须包含"模块间依赖矩阵"一级章节，矩阵为**完整对称方阵**（行列均为模块 ID，蛇形小写），单元格从 `→` / `↔` / `×` / `–` 四个符号中选取；4 符号语义严格为：`→` 强单向允许依赖（行可调列，反之不可）；`↔` 双向允许依赖（互为接口）；`×` 明确禁止依赖；`–` 无依赖关系（默认，对角线亦为 `–`）。**每行每列每个单元格必须填满一个符号**，不留空白、不留 NA；自反对角线一律为 `–`。矩阵中 `→` 与 `↔` 的边集合（即"允许依赖"边）**必须**无回路（构造有向图跑拓扑排序验证）。
- **FR-024**：architecture_modules.md 必须包含"模块到 Feature 的拆分映射表"一级章节，列必须含 `module_id` / `feature_id`（`F01`..`F10+`）/ `职责` / `依赖的下游模块` 四列；`feature_id` 列不得出现 `F00`。
- **FR-025**：architecture_modules.md 必须包含"静态约束 CI 校验清单"一级章节，每条约束必须以 `- ID: CHK-AR-NNN | 约束描述 | 实现方式（grep / ripgrep / AST）` 形式书写，实现方式列不得包含"人工"二字。静态约束 CI 校验清单至少 **12 条**，覆盖范围建议：3 条文档存在性 / 3 条锚点命名空间 / 2 条依赖矩阵 / 2 条 module_id 全局唯一 / 2 条宪法一致性。
- **FR-026**：architecture_modules.md 中每个模块必须拥有显式锚点（形如 `#mod-<module-id>`，其中 `<module-id>` 为英文蛇形小写，锚点中将下划线替换为短横线；示例：`#mod-agent-state-loader`），以便 module_schemas.md 与 workflow.md 反向引用。

#### module_schemas.md 必备小节（User Story 3 落地）

- **FR-030**：module_schemas.md 顶层必须包含"文档元信息"小节，字段集合同 FR-010。
- **FR-031**：module_schemas.md 必须包含"Schema 总目录"一级章节，以表格列出全部 19 个**一级章节**（承载 22 个类型；3 对天然耦合的 schema 各自合并为一个一级章节），每行至少含 `schema_id` / `python_kind` / `schema_version` / `disk_format` / `承载类型数` 五列；表末必须有合计行 `合计 — — — — 19 / 22`。
- **FR-032**：module_schemas.md 必须包含 19 个**一级章节**（承载 22 个类型），每章节标题**逐字**对应以下列表（顺序亦同）：
  1. `AgentState`
  2. `RuntimeConfig`
  3. `LoadedAgent`
  4. `SkillSpec / SkillFrontmatter`（合并章节，承载 2 个类型）
  5. `ToolSpec / ToolSideEffect`（合并章节，承载 2 个类型）
  6. `MiddlewareSpec`
  7. `ChannelSpec`
  8. `ChannelContext`
  9. `SandboxSpec`
  10. `ScheduleSpec`
  11. `MemorySpec`
  12. `IdentitySpec`
  13. `EvalTaskSpec`
  14. `Span / Trace`（合并章节，承载 2 个类型）
  15. `Event`（章节正文标题为"Event 总线"）
  16. `MetricsSnapshot`
  17. `AuditEntry`
  18. `DoctorReport`
  19. `EvalReport`
  
  （说明：上列共 19 个一级章节；其中第 4、5、14 项为合并章节，各自承载 2 个类型；合计承载 22 个类型。`Schema 总目录`表的行数 = 19。本规范 Key Entities "Module Schema" 列举的 schema 数量按"19 个一级章节"统计；schema 类型的总数（22）则在表末"合计行"显式标注。）
- **FR-033**：每项 schema 的一级章节下必须含 4 个基础二级小节：`Python 类型签名` / `磁盘格式与 schema_version` / `与 LangChain/LangGraph 原生类型映射` / `reducer 与不可变约束`（仅 AgentState 必须给出 reducer；其余 schema 给出不可变约束说明即可）。**承载单类型的 16 个非合并章节中**，这 4 个二级小节各出现 1 次；**承载 2 个类型的 3 个合并章节（`Span / Trace` / `SkillSpec / SkillFrontmatter` / `ToolSpec / ToolSideEffect`）中**，前 2 个二级小节（`Python 类型签名` / `磁盘格式与 schema_version`）共用 1 套（2 个类型磁盘格式相同），后 2 个二级小节（`与 LangChain/LangGraph 原生类型映射` / `reducer 与不可变约束`）按类型拆为 2 套并列子小节，命名形如 `<类型 A> 与 LangChain/LangGraph 原生类型映射` / `<类型 A> reducer 与不可变约束` ——合并章节下共 6 个二级小节。
- **FR-034**：`Python 类型签名`小节中，每项 schema 必须显式标注为 `TypedDict` / `Pydantic BaseModel` / `dataclass(frozen=True)` 三选一；必填字段不得使用 `Any`。
- **FR-035**：`磁盘格式与 schema_version`小节中，磁盘格式必须从 `JSON` / `JSONL` / `YAML` / `TOML` / `MessagePack` / `Parquet` 集合中选取；`schema_version` 字段必须存在且符合 `^v\d+\.\d+\.\d+$` 正则。
- **FR-036**：`与 LangChain/LangGraph 原生类型映射`小节中，表格必须含 `field` / `langchain_native` / `langgraph_native` / `notes` 四列；若某列不适用，填 `N/A` 并加注释，不得省略。
- **FR-037**：`AgentState` 章节的 `reducer 与不可变约束`小节必须显式给出 `messages` / `todos` / `files` / `context` / `scratchpad` 共 5 个字段的 reducer 规则；`messages` 字段默认 `add_messages`，若项目自定义必须显式说明；`context` 字段的 reducer 必须从 `overwrite` / `merge_with_prior` 中选取（`context` 为会话级元数据，非追加流），不得使用追加式 reducer；`files` / `todos` / `scratchpad` 字段均不得使用无脑覆盖式 reducer。

#### 交叉引用规则

- **FR-040**：3 份文档之间的引用必须使用**相对路径**，相对路径起点为引用方所在目录（即 `harness/top_level_design/`），因此目标文件路径为 `architecture_modules.md` / `module_schemas.md` / `workflow.md`（不带 `./` 前缀，不带 `../`）。对智能体目录外（但仓库内）的文件相对路径，以引用方所在目录为起点，使用 `../`
拼接跨目录，每跳一层加一个 `../`。例如 3 份文档中的 `constitution_ref`
应写为 `../../.specify/memory/constitution.md`（仓库根的宪法文件位于
`harness/top_level_design/` 的两级父目录）。
- **FR-041**：3 份文档之间引用的锚点必须采用以下命名空间：
  - 阶段锚点：`#stage-dir_load` / `#stage-config_resolve` / `#stage-model_adapt` / `#stage-graph_compose` / `#stage-main_loop` / `#stage-exit_cleanup`（workflow.md 一级章节直接作为锚点，ID 形如 `dir_load`，锚点前缀 `stage-`）。
  - 退出码锚点：`#exit-code-<n>`（n 为阿拉伯数字）。
  - 日志标签锚点：`#log-tag-<la.xx.yy.zz>`（点号替换为短横线）。
  - 模块锚点：`#mod-<module-id>`（architecture_modules.md），其中 `<module-id>` 为英文蛇形小写，锚点中下划线替换为短横线；示例：`#mod-agent-state-loader` / `#mod-cli-runner` / `#mod-main-loop-dispatcher`。
  - schema 锚点：`#schema-<schema-id>`（module_schemas.md），具体为：
    - 单类型章节（共 16 个）：`#schema-agent-state` / `#schema-runtime-config` / `#schema-loaded-agent` / `#schema-middleware-spec` / `#schema-channel-spec` / `#schema-channel-context` / `#schema-sandbox-spec` / `#schema-schedule-spec` / `#schema-memory-spec` / `#schema-identity-spec` / `#schema-eval-task-spec` / `#schema-event` / `#schema-metrics-snapshot` / `#schema-audit-entry` / `#schema-doctor-report` / `#schema-eval-report`；
    - 合并章节（共 3 个）：`#schema-skill-spec-frontmatter`（承载 SkillSpec + SkillFrontmatter）/ `#schema-tool-spec-side-effect`（承载 ToolSpec + ToolSideEffect）/ `#schema-span-trace`（承载 Span + Trace）。
- **FR-042**：3 份文档均不得引用仓库外的相对路径、绝对路径、URL、内部 IP。
- **FR-043**：3 份文档均不得出现"TODO" / "TBD" / "留待决定" / "FIXME" / "XXX" / "...此处略" 之类占位词；缺内容的格子必须以 `<待本 Feature 实施时填充>` 之外的更具体表述（如 `此处不适用，因为 ...`）说明。
  - **(a) 扩展占位禁止（来自 Clarification Q11）**：不得以 `...` / `<其它枚举>` / `etc.` 等省略号占位符表达"未来可能新增的取值"。如需表达扩展点，必须从以下两条路径中选取其一：
    - **路径 1（推荐）**：在 schema 一级章节末尾追加"扩展接口约定"二级小节，以 `<字段名>_extensibility` 命名约定列出扩展字段（如 `grader_extensibility: list[str] = []` / `category_extensibility: list[str] = []`），明示"未来新增值应登记到该字段"，禁止用 `...` 占位。
    - **路径 2（fallback）**：直接枚举所有当前取值（如 `category: Literal["pii_leak", "unauthorized_tool", "prompt_injection"]`），不预留扩展字段；如需新增，必须新增 Literal 元素并升 schema_version（触发 E-2 的 migrators 规则）。

#### 与宪法一致性

- **FR-050**：3 份文档均不得引入与宪法第 I-XIV 条相冲突的约束；若因设计需要触及宪法条款边界（如"是否属于 SDK"的判定），文档必须以 `与宪法第 N 条关系：...` 形式显式说明，并指向宪法原文。
- **FR-051**：3 份文档均不得出现 LangSmith 闭源依赖相关的 import 名 / API 名 / 环境变量名 / 镜像名 / Helm chart 名；示例中若必须提及，措辞必须为`LangSmith 仅作反例：不应 ...`。
- **FR-052**：3 份文档均不得在示例中硬编码 API key、内网 IP、绝对路径；必须使用占位写法（`sk-<redacted>` / `internal.example` / `path/to/agent`）。

#### 文档元数据

- **FR-060**：每份文档的"文档元信息"小节必须含 `doc_id` / `version` / `last_updated` / `constitution_ref` / `related_docs` 5 字段；`version` 字段在 Feature 00 实施期间固定为 `v0.1.0`。
- **FR-061**：每份文档末尾必须包含"变更日志"小节，至少 1 条记录（Feature 00 初版）。

### Key Entities

- **Workflow Document（workflow.md）**：
  - 一份 Markdown 设计文档。
  - 属性：阶段名（6 项，英文蛇形）、退出码集合、日志标签集合、MDA 能力对照行。
  - 关系：每条退出码 / 日志标签 / 阶段名都拥有自己的锚点；每个阶段都引用 architecture_modules.md 中 1 至 N 个模块；每个阶段都引用 module_schemas.md 中 1 至 N 个 schema。
  - 不可变：阶段名集合在 Feature 00 期间不得新增（`dir_load`...`exit_cleanup` 共 6 个）；后续 Feature 如需新增阶段必须修订本规范。

- **Architecture Module（architecture_modules.md）**：
  - 一个模块（`module_id`，英文蛇形小写，且在 5 层之间**全局唯一**，冲突时改名；命名建议带层语义前缀，如 `cli_runner` / `runtime_runner` / `agent_state_loader` / `main_loop_dispatcher`）。
  - 属性：所属层（`cli` / `runtime` / `protocol` / `cross_cutting` / `primitives`）、职责、关键 API、允许的依赖方向、禁止的依赖方向。
  - 关系：每个模块依赖矩阵中若干其它模块（无回路）；每个模块被映射到 1 个 `feature_id`（`F01`..`F10+`）；每个模块可被 0 至 N 个 schema 引用。
  - 不可变：5 层名称集合在 Feature 00 期间不得新增（5 个固定值）；后续 Feature 如需新增层必须修订本规范并附 RFC。

- **Module Schema（module_schemas.md）**：
  - 一个一级章节（`schema_id`，英文蛇形小写，如 `agent_state` / `tool_spec_side_effect` / `span_trace`；章节标题保留 PascalCase 形式以贴近 LangChain / LangGraph 原生类型名）。
  - 属性：Python 类型签名（`TypedDict` / `Pydantic BaseModel` / `dataclass(frozen=True)` 三选一）、磁盘格式（6 选 1）、`schema_version`（`^v\d+\.\d+\.\d+$`）、与 LangChain/LangGraph 原生类型的映射、承载类型数（`1` 或 `2`）。
  - 关系：每个一级章节可被 0 至 N 个模块读写；AgentState 拥有 reducer 规则集合；`Span / Trace` 合并章节承载的 2 个类型被 Event 总线、MetricsSnapshot、AuditEntry 引用。
  - 不可变：19 个一级章节（承载 22 个类型）列表在 Feature 00 期间不得新增、不得删除、不得重命名（合并 / 拆分须在 Key Entities 中显式声明）。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：`harness/top_level_design/workflow.md`、`harness/top_level_design/architecture_modules.md`、`harness/top_level_design/module_schemas.md` 三份文件均存在，且每份文件 `wc -l` 结果 ≥ 200。
- **SC-002**：在 3 份文档组成的相对路径 + 锚点引用集合中，机械扫描（`grep` 抓取所有 `](#...)` 与 `](...md#...)` 形式）后无死链；任一引用在目标文档中均可找到对应锚点。扫描脚本在 `requirements.md` 校验清单中显式列出。
- **SC-003**：3 份文档对"阶段名 / 退出码 / 日志标签 / 字段名"4 类同名概念的字面量完全一致；任一处字面量漂移（即"main_loop" 写成了 "mainloop" 或 "MainLoop"）即判定不通过。一致性表作为 `requirements.md` 校验清单的一项。
- **SC-004**：3 份文档不出现任何形如 `/Users/...` / `/home/<user>/...` / `C:\...` 的绝对路径；不出现任何形如 `192.168.x.x` / `10.x.x.x` / `172.16-31.x.x` 的内网 IP；不出现任何形如 `sk-...` / `LANGSMITH_API_KEY=...` / `OPENAI_API_KEY=sk-...` 的硬编码密钥。扫描脚本使用 `grep -E` 对正则核验，列于 `requirements.md`。
- **SC-005**：3 份文档不出现 `TODO` / `TBD` / `FIXME` / `XXX` / `留待决定` / `待定` / `占位` / `...此处略` 等占位词；扫描使用 `grep -wE 'TODO|TBD|FIXME|XXX|留待决定|待定|占位'`，列于 `requirements.md`。
- **SC-006**：3 份文档与宪法第 I-XIV 条无冲突；若实施者发现需要触及宪法条款边界（如"模块 → 协议层是否属于 SDK"），文档中必须以 `与宪法第 N 条关系：...` 形式显式标注，且不得擅自修改宪法。这一项以人工 review 为主、人工 + `grep` 抽查为辅，列于 `requirements.md`。
- **SC-007**：本规范的 `checklists/requirements.md`（Feature 00 的 requirements.md 校验清单）所列每一条验证项均可由"机械脚本 + 人工 review"组合方式跑过；每条验证项后必须显式注明"机械 / 人工 / 二者"。
- **SC-008**：本 Feature 的范围严格限于 3 份 Markdown 设计文档；Feature 00 完成后，仓库内不出现 `langagent/` Python 包、不出现 `tests/` 目录、不出现 `pyproject.toml`、不出现任何 `.py` 源文件（除 `.specify/scripts/bash/*.sh` 等基础设施脚本外），亦不出现任何 `Feature 01`..`Feature 10+` 的 spec 文件。`find` 脚本列于 `requirements.md`。

---

## Assumptions

- A-1：项目宪法（`.specify/memory/constitution.md`，v1.0.0，2026-09-14 定稿）在 Feature 00 实施期间不再变更；如必须变更，按宪法第 XIV 条走 RFC 流程，并相应修订本规范。
- A-2：LangChain 与 LangGraph 的官方 API 行为以 `harness/LangChain_doc/` 与 `harness/LangGraph_doc/` 下的本地副本为**唯一可信来源**；不在本规范中要求实施者访问外网或推断未在本地副本中出现的 API 行为。
- A-3：Managed Deep Agents（MDA）仅作**设计参考**；Feature 00 不 import、不 pip install、不复制 MDA 任何代码片段到 LangAgent 主代码或文档中。
- A-4：Feature 00 不实现 channels（IM 通道）、schedules（定时调度）、long_term_memory（长期记忆）、sandbox（沙箱；SandboxSpec.sandbox_type 候选 docker / firecracker / local-subprocess）这 4 项 v1 占位能力；仅在 workflow.md / architecture_modules.md / module_schemas.md 中以"v1 预留接口，不实现"的统一措辞预留接口，由后续 Feature 启用。
- A-5：3 份文档语言为中文（章节标题、叙述、表格文字、注释），代码示例与类型名 / 字段名以英文书写；日志标签、退出码、阶段名、模块 ID、schema ID 一律使用英文蛇形或 PascalCase，不得中英混拼。
- A-6：3 份文档完成后须由项目维护者本人进行人工 review；人工 review 通过后，方可进入 Feature 01-10+ 的 spec / plan / tasks 阶段；人工 review 不通过则迭代修订直至通过。
- A-7：本规范仅约定 3 份文档的 WHAT & WHY 边界，不约束具体的段落编排、字体、Markdown 风格细节（除锚点命名空间与禁用占位词外），允许实施者在必备小节内自由发挥。
- A-8：本规范的"用户"专指后续 Feature 的设计者与实现者（即项目维护者本人），**不**指代终端用户；所有 User Story、Acceptance Scenarios、Success Criteria 皆从该视角书写。
- A-9：本规范在 spec.md 末尾要求生成 `requirements.md` 校验清单（路径 `specs/000-top-level-design/checklists/requirements.md`），其内容由本规范的 SC-001..SC-008 衍生，不另行创建独立文件。
- A-10：项目根不存在 `.specify/extensions.yml`；本 Feature 不触发任何 `before_specify` / `after_specify` 扩展钩子；如未来引入 extensions.yml，按钩子定义执行，本规范不预先约定钩子行为。

---

## Out of Scope

- OOS-1：编写任何 `langagent/` 下的 Python 源代码（包初始化、CLI 入口、runtime、protocol、middleware、graph 组合、State 实现等）。
- OOS-2：生成 `pyproject.toml`、Pipfile、poetry.lock、requirements.txt 等任何依赖声明文件。
- OOS-3：生成 `tests/` 目录、pytest 配置、任何测试用例（单元 / 集成 / 回归 / 端到端）。本条与宪法第 VIII 条（开发方法论 TDD 刚性约束）的关系：第 VIII 条 "测试驱动开发" 的语义范围限定于 "产生可执行代码的功能开发"；Feature 00 仅产出 Markdown 设计文档、不产生可执行代码，故第 VIII 条不触发；本 Feature 的产出物验证由 `quickstart.md` §QS-1 机械脚本与 §QS-2 人工 review 共同承担（详见 tasks.md T053 / T054）。
- OOS-4：修改项目宪法（`.specify/memory/constitution.md`），或对宪法第 I-XIV 条做任何注释性 / 实质性修订。
- OOS-5：提前开启 Feature 01-10+ 的 spec / plan / tasks 撰写；Feature 00 完成后必须先经人工 review 通过，再进入下一个 Feature。
- OOS-6：编写 CLI 二进制的可执行入口（`langagent run` / `init` / `eval` / `doctor`）的任何实现。
- OOS-7：编写智能体目录的模板生成器（`langagent init <name>` 的实现）。
- OOS-8：实现 v1 占位能力（channels / schedules / long_term_memory / sandbox（SandboxSpec.sandbox_type 候选 docker / firecracker / local-subprocess））的任何运行时；仅文档中预留接口。
- OOS-9：实现任何 LangGraph 图（`CompiledStateGraph`）、任何 State schema 的实际类、任何 middleware 的实际函数。
- OOS-10：搭建 CI / CD 流水线、静态约束扫描脚本、Docker 镜像、PyInstaller 打包脚本。
- OOS-11：发布 README、CHANGELOG、安装指南、用户使用文档（这些属于"面向终端用户"的产物，超出本规范的"用户"边界）。
- OOS-12：在 harness 之外的位置（如 `docs/`、`top_level_design/` 根目录、`designs/`）创建额外的设计文档；本 Feature 的全部设计文档严格位于 `harness/top_level_design/` 目录。
