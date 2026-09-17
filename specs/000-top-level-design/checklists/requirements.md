# Specification Quality Checklist: Feature 00 — 顶层设计（Top-Level Design）

**Purpose**: 校验本规范（`spec.md`）本身的质量，以及在实施阶段对 3 份 Markdown 设计文档（`workflow.md` / `architecture_modules.md` / `module_schemas.md`）的产出物校验。
**Created**: 2026-09-14
**Feature**: [spec.md](./spec.md)

> 标记约定：`[x]` 表示校验项已被审阅并满足；未勾选则表示仍需澄清、修正或审阅。
> `机械` 表示可由脚本 / `grep` / `ripgrep` / AST 自动核验；`人工` 表示需项目维护者 review；`二者` 表示两者结合。

---

## 1. 内容质量（Content Quality）

- [x] CHK001 规范未规定实现细节（无具体语言、框架、API、IDE、构建工具的硬性要求；仅在举例处提及 LangChain、LangGraph、Pydantic 等用于澄清边界的工具名） — 机械+人工
- [x] CHK002 规范聚焦于"价值与必要性"（3 份文档为什么必须存在、缺一会发生什么、字段为什么必填）而非"实现步骤" — 人工
- [x] CHK003 规范面向"项目维护者本人"（后续 Feature 设计者与实现者），未使用面向终端用户的措辞 — 人工
- [x] CHK004 所有 Mandatory 章节（User Scenarios & Testing、Requirements、Success Criteria、Assumptions、Out of Scope）均已填写，无"N/A"占位 — 人工
- [x] CHK005 不出现"TODO" / "TBD" / "FIXME" / "XXX" / "留待决定" / "待定" 之类占位词 — 机械（`grep -wE`）

## 2. 需求完整性（Requirement Completeness）

- [x] CHK010 规范中不遗留 `[NEEDS CLARIFICATION]` 占位符 — 机械（`grep -F '[NEEDS CLARIFICATION]'`）
- [x] CHK011 每条 Functional Requirement（FR-001..FR-061）皆可机械核验或人工 review，无歧义措辞 — 机械+人工
- [x] CHK012 Success Criteria（SC-001..SC-008）皆可量化核验（行数、死链、字面量一致性、占位词、绝对路径 / 内网 IP / 硬编码密钥、与宪法一致性、范围零代码） — 机械+人工
- [x] CHK013 Success Criteria 不涉及实现细节（不指定具体技术栈、不指定具体脚本语言、不指定具体 CI 平台） — 人工
- [x] CHK014 3 份 User Story 的 Acceptance Scenarios 完整覆盖"主流程 + 边界条件" — 人工
- [x] CHK015 Edge Cases 至少覆盖：阶段越权调用、schema 字段漂移、v1 占位能力、概念命名漂移、绝对路径 / 内网 IP / 密钥潜入、文档间锚点死链、宪法冲突（7 项） — 人工
- [x] CHK016 Out of Scope 至少覆盖：langagent 代码、pyproject.toml、tests/、宪法修改、Feature 01-10+ spec、其他超出范围项（12 项） — 人工
- [x] CHK017 Assumptions 至少覆盖：宪法定稿、官方文档唯一可信、MDA 仅参考、v1 占位能力、文档语言、review 流程（6 项必需 + 4 项补充） — 人工

## 3. 功能就绪度（Feature Readiness）

- [x] CHK020 3 份 User Story 优先级均为 P1（3 份文档同等重要） — 人工
- [x] CHK021 3 份 User Story 各自有独立的 Independent Test（不互相依赖实施） — 人工
- [x] CHK022 Key Entities 至少包含：Workflow Document、Architecture Module、Module Schema（3 项） — 人工
- [x] CHK023 Key Entities 中每项的"属性 / 关系 / 不可变"三段说明完整 — 人工

## 4. 文档结构约束（Document Structure Constraints — 针对实施阶段 3 份文档）

> 本节为实施阶段 3 份 Markdown 设计文档的产出物校验项；本 Feature 自身（spec.md）已完成，本节用于实施者 review。

### 4.1 文档存在性与体量

- [ ] CHK100 `harness/top_level_design/workflow.md` 存在且 `wc -l` ≥ 200 — 机械
- [ ] CHK101 `harness/top_level_design/architecture_modules.md` 存在且 `wc -l` ≥ 200 — 机械
- [ ] CHK102 `harness/top_level_design/module_schemas.md` 存在且 `wc -l` ≥ 200 — 机械
- [ ] CHK103 三份文件字符编码为 UTF-8，行尾为 LF，无 BOM — 机械（`file` 命令 + `hexdump | head`）

### 4.2 workflow.md 必备小节

- [ ] CHK110 含"文档元信息"小节，字段含 `doc_id` / `version` / `last_updated` / `constitution_ref` / `related_docs` — 机械
- [ ] CHK111 含"用户视角：CLI 生命周期"一级章节，覆盖 `init` / `run` / `eval` / `doctor` 4 个子命令 — 机械
- [ ] CHK112 含"系统视角：6 阶段"一级章节，6 阶段名为 `dir_load` / `config_resolve` / `model_adapt` / `graph_compose` / `main_loop` / `exit_cleanup` — 机械
- [ ] CHK113 每个阶段有五栏：`输入` / `输出` / `失败模式` / `退出码` / `日志标签`，五栏均非空 — 机械+人工
- [ ] CHK114 退出码集合在 `{0, 1, 2, 3, 4, 5, 64, 65, 66, 70, 78, 130}` 内 — 机械（`grep -E` 抓取所有"退出码: <n>"行）
- [ ] CHK115 日志标签以 `la.` 前缀开头 — 机械
- [ ] CHK116 含"MDA 能力对照表"一级章节，行含 `mda_capability` / `mda_source_path` / `langagent_equivalent_stage` / `notes` 四列 — 机械+人工
- [ ] CHK117 每个阶段、退出码、日志标签有显式锚点 — 机械

### 4.3 architecture_modules.md 必备小节

- [ ] CHK120 含"文档元信息"小节（字段同 FR-060） — 机械
- [ ] CHK121 含"5 层架构总览"一级章节，5 层名称为 `cli` / `runtime` / `protocol` / `cross_cutting` / `primitives` — 机械
- [ ] CHK122 每层下挂至少 2 个模块；总模块数 ≥ 12；每模块有四栏 `职责` / `关键 API` / `允许的依赖方向` / `禁止的依赖方向` — 机械+人工
- [ ] CHK123 含"模块间依赖矩阵"一级章节，矩阵无回路（机械：构造有向图跑拓扑排序） — 机械
- [ ] CHK124 含"模块到 Feature 的拆分映射表"一级章节，列含 `module_id` / `feature_id` / `职责` / `依赖的下游模块` 四列；`feature_id` 不得出现 `F00` — 机械
- [ ] CHK125 含"静态约束 CI 校验清单"一级章节，约束以 `CHK-AR-NNN | 描述 | 实现方式` 形式书写；实现方式列不含"人工" — 机械
- [ ] CHK126 每个模块有显式锚点 `#mod-<module-id>` — 机械

### 4.4 module_schemas.md 必备小节

- [ ] CHK130 含"文档元信息"小节（字段同 FR-060） — 机械
- [ ] CHK131 含"Schema 总目录"一级章节，列出 19 项 schema，行含 `schema_id` / `python_kind` / `schema_version` / `disk_format` / `承载类型数` 五列；表末必须有合计行 `合计 — — — — 19 / 22` — 机械
- [ ] CHK132 19 项 schema 标题逐字对应 FR-032 列表（AgentState / RuntimeConfig / LoadedAgent / SkillSpec / SkillFrontmatter / ToolSpec / ToolSideEffect / MiddlewareSpec / ChannelSpec / ChannelContext / SandboxSpec / ScheduleSpec / MemorySpec / IdentitySpec / EvalTaskSpec / Span/Trace / Event / MetricsSnapshot / AuditEntry / DoctorReport / EvalReport，其中 Span/Trace 共占一项一级章节，Event 文档表述为"Event 总线"，AuditEntry / DoctorReport / EvalReport 各占一项，故一级章节总数为 19） — 机械
- [ ] CHK133 每项 schema 含 4 个二级小节：`Python 类型签名` / `磁盘格式与 schema_version` / `与 LangChain/LangGraph 原生类型映射` / `reducer 与不可变约束` — 机械
- [ ] CHK134 `Python 类型签名`中每项标注为 `TypedDict` / `Pydantic BaseModel` / `dataclass(frozen=True)` 三选一；必填字段不使用 `Any` — 机械+人工
- [ ] CHK135 `磁盘格式与 schema_version`中磁盘格式从 `JSON` / `JSONL` / `YAML` / `TOML` / `MessagePack` / `Parquet` 中选取；`schema_version` 符合 `^v\d+\.\d+\.\d+$` — 机械
- [ ] CHK136 `与 LangChain/LangGraph 原生类型映射`小节含 `field` / `langchain_native` / `langgraph_native` / `notes` 四列；不适用者填 `N/A` 加注释 — 机械
- [ ] CHK137 `AgentState` 章节显式给出 `messages` / `todos` / `files` / `context` / `scratchpad` 5 个字段的 reducer 规则 — 人工
- [ ] CHK138 每项 schema 有显式锚点 `#schema-<schema-id>`，其中 `Span / Trace` 使用 `#schema-span-trace` — 机械

## 5. 交叉引用与一致性（Cross-Reference & Consistency）

- [ ] CHK200 3 份文档之间的相对路径引用均使用 `architecture_modules.md` / `module_schemas.md` / `workflow.md`（不带 `./` 前缀、不带 `../`） — 机械
- [ ] CHK201 3 份文档之间的锚点严格符合 FR-041 命名空间 — 机械
- [ ] CHK202 3 份文档中所有相对路径 + 锚点引用均可被目标文档中对应锚点解析（无死链） — 机械（构造脚本扫描所有 `](...md#...)` 引用并核验）
- [ ] CHK203 3 份文档对"阶段名 / 退出码 / 日志标签 / 字段名"4 类同名概念字面量完全一致 — 机械（构造字符串表交叉比对）
- [ ] CHK204 3 份文档不出现绝对路径 `/Users/...` / `/home/<user>/...` / `C:\...` — 机械（`grep -E`）
- [ ] CHK205 3 份文档不出现内网 IP `192.168.x.x` / `10.x.x.x` / `172.(1[6-9]|2[0-9]|3[01]).x.x` — 机械（`grep -E`）
- [ ] CHK206 3 份文档不出现硬编码密钥 `sk-<...>` / `LANGSMITH_API_KEY=` / `OPENAI_API_KEY=sk-` 等 — 机械（`grep -E`）
- [ ] CHK207 3 份文档不出现 `TODO` / `TBD` / `FIXME` / `XXX` / `留待决定` / `待定` / `占位` — 机械（`grep -wE`）

## 6. 与宪法一致性（Constitution Consistency — 第 I-XIV 条）

- [ ] CHK300 第 I 条（项目身份与边界）：3 份文档不发布 SDK、不暴露 importable API、不破坏"开箱即用产品"定位 — 人工
- [ ] CHK301 第 II 条（技术栈与依赖范围）：3 份文档以 LangChain + LangGraph 为原语、不依赖 MDA 代码 — 人工
- [ ] CHK302 第 III 条（LangSmith 剥离）：3 份文档不出现 LangSmith import / API / 环境变量 / 镜像名 — 机械+人工
- [ ] CHK303 第 IV 条（模型抽象层）：3 份文档不硬编码 provider；本地 OpenAI Compatible 与联网模型同等优先级 — 人工
- [ ] CHK304 第 V 条（智能体目录契约）：3 份文档以宪法第 V 条的目录布局为底层约束，module_schemas.md 中 SkillSpec / ToolSpec / MiddlewareSpec 等与目录文件一一对应 — 人工
- [ ] CHK305 第 VI 条（Agent Loop 与 State）：workflow.md 6 阶段与 State schema 中的 AgentState reducer 规则一致；AgentState 字段含 `messages` / `todos` / `files` / `context` / `scratchpad` — 人工
- [ ] CHK306 第 VII 条（Middleware 与工具规则）：ToolSpec / MiddlewareSpec 字段与宪法第 VII 条的工具副作用标注、middleware 接入方式对齐 — 人工
- [ ] CHK307 第 VIII 条（TDD）：本 Feature 自身不写测试，3 份文档亦不包含测试用例（无 `def test_` / `assert`） — 机械
- [ ] CHK308 第 IX 条（质量诊断能力矩阵）：module_schemas.md 中的 Span / Trace / MetricsSnapshot / AuditEntry / EvalReport / DoctorReport 与第 IX 条 5 项子能力（Tracing / Monitoring / Evaluation / Testing / Guardrails）一一对应 — 人工
- [ ] CHK309 第 X 条（安全与隐私）：3 份文档不出现硬编码密钥、内网 IP、绝对路径 — 机械
- [ ] CHK310 第 XI 条（打包与分发）：workflow.md 中 CLI 生命周期含 `init` / `run` / `eval` / `doctor` 4 个子命令 — 机械
- [ ] CHK311 第 XII 条（配置与可观测契约）：RuntimeConfig schema 体现"CLI > 环境变量 > .env > 内置默认"优先级；Span / Trace schema 字段含 `trace_id` / `span_id` / `parent_span_id` / `name` / `start` / `end` / `attributes` — 人工
- [ ] CHK312 第 XIII 条（禁止项）：3 份文档不依赖 LangSmith 闭源、不在示例中硬编码 API key / 模型名 / 路径、不混入外部网络地址 — 机械+人工
- [ ] CHK313 第 XIV 条（宪法修订程序）：本 Feature 期间不修改宪法；如触及宪法条款边界，3 份文档必须以 `与宪法第 N 条关系：...` 显式标注 — 人工

## 7. 范围零代码（Zero-Code Scope — 本 Feature 不实施任何代码）

- [ ] CHK400 Feature 00 完成后仓库内不存在 `langagent/` Python 包目录 — 机械（`find . -type d -name langagent`）
- [ ] CHK401 Feature 00 完成后仓库内不存在 `tests/` 目录 — 机械（`find . -type d -name tests -not -path '*/.specify/*' -not -path '*/.git/*'`）
- [ ] CHK402 Feature 00 完成后仓库内不存在 `pyproject.toml` / `Pipfile` / `poetry.lock` / `requirements.txt` — 机械
- [ ] CHK403 Feature 00 完成后仓库内不存在 `Feature 01`..`Feature 10+` 的 spec 文件（即 `specs/*-top-level-design` 之外的 spec 目录） — 机械
- [ ] CHK404 Feature 00 完成后仓库内不存在 `src/` / `lib/` / `app/` 等任何 LangAgent 业务源码目录 — 机械
- [ ] CHK405 Feature 00 完成后仓库内不存在任何 `.py` 源文件（基础设施脚本如 `.specify/scripts/bash/*.sh` 除外） — 机械

## 8. 命名表（用于 SC-003 一致性核验的"事实来源"）

> 实施阶段 3 份文档须以下表为字面量基准，任一漂移即不通过。

| 概念 | 字面量 | 出现位置 | 类型 |
| --- | --- | --- | --- |
| 阶段 1 | `dir_load` | workflow.md / architecture_modules.md / module_schemas.md | 英文蛇形 |
| 阶段 2 | `config_resolve` | workflow.md / architecture_modules.md / module_schemas.md | 英文蛇形 |
| 阶段 3 | `model_adapt` | workflow.md / architecture_modules.md / module_schemas.md | 英文蛇形 |
| 阶段 4 | `graph_compose` | workflow.md / architecture_modules.md / module_schemas.md | 英文蛇形 |
| 阶段 5 | `main_loop` | workflow.md / architecture_modules.md / module_schemas.md | 英文蛇形 |
| 阶段 6 | `exit_cleanup` | workflow.md / architecture_modules.md / module_schemas.md | 英文蛇形 |
| 层 1 | `cli` | architecture_modules.md | 英文蛇形 |
| 层 2 | `runtime` | architecture_modules.md | 英文蛇形 |
| 层 3 | `protocol` | architecture_modules.md | 英文蛇形 |
| 层 4 | `cross_cutting` | architecture_modules.md | 英文蛇形 |
| 层 5 | `primitives` | architecture_modules.md | 英文蛇形 |
| 日志标签前缀 | `la.` | workflow.md / module_schemas.md | 英文点分 |
| 退出码集合 | `{0, 1, 2, 3, 4, 5, 64, 65, 66, 70, 78, 130}` | workflow.md | 阿拉伯数字 |
| schema_version 正则 | `^v\d+\.\d+\.\d+$` | module_schemas.md | 语义版本字符串 |
| 磁盘格式候选 | `JSON` / `JSONL` / `YAML` / `TOML` / `MessagePack` / `Parquet` | module_schemas.md | 英文 |
| Python 类型签名候选 | `TypedDict` / `Pydantic BaseModel` / `dataclass(frozen=True)` | module_schemas.md | 英文 |

## 9. 校验脚本（机械部分）参考实现路径

> 本节列出实施阶段机械校验脚本应放置的位置（仅作为提示，不在本 Feature 范围内实施）。

- 文档存在性与行数：`harness/top_level_design/scripts/check_existence.sh` — 不在本 Feature 范围。
- 死链扫描：`harness/top_level_design/scripts/check_dead_links.sh` — 不在本 Feature 范围。
- 占位词 / 硬编码 / 内网 IP：`harness/top_level_design/scripts/check_secrets_and_placeholders.sh` — 不在本 Feature 范围。
- 与宪法一致性：人工 review（无脚本）。

---

## Notes

- 本校验清单的两段生命周期：
  - **段 1（spec.md 自身）**：CHK001..CHK022 由 `/speckit.specify` 命令自身在落盘 `spec.md` 时即已勾选（即 `[x]`），代表本规范作为"规范自身"已经过审阅。
  - **段 2（3 份实施产物）**：CHK100..CHK405 由项目维护者在 Feature 00 实施完成后人工 review 时勾选；实施者使用本清单逐条核验。
- 段 2 中所有"机械"项在实施者交付时必须跑过对应脚本并附上脚本输出；"人工"项必须由项目维护者本人签字确认。
- 任何未勾选项即代表未通过校验；未通过校验前不得进入 Feature 01-10+。
- 命名表（第 8 节）是 SC-003 的事实来源；如未来阶段名 / 层名 / 退出码 / 日志标签前缀等发生变更，须先修订本清单第 8 节与 `spec.md` 的 FR-011..FR-016 / FR-021 / FR-041。
