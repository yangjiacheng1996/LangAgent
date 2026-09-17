# Tasks: Feature 00 — 顶层设计（Top-Level Design）

**Input**: Design documents from `/specs/000-top-level-design/`
- spec.md (required, 260 行；含 12 条 Clarifications Q1–Q12 + 8 项局部精修 + 4 项 /speckit.specify 重入缺陷修补 + Q10 /speckit.specify 追加澄清 + Q11 + Q12 /speckit.specify 2026-09-15 重入追加 + 4 处 spec 缺陷修补 2026-09-15（FR-043 占位词清单扩 `...此处略` + 新增 (a) 扩展占位子条款 / E-2 新增 v0.1.0 处理澄清 / E-5 硬编码模式清单对齐 SC-004 + 删除误写 `/ SC-005`）+ **第 4 次重入 2026-09-15** Out of Scope 小节 `O-1..O-12` 前缀统一为 `OOS-1..OOS-12` 对齐 plan.md / tasks.md 既有用法 + OOS-3 行内追加宪法第 VIII 条锚定句消除宪法对齐候选)
- plan.md (required, 332 行；含 §Spec 同步说明 12 条 Clarifications 映射表 + 8 项局部精修 + 4 项 /speckit.specify 重入缺陷溯源 + /speckit.plan 重入 6 处修订记录（2026-09-14）+ 1 处 /speckit.plan 重入修订（2026-09-15，新增 §本轮 /speckit.plan 重入修复（2026-09-15）+ §MC-2.6 扩展接口约定 1 处下游 contracts 修订）+ **1 处 /speckit.plan 重入修订（2026-09-15 第 2 次，新增 §本轮 /speckit.plan 重入修复（2026-09-15, 第 2 次）节，L67 Constitution Check 第 VIII 条评注引用 spec.md OOS-3 锚定句指针 + L132 spec 修补清单由 4 项扩为 6 项）**)
- research.md (required, 207 行)
- data-model.md (required, 855 行)
- contracts/workflow.md.contract.md (required)
- contracts/architecture_modules.md.contract.md (required)
- contracts/module_schemas.md.contract.md (required)
- quickstart.md (required, 255 行)
- checklists/requirements.md (required, 160 行；含 T000 完成的 4 处修订)

**Prerequisites**: plan.md（required）、spec.md（required for user stories）、research.md / data-model.md / contracts/ / quickstart.md（all required for this Feature 00）

**Tests**: 不写 pytest 测试用例（spec OOS-3 + 宪法第 VIII 条 TDD 约束待 Feature 01-10+ 涉及运行时代码时触发）；本文档的"验证"由 `quickstart.md` §QS-1 的 8 段机械核验脚本 + §QS-2 的 4 段人工 review 清单承担，详见 Phase 6。

**Organization**: Tasks 按 3 个 P1 User Story 拆分（每份文档 = 1 个 User Story），使每份文档可独立落盘与独立 review。

## Spec 演化说明（2026-09-14 8 项局部精修）

> 本任务列表在 12 轮 clarify + 8 项局部精修 + 4 项 /speckit.specify 重入缺陷修补 + 4 处 spec 缺陷修补（2026-09-15）后形成，主体设计（Q1–Q12）不动。下表列出 8 项精修与 tasks.md 的对应关系，供 review 时溯源。

| # | 精修摘要 | tasks.md 中的对应位置 | 当前状态 |
|---|---|---|---|
| 1 | US1-4 / US2-6 / US3-6 删除 `../` 前缀 | contracts WC-2.7 / AC-2.7 / MC-2.4 已规定"不带 `../`"；T015 / T028 / T052 中的 cross-ref 验证已隐含 | ✅ 已对齐 |
| 2 | FR-011 / FR-012 末尾追加『项』定义 | T009 / T010 中"每栏 ≥ 3 项"已隐含 Markdown `- ...` 列表条目语义 | ✅ 已对齐 |
| 3 | FR-014："推荐使用 R-5" → "至少 15 行（硬下限）；参考 R-5 但不作为强制目标" | **T012 措辞同步更新** | ✅ 已对齐 |
| 4 | FR-022：""职责"栏建议 ≥ 2 项" → ""职责"栏 ≥ 2 项" | T019 / T020 / T021 / T022 / T023 中 `职责 ≥ 2 项` 已无"建议"措辞 | ✅ 已对齐 |
| 5 | checklist CHK122 → "每层下挂至少 2 个模块；总模块数 ≥ 12" | T019–T023 中"每层 ≥ 2 个"已锁定此下界；T028 追加"总模块数 ≥ 12"校验（H4 修订） | ✅ 已对齐 |
| 6 | checklist CHK137 → "5 字段（含 `context`）reducer 规则" | T032 中 `messages / todos / files / context / scratchpad` 5 字段已显式列出 | ✅ 已对齐 |
| 7 | checklist CHK131 → "5 列（含 `承载类型数`）+ 合计行 `合计 — — — — 19 / 21`" | T031 中 5 列定义 + 合计行已显式列出 | ✅ 已对齐 |
| 8 | checklist CHK020（L34）→ CHK021（消除重复 ID） | **T000 状态同步**：[ ] → [x]（含 (a)(b)(c)(d) 4 处修订） | ✅ 已对齐 |

> **结论**：8 项精修全部已在 tasks.md 中闭环；T000 提前完成（含 4 处修订），T012 措辞已与 FR-014 精修后对齐；T028 已追加"总模块数 ≥ 12"校验（H4 修订）；其余 56 个任务（T001–T056）所引用的 spec 字面量在 8 项精修前后保持一致，无需修改。

## Spec 演化说明（2026-09-14 /speckit.specify 重入后续修订）

> 本节为 8 项精修之后的"第二轮 spec 修订"溯源。经 `/speckit.analyze` 重入发现 4 处缺陷，由后续 `/speckit.specify` 重入命令统一修订；本表列出每项缺陷在 tasks.md 中的对应位置。

| # | 缺陷摘要 | tasks.md 中的对应位置 | 当前状态 |
|---|---|---|---|
| **缺陷 1 (CRITICAL)** | spec.md FR-031 / FR-032 / Q2 Clarification / US3 acceptance / Key Entities 共 6 处 `21 个类型` / `19 / 21` → `22 个类型` / `19 / 22`；同步传播至 `data-model.md` DM-1 / `contracts/module_schemas.md.contract.md` MC-2.2 / `checklists/requirements.md` CHK131 | **T006**（"19 个一级章节 / 21 个类型" → "19 个一级章节 / 22 个类型"，L86 已修订）；**US3 Goal**（"19 个一级章节（承载 21 个类型）" → "（承载 22 个类型）"，L147 已修订）；**T031**（"合计行 `19 / 21`" → "`19 / 22`"，L155 已修订） | ✅ 已对齐 |
| **缺陷 2 (HIGH)** | spec.md FR-040 末尾追加"跨目录相对路径"规则段；为使自检 grep `'跨目录'` 命中 1 行，处方文本"拼接跨级目录"微调为"拼接跨目录"（删 1 字"级"） | **T008 / T017 / T030** 的 `constitution_ref: ../../.specify/memory/constitution.md` 字面量已对齐 FR-040 修订后的 `../` 规则；tasks.md 本体未触及 FR-040，无需修改 | ✅ 已对齐 |
| **缺陷 3 (HIGH)** | `checklists/requirements.md` L35/L36 CHK ID 重编号 CHK021 → CHK022 / CHK022 → CHK023（消除 L34/L35 重复 CHK021）；原"8 项精修 #8"尝试未完全消除 | **T000 (e) 新增子项**（见下方 T000 修订记录） | ✅ 已对齐 |
| **缺陷 4 (后续修补)** | spec.md FR-033 "19 个非合并章节" → "16 个非合并章节"（与 FR-032 列表 / FR-041 锚点命名空间 / Key Entities 字面对齐） | **T032 / T035 / T045** 中"4 个二级小节 / 6 个二级小节"组织结构不变；FR-033 的字数仅是"非合并章节"计数描述调整（19 → 16），不改变任务结构 | ✅ 已对齐 |

> **本表传播结论**：缺陷 1 触发 3 处下游任务字面量同步（T006 / US3 Goal / T031），全部已修订为 `22` / `19 / 22`；缺陷 2 仅影响 FR-040 文本，不改变 tasks.md 任何任务结构；缺陷 3 触发 T000 子项 (e) 新增；缺陷 4 仅描述计数，不改变任务结构。tasks.md T001–T056 全部任务定义与修订后 spec 完全对齐，可直接执行。


## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files / 不同文档小节, no dependencies on incomplete tasks)
- **[Story]**: 任务所属 User Story（US1 / US2 / US3；Setup / Foundational / Polish 阶段不带 Story 标签）
- Description 应含确切文件路径 / 命令 / 验证点（按需引用 `harness/top_level_design/...`）

## Path Conventions

- 本 Feature 不写源代码；唯一落盘目录为 `harness/top_level_design/`。
- 3 份设计文档：`<doc>.md`（全小写 + 下划线 + `md` 后缀）。
- spec 自身文件位于 `specs/000-top-level-design/`。

---

## 预修正 checklist（先于 Phase 1；已于 2026-09-14 完成）

**Purpose**: 在 Phase 1 开始前，先修订 `checklists/requirements.md` 中与 spec.md 不一致之处，确保后续 T015 / T028 / T052 / T053 / T054 / T055 验证步骤的判定基准与 spec FR / Clarifications 字面对齐。**T000 未完成前不得开始 T002**（因 T002 的"目录清理"动作需以 spec FR-001 / SC-008 为依据，而 checklist 与 spec 不一致会误导后续 review）。

- [x] T000 修订 `specs/000-top-level-design/checklists/requirements.md` 中与 spec.md 不一致之处（**已于 2026-09-14 完成，作为 8 项局部精修的第 5/6/7/8 项 + 后续 /speckit.specify 重入缺陷 3 一并落地**，覆盖 T000 原列 2 项 + 3 项额外修订）：
  - (a) CHK122（行 64）原文"每层下挂至少 1 个模块" → 已改为"每层下挂至少 2 个模块；总模块数 ≥ 12"（与 spec FR-022 字面对齐；FR-022 明示"每层下挂至少 2 个模块；总模块数 ≥ 12"）✓
  - (b) CHK137（行 79）原文"显式给出 `messages` / `todos` / `files` / `scratchpad` 4 个字段的 reducer 规则" → 已改为"显式给出 `messages` / `todos` / `files` / `context` / `scratchpad` 5 个字段的 reducer 规则"（与 spec FR-037 + Clarifications Q1 字面对齐；FR-037 明示 5 个字段均有 reducer 约束）✓
  - (c) **额外修订** CHK131（行 73）已增加 `承载类型数` 第 5 列与表末合计行 `合计 — — — — 19 / 22`（与 spec FR-031 字面对齐——FR-031 现行值为 `19 / 22`，原 `19 / 21` 系 8 项精修时字面漂移，已由 /speckit.specify 缺陷 1 修正）✓
  - (d) **额外修订** CHK ID 重编号（消除 L34/L35 重复 CHK021；原"8 项精修 #8" T000(d) 仅做不完整尝试）：L34 保持 `CHK021`（Independent Test）；L35 原重复 `CHK021`（Key Entities 至少包含）→ `CHK022`；L36 原 `CHK022`（3 段说明完整）→ `CHK023`。**当前 checklist 段 1（spec.md 自身）最大 CHK ID = CHK023（3 字段组织 + 2 字段重复结构已展开为 4 个：CHK020 / CHK021 / CHK022 / CHK023）** ✓
  - 自检命令已全部通过：`grep -nE '每层下挂|reducer 规则|承载类型数' specs/000-top-level-design/checklists/requirements.md` 输出 4 处修订；`awk '/^- \[x\] CHK[0-9]+/{print $3}' specs/000-top-level-design/checklists/requirements.md | sort | uniq -d` 输出为空（CHK ID 全部唯一）；段 1 各 CHK ID 当前计数：CHK020=1（L33）/ CHK021=1（L34）/ CHK022=1（L35）/ CHK023=1（L36）。**T002 的目录清理前置条件已满足。**

**Checkpoint**: T000 完成——4 处 checklist 不一致已修订并通过 grep 自检；后续 T002 / T015 / T028 / T052 / T053 / T054 / T055 全部以修订后的 checklist 为判定基准。

---

### Phase 1: Setup（共享基础设施）

**Purpose**: 准备落盘目录与读取所有设计依据。

- [ ] T001 读取所有设计依据文件，按以下顺序在 memory 中建立"事实参考表"：先读 `specs/000-top-level-design/plan.md`（理解 Summary / Technical Context / Phase 0-1 引用），再读 `specs/000-top-level-design/spec.md`（理解 12 条 Clarifications Q1–Q12 + FR-001..FR-061），再读 `specs/000-top-level-design/research.md`（理解 R-1..R-7 决策），再读 `specs/000-top-level-design/data-model.md`（理解 19 个 schema 字段级定义），最后读 `specs/000-top-level-design/contracts/{workflow,architecture_modules,module_schemas}.md.contract.md`（理解 3 份文档的格式合同；特别注意 `contracts/module_schemas.md.contract.md` §MC-2.6 扩展接口约定——FR-043 (a) 路径 1 落盘形式契约）；**不创建任何文件**，仅在 memory 中建立引用关系
- [ ] T002 验证落盘目录可写且为空：执行 `ls harness/top_level_design/` 确认输出为空或仅含隐藏文件（`.gitkeep` 允许）；若目录不存在，执行 `mkdir -p harness/top_level_design/`；若目录存在但含非空文件，按 `spec.md` FR-001 / SC-008 约束必须先清理——`rm -f harness/top_level_design/*.md` 移除残留（**注意**：本任务不删除 `harness/top_level_design/` 本身，只删除其下的 `.md` 文件）
- [ ] T003 建立"命名约定速查表"（仅在 memory 中，不写文件）：从 `spec.md` Clarifications Q3 抽取章节标题 PascalCase / ID 蛇形 / 锚点短横线约定；从 `spec.md` FR-021 抽取 5 层名；从 `spec.md` FR-012 抽取 6 阶段名；从 `spec.md` FR-013 抽取 12 退出码；从 `spec.md` FR-016 / FR-041 抽取锚点命名空间；从 `spec.md` Clarifications Q6 抽取阶段锚点显式 `## <title> {#stage-<id>}` 形式

**Checkpoint**: Setup 完成——已建立 3 份设计文档的全部事实参考表，目录可写，命名约定已就绪。

---

### Phase 2: Foundational（阻塞前置条件）

**Purpose**: 抽取跨 3 份文档共享的"基础数据表"，作为 US1/US2/US3 的输入。

**⚠️ CRITICAL**: 任何 User Story 任务都必须等本阶段完成。

- [ ] T004 [P] 构建"6 阶段名 + 12 退出码 + 25 日志标签"基础表：参考 `research.md` R-3（退出码溯源）+ R-5（日志标签初始 25 项），在 memory 中建立 3 张字面量表（`STAGES = ['dir_load', 'config_resolve', 'model_adapt', 'graph_compose', 'main_loop', 'exit_cleanup']` / `EXIT_CODES = [0,1,2,3,4,5,64,65,66,70,78,130]` / `LOG_TAGS = [25 项 from R-5]}`），后续 US1 / US2 / US3 任务必须严格使用这 3 张表的字面量
- [ ] T005 [P] 构建"12 个 module_id 初始候选"基础表：参考 `research.md` R-1.3（每层 ≥ 2 个，总模块数 ≥ 12），在 memory 中建立 1 张表（`MODULES = [('cli', ['cli_runner', 'cli_parser']), ('runtime', ['runtime_dir_loader', 'runtime_config_resolver', 'runtime_main_loop_dispatcher', 'runtime_exit_handler']), ('protocol', ['protocol_event_bus', 'protocol_skill_loader', 'protocol_tool_registry']), ('cross_cutting', ['cross_cutting_logger', 'cross_cutting_metrics_collector', 'cross_cutting_audit_recorder', 'cross_cutting_guardrail_middleware']), ('primitives', ['primitives_chat_model_factory', 'primitives_state_graph_builder', 'primitives_checkpoint_adapter'])]}`），US2 任务可自由调整 module_id 字面量但必须保证（1）每层 ≥ 2 个；（2）总模块数 ≥ 12；（3）全局唯一
- [ ] T006 [P] 构建"19 个 schema_id + 章节标题 + 锚点"基础表：参考 `data-model.md` DM-1（19 个一级章节 / 22 个类型），在 memory 中建立 1 张表（`SCHEMAS = [('agent_state', 'AgentState', '#schema-agent-state', 1), ('runtime_config', 'RuntimeConfig', '#schema-runtime-config', 1), ... 19 行]}`），其中 3 个合并章节的锚点为 `#schema-skill-spec-frontmatter` / `#schema-tool-spec-side-effect` / `#schema-span-trace`；US3 任务必须严格使用这 19 行的字面量

**Checkpoint**: Foundation ready——4 张基础表（命名约定 / 阶段退出码日志标签 / module_id / schema_id）已就绪，3 个 User Story 可并行开始。

---

### Phase 3: User Story 1 — workflow.md 工作流文档 (Priority: P1) 🎯 MVP

**Goal**: 在 `harness/top_level_design/workflow.md` 落盘一份 ≥ 200 行的 Markdown 设计文档，覆盖 4 CLI 子命令 + 6 阶段 + 12 退出码 + ≥ 15 日志标签 + ≥ 10 行 MDA 能力对照表，作为后续 Feature 01-10+ 拆分"切到哪个阶段"的事实来源。

**Independent Test**: 跑 `quickstart.md` §QS-1.1..§QS-1.5 中的 workflow.md 相关核验（行数 ≥ 200、字符编码 UTF-8/LF、占位词 / 硬编码 / 内网 IP / 密钥扫描、6 阶段锚点 / 12 退出码锚点 / N 日志标签锚点存在）；跑 §QS-2.1 人工 review 清单（10 项勾选）。

### Implementation for User Story 1

- [ ] T007 [US1] 创建 `harness/top_level_design/workflow.md` 空文件：`touch harness/top_level_design/workflow.md`；确认 `wc -l` 输出 0 行
- [ ] T008 [P] [US1] 写 workflow.md 文档元信息 + 顶部 title 段落：参考 `contracts/workflow.md.contract.md` §WC-2.1，5 字段（`doc_id: workflow` / `version: v0.1.0` / `last_updated: 2026-09-14` / `constitution_ref: ../../.specify/memory/constitution.md` / `related_docs: [architecture_modules.md, module_schemas.md]`），用 `---` 围栏的 YAML 头
- [ ] T009 [P] [US1] 写 workflow.md "用户视角：CLI 生命周期" 一级章节 + 4 个二级子命令：参考 `contracts/workflow.md.contract.md` §WC-2.2；4 个子命令为 `langagent init <name>` / `langagent run [agent-dir]` / `langagent eval [agent-dir]` / `langagent doctor`；每个子命令下挂 5 栏（`输入` / `输出` / `失败模式` / `退出码` / `日志标签`），每栏 ≥ 3 项（research R-4 下界）
- [ ] T010 [P] [US1] 写 workflow.md "系统视角：6 阶段" 一级章节 + 6 个二级阶段：参考 `contracts/workflow.md.contract.md` §WC-2.3 + spec Clarifications Q6 + plan.md "Spec 同步说明" 缺陷 2（U1）；6 个阶段为 `dir_load` / `config_resolve` / `model_adapt` / `graph_compose` / `main_loop` / `exit_cleanup`；每阶段以 `## <stage_name> {#stage-<stage_name>}` **显式锚点**形式书写（禁止依赖 Markdown 自动生成；spec FR-016 给出 `## dir_load {#stage-dir_load}` 示例，对应一级章节"系统视角：6 阶段"之下的二级章节）；每阶段下挂 5 栏，每栏 ≥ 3 项；**每个阶段的"失败模式"小节必须显式列出 `stage_capability_violation` 模式（即"阶段读取了不属于本阶段范围的配置 / 文件 / 状态"，对应 Edge Case E-1），不得遗漏；该模式即使在当前实现中不触发，也必须以 fail-safe 文档形式存在（spec FR-012 末尾强制）**
- [ ] T011 [P] [US1] 写 workflow.md 退出码表（FR-013 + spec Clarifications Q4 + spec Clarifications Q10）：参考 `contracts/workflow.md.contract.md` §WC-2.4；严格 12 行（0 / 1 / 2 / 3 / 4 / 5 / 64 / 65 / 66 / 70 / 78 / 130），列：`退出码` / `含义` / `触发阶段`；每行有显式锚点 `#exit-code-<n>`；**触发阶段列允许多阶段映射（Q10）**：多阶段时以 `/` 分隔（如 `dir_load / config_resolve`），或以"所有阶段"统称 6 个阶段；**总行数仍严格 = 12，每个退出码对应恰好 1 行**（多阶段映射不影响行数）；语义为"该退出码在所列任一阶段触发时即返回"；阶段名集合严格属于 6 阶段之一（`dir_load` / `config_resolve` / `model_adapt` / `graph_compose` / `main_loop` / `exit_cleanup`）或"所有阶段"
- [ ] T012 [P] [US1] 写 workflow.md 日志标签表（FR-014 精修后）：参考 `contracts/workflow.md.contract.md` §WC-2.5 + research R-5；至少 **15 行（硬下限，FR-014 精修后已去除"推荐"措辞）**，不得少于 15 行；research R-5 给出的 25 项初始集合**作为参考而非强制目标**，实施者可在其全部 / 子集 / 增补中自由选择，但需保证 `la.` 前缀 + 锚点命名规范；列：`日志标签` / `含义` / `触发阶段`；每行以 `la.` 前缀开头；每行有显式锚点 `#log-tag-<la.xx.yy.zz>`（点号替换为短横线）
- [ ] T013 [P] [US1] 写 workflow.md "MDA 能力对照表" 一级章节（FR-015）：参考 `contracts/workflow.md.contract.md` §WC-2.6 + research R-1.2；至少 10 行（推荐从 `harness/Managed_deep_agents/langsmith/python/` 下 19 个 managed-deep-agents-*.md 中选 10+ 项）；列：`mda_capability` / `mda_source_path` / `langagent_equivalent_stage` / `notes`；`mda_source_path` 必须为 `harness/Managed_deep_agents/langsmith/python/<file>.md` 形式相对路径
- [ ] T014 [US1] 写 workflow.md 交叉引用 + 变更日志小节：参考 `contracts/workflow.md.contract.md` §WC-2.7 + §WC-2.8；交叉引用段落列出 workflow.md 对 architecture_modules.md / module_schemas.md 的相对路径 + 锚点引用（至少 1 个 `#mod-*` 引用 + 1 个 `#schema-*` 引用）；变更日志 1 行（`2026-09-14 | v0.1.0 | Feature 00 初版 | 项目维护者`）
- [ ] T015 [US1] 运行 workflow.md 独立验证：依次执行 `quickstart.md` §QS-1.1..§QS-1.5 中所有以 workflow.md 为目标的核验命令；如发现 6 阶段锚点 / 12 退出码锚点 / 日志标签锚点缺失，回到 T010..T012 补齐；**额外核验 6 个阶段的"失败模式"栏是否均显式含 `stage_capability_violation` 模式——使用按阶段子节扫描：用 awk 以 `## <stage_id> {#stage-<id>}` 头部把 workflow.md 划成 6 个 stage 子节（每个子节从当前 `## stage_xxx` 头部到下一个 `## stage_xxx` 或文件末尾，与 T010 中 `##` 一级一致），逐 stage 在其"失败模式"小节内 `grep -c 'stage_capability_violation'` 至少 1 次命中；以"6 个 stage 各自命中 ≥ 1"为通过条件（不是文件总命中数 = 6）**；**额外核验 FR-013 退出码表的"触发阶段"列符合 Q10 多阶段映射约束——总行数 = 12（`grep -cE '^\| [0-9]+ \|' harness/top_level_design/workflow.md` 或 `grep -cE '\{#exit-code-'` = 12），每行"触发阶段"列内容仅由 6 阶段名之一或多阶段（以 `/` 分隔）或"所有阶段"组成**；不满足则回到 T010 补齐；确认 `wc -l harness/top_level_design/workflow.md` 输出 ≥ 200

**Checkpoint**: workflow.md 落盘完毕且通过 §QS-1.1..§QS-1.5 机械核验，可作为 Phase 4 / Phase 5 的 `#stage-*` / `#exit-code-*` / `#log-tag-*` 引用源。

---

### Phase 4: User Story 2 — architecture_modules.md 架构模块文档 (Priority: P1)

**Goal**: 在 `harness/top_level_design/architecture_modules.md` 落盘一份 ≥ 200 行的 Markdown 设计文档，覆盖 5 层架构 + ≥ 12 个模块（每层 ≥ 2 个）+ 完整对称依赖矩阵（4 符号）+ 模块到 Feature 拆分映射表 + ≥ 12 条静态约束 CI 校验清单，作为后续 Feature 01-10+ "我该往哪一层写 / 能不能 import" 的事实来源。

**Independent Test**: 跑 `quickstart.md` §QS-1.1..§QS-1.7 中的 architecture_modules.md 相关核验（行数 ≥ 200 / 字符编码 / 占位词 / 5 层名 / 12 个模块 / 全局唯一 / 依赖矩阵 4 符号 / 矩阵无回路）；跑 §QS-2.2 人工 review 清单（7 项勾选）。

### Implementation for User Story 2

- [ ] T016 [US2] 创建 `harness/top_level_design/architecture_modules.md` 空文件：`touch harness/top_level_design/architecture_modules.md`；确认 `wc -l` 输出 0 行
- [ ] T017 [P] [US2] 写 architecture_modules.md 文档元信息 + 顶部 title 段落：参考 `contracts/architecture_modules.md.contract.md` §AC-2.1，5 字段（`doc_id: architecture_modules` / `version: v0.1.0` / `last_updated: 2026-09-14` / `constitution_ref: ../../.specify/memory/constitution.md` / `related_docs: [workflow.md, module_schemas.md]`），用 `---` 围栏的 YAML 头
- [ ] T018 [P] [US2] 写 architecture_modules.md "5 层架构总览" 一级章节（FR-021）：参考 `contracts/architecture_modules.md.contract.md` §AC-2.2；5 层为 `cli` / `runtime` / `protocol` / `cross_cutting` / `primitives`（英文蛇形严格匹配）；每层下挂二级章节 `## <layer_name> 层`（与 spec FR-021 中"5 层架构总览"一级章节对应的二级子节，modules 是再下一级 `###`）+ 2-3 项"职责概述"
- [ ] T019 [P] [US2] 写 architecture_modules.md "模块清单" 一级章节下的 `cli` 层模块（FR-022）：参考 `contracts/architecture_modules.md.contract.md` §AC-2.3 + research R-1.3；从 Phase 2 T005 基础表的 `cli` 子集中选 ≥ 2 个 module_id；每个 module_id 一级章节下挂 4 栏（`职责` ≥ 2 项 / `关键 API` ≥ 1 项 / `允许的依赖方向` ≥ 1 项 / `禁止的依赖方向` ≥ 1 项）；每个 module_id 以 `### <module_id> {#mod-<module-id>}` 显式锚点
- [ ] T020 [P] [US2] 写 architecture_modules.md "模块清单" 一级章节下的 `runtime` 层模块：同 T019 模式，从 `runtime` 子集中选 ≥ 2 个 module_id
- [ ] T021 [P] [US2] 写 architecture_modules.md "模块清单" 一级章节下的 `protocol` 层模块：同 T019 模式，从 `protocol` 子集中选 ≥ 2 个 module_id
- [ ] T022 [P] [US2] 写 architecture_modules.md "模块清单" 一级章节下的 `cross_cutting` 层模块：同 T019 模式，从 `cross_cutting` 子集中选 ≥ 2 个 module_id
- [ ] T023 [P] [US2] 写 architecture_modules.md "模块清单" 一级章节下的 `primitives` 层模块：同 T019 模式，从 `primitives` 子集中选 ≥ 2 个 module_id
- [ ] T024 [US2] 写 architecture_modules.md "模块间依赖矩阵" 一级章节（FR-023 / spec Clarifications Q7）：参考 `contracts/architecture_modules.md.contract.md` §AC-2.4；从 T019..T023 收集所有 module_id 形成 N×N 完整对称方阵；每个单元格从 4 符号（`→` / `↔` / `×` / `–`）中选取一个；自反对角线一律为 `–`；构造有向图跑拓扑排序验证 `→` 与 `↔` 的边集合无回路
- [ ] T025 [US2] 写 architecture_modules.md "模块到 Feature 拆分映射表" 一级章节（FR-024）：参考 `contracts/architecture_modules.md.contract.md` §AC-2.5；从 T019..T023 收集所有 module_id；每行 4 列（`module_id` / `feature_id` / `职责` / `依赖的下游模块`）；`feature_id` 取值 `F01`..`F10+`，**不得出现 F00**
- [ ] T026 [US2] 写 architecture_modules.md "静态约束 CI 校验清单" 一级章节（FR-025 / research R-1.2）：参考 `contracts/architecture_modules.md.contract.md` §AC-2.6；至少 12 条；每条以 `- ID: CHK-AR-NNN | 约束描述 | 实现方式（grep / ripgrep / AST）` 形式书写；必须覆盖：3 条文档存在性 / 3 条锚点命名空间 / 2 条依赖矩阵 / 2 条 module_id 全局唯一 / 2 条宪法一致性；实现方式列不得包含"人工"二字
- [ ] T027 [US2] 写 architecture_modules.md 交叉引用 + 变更日志小节：参考 `contracts/architecture_modules.md.contract.md` §AC-2.7 + §AC-2.8；交叉引用段落列出对 workflow.md / module_schemas.md 的相对路径 + 锚点引用（至少 1 个 `#stage-*` 引用 + 1 个 `#schema-*` 引用）；变更日志 1 行（`2026-09-14 | v0.1.0 | Feature 00 初版 | 项目维护者`）
- [ ] T028 [US2] 运行 architecture_modules.md 独立验证：依次执行以下核验命令：
  - `quickstart.md` §QS-1.1..§QS-1.5 中所有以 architecture_modules.md 为目标的核验命令（行数 / 编码 / 占位词 / 锚点命名空间等）
  - `§QS-1.6` 依赖矩阵无回路（构造有向图跑拓扑排序）
  - `§QS-1.7` module_id 全局唯一性（`grep`+`sort`+`uniq -d` 实现）
  - **总模块数 ≥ 12（spec FR-022）**：`grep -cE '^### .*\{#mod-' harness/top_level_design/architecture_modules.md`（或等价的 `awk '/^### .*\{#mod-/{n++} END{print n}'` 锚点计数命令）输出值 ≥ 12；不满足则回到 T019..T023 增加模块直到 ≥ 12；注意：FR-022 的 ≥ 12 是**总数约束**，每层 ≥ 2 是 **per-layer 约束**，二者需同时满足
  如发现冲突，回到 T019..T024 调整；确认 `wc -l harness/top_level_design/architecture_modules.md` 输出 ≥ 200

**Checkpoint**: architecture_modules.md 落盘完毕且通过 §QS-1.1..§QS-1.7 机械核验（含 §QS-1.6 / §QS-1.7 / 总模块数 ≥ 12），模块 ID 命名空间稳定可作为 Phase 5 的 `#mod-*` 引用源。

---

### Phase 5: User Story 3 — module_schemas.md 模块 schema 文档 (Priority: P1)

**Goal**: 在 `harness/top_level_design/module_schemas.md` 落盘一份 ≥ 200 行的 Markdown 设计文档，覆盖 19 个一级章节（承载 22 个类型）的 Python 类型签名 + 磁盘格式 + schema_version + 与 LangChain/LangGraph 原生类型映射 + reducer 规则，作为后续 Feature 01-10+ 编写 TDD 失败用例时"我要造什么对象 / 字段是什么 / 序列化到磁盘长什么样"的事实来源。

**Independent Test**: 跑 `quickstart.md` §QS-1.1..§QS-1.5 + §QS-1.8 中的 module_schemas.md 相关核验（行数 ≥ 200 / 字符编码 / 占位词 / 19 个一级章节 / 3 个合并章节 / 16 个单类型章节 / Schema 总目录 5 列 + 合计行 / AgentState 5 字段 reducer）；跑 §QS-2.3 人工 review 清单（7 项勾选）。

### Implementation for User Story 3

- [ ] T029 [US3] 创建 `harness/top_level_design/module_schemas.md` 空文件：`touch harness/top_level_design/module_schemas.md`；确认 `wc -l` 输出 0 行
- [ ] T030 [P] [US3] 写 module_schemas.md 文档元信息 + 顶部 title 段落：参考 `contracts/module_schemas.md.contract.md` §MC-2.1，5 字段（`doc_id: module_schemas` / `version: v0.1.0` / `last_updated: 2026-09-14` / `constitution_ref: ../../.specify/memory/constitution.md` / `related_docs: [workflow.md, architecture_modules.md]`），用 `---` 围栏的 YAML 头
- [ ] T031 [P] [US3] 写 module_schemas.md "Schema 总目录" 一级章节（FR-031 修订后）：参考 `contracts/module_schemas.md.contract.md` §MC-2.2 + `data-model.md` DM-1；以 `# Schema 总目录` **一级章节**书写（与 T032..T050 的 19 个 schema 一级章节同级，最终 module_schemas.md 共 20 个 `#` 标题：1 个总目录 + 19 个 schema，与 spec FR-031 / FR-032 字面解读一致）；以 Markdown 表格列出 19 个一级章节；每行 5 列（`schema_id` / `python_kind` / `schema_version` / `disk_format` / `承载类型数`）；表末必须有合计行 `合计 — — — — 19 / 22`
- [ ] T032 [P] [US3] 写 `AgentState` 一级章节（FR-037 + spec Clarifications Q1）：参考 `data-model.md` DM-2.1；以 `# AgentState {#schema-agent-state}` 显式锚点（与 T031 同级；spec FR-031 / FR-032 字面解读）；下挂 4 个二级小节（`Python 类型签名` / `磁盘格式与 schema_version` / `与 LangChain/LangGraph 原生类型映射` / `reducer 与不可变约束`），每个以 `## <sub-section-name>` 显式书写（spec FR-033 字面"二级小节"对应 `##`）；reducer 小节显式给出 5 字段规则——**reducer 名称由实施者选定，但必须满足 spec FR-037 约束：`messages` 默认 `add_messages`；`context` 仅限 `overwrite` / `merge_with_prior`；`files` / `todos` / `scratchpad` 不得使用无脑覆盖式 reducer（推荐 keyed-merge / replace-if-newer 模式）；实施者选定的具体 reducer 名须在 module_schemas.md 中显式列出，并能与 LangGraph 现有 reducer（`add_messages` / `overwrite` 等）一一对应或为可实现的自定义 reducer**
- [ ] T033 [P] [US3] 写 `RuntimeConfig` 一级章节：参考 `data-model.md` DM-2.2；显式锚点 `# RuntimeConfig {#schema-runtime-config}`；下挂 4 个二级小节（`Python 类型签名` / `磁盘格式与 schema_version` / `与 LangChain/LangGraph 原生类型映射` / `reducer 与不可变约束`），每个以 `## <sub-section-name>` 显式书写；字段含 `cli_args` / `env_vars` / `dotenv_values` / `builtin_defaults` 4 字段优先级链 + `model: BaseChatModel` + `model_provider` / `model_name` / `model_base_url`（OpenAI Compatible 后端必填）
- [ ] T034 [P] [US3] 写 `LoadedAgent` 一级章节：参考 `data-model.md` DM-2.3；显式锚点 `# LoadedAgent {#schema-loaded-agent}`；下挂 4 个二级小节，每个以 `## <sub-section-name>` 显式书写；`compiled_graph: CompiledStateGraph`
- [ ] T035 [P] [US3] 写 `SkillSpec / SkillFrontmatter` 合并一级章节（FR-033 / spec Clarifications Q9）：参考 `data-model.md` DM-2.4；显式锚点 `# SkillSpec / SkillFrontmatter {#schema-skill-spec-frontmatter}`；下挂 **6 个二级小节**（`Python 类型签名` 共用 + `磁盘格式与 schema_version` 共用 + `SkillSpec 与 LangChain/LangGraph 原生类型映射` + `SkillSpec reducer 与不可变约束` + `SkillFrontmatter 与 LangChain/LangGraph 原生类型映射` + `SkillFrontmatter reducer 与不可变约束`），每个以 `## <sub-section-name>` 显式书写；承载 2 个类型
- [ ] T036 [P] [US3] 写 `ToolSpec / ToolSideEffect` 合并一级章节：参考 `data-model.md` DM-2.5；显式锚点 `# ToolSpec / ToolSideEffect {#schema-tool-spec-side-effect}`；下挂 6 个二级小节，每个以 `## <sub-section-name>` 显式书写；承载 2 个类型；`ToolSideEffect` 枚举 7 个值（`NONE` / `READ_FILE` / `WRITE_FILE` / `EXEC_SHELL` / `NETWORK_CALL` / `SEND_MESSAGE` / `EXTERNAL_STATE`）
- [ ] T037 [P] [US3] 写 `MiddlewareSpec` 一级章节：参考 `data-model.md` DM-2.6；显式锚点 `# MiddlewareSpec {#schema-middleware-spec}`；下挂 4 个二级小节，每个以 `## <sub-section-name>` 显式书写；`hook_points` 6 个值（`before_model` / `after_model` / `before_tools` / `after_tools` / `before_agent` / `after_agent`）
- [ ] T038 [P] [US3] 写 `ChannelSpec` 一级章节：参考 `data-model.md` DM-2.7；显式锚点 `# ChannelSpec {#schema-channel-spec}`；下挂 4 个二级小节，每个以 `## <sub-section-name>` 显式书写；`enabled: bool = False`（v1 占位）
- [ ] T039 [P] [US3] 写 `ChannelContext` 一级章节：参考 `data-model.md` DM-2.8；显式锚点 `# ChannelContext {#schema-channel-context}`；下挂 4 个二级小节，每个以 `## <sub-section-name>` 显式书写；reducer 嵌入 `AgentState.context` 受其约束
- [ ] T040 [P] [US3] 写 `SandboxSpec` 一级章节：参考 `data-model.md` DM-2.9；显式锚点 `# SandboxSpec {#schema-sandbox-spec}`；下挂 4 个二级小节，每个以 `## <sub-section-name>` 显式书写；`enabled: bool = False`（v1 占位）
- [ ] T041 [P] [US3] 写 `ScheduleSpec` 一级章节：参考 `data-model.md` DM-2.10；显式锚点 `# ScheduleSpec {#schema-schedule-spec}`；下挂 4 个二级小节，每个以 `## <sub-section-name>` 显式书写；`enabled: bool = False`（v1 占位）
- [ ] T042 [P] [US3] 写 `MemorySpec` 一级章节：参考 `data-model.md` DM-2.11；显式锚点 `# MemorySpec {#schema-memory-spec}`；下挂 4 个二级小节，每个以 `## <sub-section-name>` 显式书写；`enabled: bool = False`（v1 占位）
- [ ] T043 [P] [US3] 写 `IdentitySpec` 一级章节：参考 `data-model.md` DM-2.12；显式锚点 `# IdentitySpec {#schema-identity-spec}`；下挂 4 个二级小节，每个以 `## <sub-section-name>` 显式书写
- [ ] T044 [P] [US3] 写 `EvalTaskSpec` 一级章节：参考 `data-model.md` DM-2.13；显式锚点 `# EvalTaskSpec {#schema-eval-task-spec}`；下挂 4 个二级小节，每个以 `## <sub-section-name>` 显式书写；`grader` 5 个候选值（`exact_match` / `contains` / `regex` / `llm_judge` / `tool_call_match`）；**⚠️ 警示（FR-043 + FR-043 (a) / Q11）**：实施者不得在 module_schemas.md 的 EvalTaskSpec 章节中保留 `...` / `<其它枚举>` / `etc.` 之类占位符（FR-043 + FR-043 (a) / SC-005）；如需表达"未来扩展"必须从以下两条路径中二选一——**路径 1（推荐，参考 `contracts/module_schemas.md.contract.md` §MC-2.6）**：在该章节末尾追加 `#### 扩展接口约定` 二级小节 + `grader_extensibility: list[str] = []` 字段（明示"未来新增 grader 取值应登记到该字段"，禁止用 `...` 占位）；**路径 2（fallback）**：直接以 `Literal[...]` 枚举所有 5 个当前取值（严格列 `exact_match` / `contains` / `regex` / `llm_judge` / `tool_call_match`，不预留扩展字段），如需新增则升 schema_version 触发 E-2 migrators 规则
- [ ] T045 [P] [US3] 写 `Span / Trace` 合并一级章节（FR-033 / Q9）：参考 `data-model.md` DM-2.14；显式锚点 `# Span / Trace {#schema-span-trace}`；下挂 6 个二级小节，每个以 `## <sub-section-name>` 显式书写；承载 2 个类型；`Span` 字段含 `trace_id` / `span_id` / `parent_span_id` / `name` / `start` / `end` / `attributes` 7 字段（宪法第 XII 条 3 款）
- [ ] T046 [P] [US3] 写 `Event` 一级章节（Event 总线）：参考 `data-model.md` DM-2.15；显式锚点 `# Event {#schema-event}`；下挂 4 个二级小节，每个以 `## <sub-section-name>` 显式书写；一级章节标题用 `Event` 但正文标题可写为"Event 总线"
- [ ] T047 [P] [US3] 写 `MetricsSnapshot` 一级章节：参考 `data-model.md` DM-2.16；显式锚点 `# MetricsSnapshot {#schema-metrics-snapshot}`；下挂 4 个二级小节，每个以 `## <sub-section-name>` 显式书写；`token_usage` 引用 `AIMessage.usage_metadata`
- [ ] T048 [P] [US3] 写 `AuditEntry` 一级章节：参考 `data-model.md` DM-2.17；显式锚点 `# AuditEntry {#schema-audit-entry}`；下挂 4 个二级小节，每个以 `## <sub-section-name>` 显式书写；`category` 含 3 个当前安全事件类别（与 `data-model.md` DM-2.17 字面对齐：`pii_leak` / `unauthorized_tool` / `prompt_injection`，共 3 项枚举字面量）——**⚠️ 警示（FR-043 + FR-043 (a) / Q11，**与 T044 同源）：实施者不得在 module_schemas.md 的 AuditEntry 章节中保留 `...` / `<其它枚举>` / `etc.` 之类占位符；如需表达"未来扩展"必须从以下两条路径中二选一——**路径 1（推荐，参考 `contracts/module_schemas.md.contract.md` §MC-2.6）**：在该章节末尾追加 `#### 扩展接口约定` 二级小节 + `category_extensibility: list[str] = []` 字段（明示"未来新增 category 取值应登记到该字段"，禁止用 `...` 占位）；**路径 2（fallback）**：直接以 `Literal[...]` 枚举所有 3 个当前取值（严格列 `pii_leak` / `unauthorized_tool` / `prompt_injection`，不预留扩展字段），如需新增则升 schema_version 触发 E-2 migrators 规则。**注意**：原 T048 描述中曾以 `Literal["pii_leak", "unauthorized_tool", "prompt_injection", "<其它枚举>"]` 作为示例——该示例本身违反 FR-043 (a)（`<其它枚举>` 即 FR-043 (a) 明示禁止的占位符之一），已在 2026-09-15 /speckit.tasks 重入时统一修订；本任务后续严格遵循上述两条路径之一。
- [ ] T049 [P] [US3] 写 `DoctorReport` 一级章节：参考 `data-model.md` DM-2.18；显式锚点 `# DoctorReport {#schema-doctor-report}`；下挂 4 个二级小节，每个以 `## <sub-section-name>` 显式书写；嵌套 `RuntimeConfig`
- [ ] T050 [P] [US3] 写 `EvalReport` 一级章节：参考 `data-model.md` DM-2.19；显式锚点 `# EvalReport {#schema-eval-report}`；下挂 4 个二级小节，每个以 `## <sub-section-name>` 显式书写；`token_usage` 引用 `AIMessage.usage_metadata`
- [ ] T051 [US3] 写 module_schemas.md 交叉引用 + 变更日志小节：参考 `contracts/module_schemas.md.contract.md` §MC-2.4 + §MC-2.5；交叉引用段落列出对 workflow.md / architecture_modules.md 的相对路径 + 锚点引用（至少 1 个 `#stage-*` 引用 + 1 个 `#mod-*` 引用）；变更日志 1 行（`2026-09-14 | v0.1.0 | Feature 00 初版 | 项目维护者`）
- [ ] T052 [US3] 运行 module_schemas.md 独立验证：依次执行 `quickstart.md` §QS-1.1..§QS-1.5 + §QS-1.8 中所有以 module_schemas.md 为目标的核验命令（特别注意 §QS-1.8 schema 数量检查 + 合并章节 6 二级小节结构；§QS-1.8 中关于"20 个 `#` 标题（1 个总目录 + 19 个 schema）"的断言需以本文件中 `grep -cE '^# .*\{#schema-' module_schemas.md` ≥ 19 + 顶部"# Schema 总目录"标题字面命中来共同验证）；如发现 19 章节缺失或合并章节结构错误，回到 T031..T051 补齐；确认 `wc -l` 输出 ≥ 200

**Checkpoint**: module_schemas.md 落盘完毕且通过 §QS-1.1..§QS-1.5 + §QS-1.8 机械核验，3 份设计文档全部独立可 review。

---

### Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 跨 3 份文档的全局核验、人工 review、checklist 状态同步。

- [ ] T053 跑 `quickstart.md` §QS-1 全部 8 段机械核验脚本：依次执行 QS-1.1（存在性 + 行数）/ QS-1.2（编码 + 行尾）/ QS-1.3（占位词 / 绝对路径 / 内网 IP / 硬编码密钥）/ QS-1.4（锚点命名空间扫描）/ QS-1.5（死链扫描）/ QS-1.6（依赖矩阵无回路）/ QS-1.7（module_id 全局唯一）/ QS-1.8（schema 数量）；将每段输出保存到 `harness/top_level_design/scripts/verification.log`（如该 scripts 目录不存在则 `mkdir -p`）；如任何一段失败，定位失败任务并修复后重跑
- [ ] T054 项目维护者按 `quickstart.md` §QS-2 跑 4 段人工 review：QS-2.1（workflow.md 6 项）/ QS-2.2（architecture_modules.md 7 项）/ QS-2.3（module_schemas.md 7 项）/ QS-2.4（3 份文档间一致性 5 项）；每勾选一项即在 `specs/000-top-level-design/checklists/requirements.md` 对应 `CHK1xx..CHK4xx` 行的 `[ ]` 改为 `[x]`；如 review 发现问题，回到 Phase 3/4/5 对应任务修复
- [ ] T055 同步 `specs/000-top-level-design/checklists/requirements.md` 段 2 状态：项目维护者审阅后，把"已通过机械 + 人工 review"的所有段 2 CHK 条目（CHK1xx..CHK4xx，共 56 项）从 `[ ]` 改为 `[x]`；保留段 1（spec.md 自身 CHK0xx 共 17 项）的 `[x]` 状态不变；最终用 `grep -c '^- \[x\]' specs/000-top-level-design/checklists/requirements.md` 统计已勾选数 X；用 `grep -c '^- \[' specs/000-top-level-design/checklists/requirements.md` 统计总条目数 Y；预期 X = Y（即 17 个段 1 + 56 个段 2 = 73），二者差值应为 0；实际数字以 `requirements.md` 修订后为准
- [ ] T056 提交：执行 `git add harness/top_level_design/ specs/000-top-level-design/checklists/requirements.md` + `git commit -m "feat(F00): 落盘顶层设计 3 份文档 + 完成 checklist 核验"`（**不**自动 push；按宪法第 VIII 条 6 款，主分支不得直推，须由项目维护者本人 push）；commit message 须包含 Feature 编号 `F00`

**Checkpoint**: Feature 00 全部完成——3 份设计文档落盘、checklist 同步、commit 落地。可进入 Feature 01-10+ 的 spec 阶段。

---

## Dependencies & Execution Order

### 阶段依赖关系（Phase Dependencies）

- **Setup (Phase 1)**: No dependencies — T001..T003 立即可开始；但 T002 须在 T000 完成之后开始（T000 修订 checklist，T002 的目录清理决策依赖与 spec 一致的 checklist，否则 FR-001 / SC-008 判定会出现双标）。
- **Foundational (Phase 2)**: Depends on Setup completion (T001..T003 全部 `[x]`) — **BLOCKS** all user stories。
- **User Stories (Phase 3 / 4 / 5)**: All depend on Foundational phase completion (T004..T006 全部 `[x]`)。
  - User Stories 1 / 2 / 3 彼此**独立**（每份文档可独立落盘 + 独立 review）。
  - 推荐顺序：US1 → US2 → US3（workflow.md 阶段锚点先定，US2 的模块→阶段映射可引用；US2 模块 ID 命名空间定后，US3 的 schema 字段可引用 module_id）。
  - 实际执行可按团队人员并行（如多人同时落盘 3 份文档）。
- **Polish (Phase 6)**: Depends on all 3 User Stories complete (T015 / T028 / T052 全部 `[x]`)。

### User Story Dependencies

- **User Story 1 (P1)**: 依赖 Phase 2 T004（命名约定 + 阶段名 + 退出码 + 日志标签基础表）；不依赖 US2 / US3；可独立 review。
- **User Story 2 (P1)**: 依赖 Phase 2 T005（module_id 初始候选表）；不依赖 US1 / US3；可独立 review；但模块→阶段映射表的"下游模块"列可能引用 US1 阶段名（可在 T025 阶段查阅 US1 的 workflow.md 阶段名表后回填）。
- **User Story 3 (P1)**: 依赖 Phase 2 T006（schema_id + 锚点基础表）；不依赖 US1 / US2；可独立 review；但 schema 字段中 `RuntimeConfig.model_provider` 取值（如 `'openai-compatible'`）可借鉴 US1 阶段 3 `model_adapt` 的失败模式表。

### Within Each User Story

- 文档元信息 / 主要章节 / 表格 / 列表 任务可并行（无依赖）。
- "交叉引用 + 变更日志" 任务依赖主体内容已落盘。
- "Verify" 任务依赖该 Story 所有"内容"任务全部 `[x]`。

### Parallel Opportunities

- **Phase 0 (T000)**: 顺序前置，单独运行，不与其它任务并行。
- **Phase 1**: T001..T003 不可并行（顺序依赖 T001 读设计依据 → T002 检查目录 → T003 建速查表）；T001 / T003 可与 T000 部分并行（但 T002 必须在 T000 之后）。
- **Phase 2**: T004 / T005 / T006 **完全并行**（3 张基础表互不依赖）。
- **Phase 3 (US1)**: T008（创建文件）必须先完成；T009..T013 **完全并行**（5 个一级章节独立）；T014 依赖 T009..T013 全部完成；T015 依赖 T014。
- **Phase 4 (US2)**: T016 必须先完成；T017 / T018 + T019..T023 全部并行；T024 / T025 / T026 依赖 T019..T023 全部完成；T027 依赖 T024..T026；T028 依赖 T027。
- **Phase 5 (US3)**: T029 必须先完成；T030 / T031 + T032..T050 全部并行（19 个 schema 章节互不依赖）；T051 依赖 T032..T050 全部完成；T052 依赖 T051。
- **Phase 6**: T053 → T054 → T055 → T056 顺序依赖。

### Parallel Team Strategy

若多人并行：
- Person A：T000 → Phase 1 (T001..T003) → Phase 2 (T004..T006) → Phase 3 US1 (T007..T015)。
- Person B：等待 T000 + Phase 1 + Phase 2 完成后，并行执行 Phase 4 US2 (T016..T028)。
- Person C：等待 T000 + Phase 1 + Phase 2 完成后，并行执行 Phase 5 US3 (T029..T052)。
- Person A：US1 完成后，参与 Phase 6 跨文档核验。
- Project Maintainer：T054 人工 review + T055 checklist 同步 + T056 commit。

---

## Implementation Strategy

### MVP First (User Story 1 Only)

最小可行产出 = Phase 0 + Phase 1 + Phase 2 + Phase 3（US1 workflow.md）。
1. 完成 Phase 0 (T000) —— 修订 checklist 与 spec 对齐。
2. 完成 Phase 1 (T001..T003) —— 准备依据。
3. 完成 Phase 2 (T004..T006) —— 建基础表。
4. 完成 Phase 3 (T007..T015) —— 落盘 workflow.md。
5. **STOP and VALIDATE**: 跑 §QS-1.1..§QS-1.5 + §QS-2.1 验证 workflow.md。
6. 如 review 通过：MVP 完成，**仍不可进入 Feature 01**（因为 US2 / US3 还没落盘，下游 Feature 设计会缺依据）；继续做 US2。

### Incremental Delivery

1. **MVP-1 (US1)**: Phase 0 + Phase 1 + Phase 2 + Phase 3 → workflow.md 落盘 → 验证。
2. **MVP-2 (US1+US2)**: + Phase 4 → architecture_modules.md 落盘 → 验证；模块边界与依赖矩阵就绪。
3. **MVP-3 (US1+US2+US3)**: + Phase 5 → module_schemas.md 落盘 → 验证；类型契约就绪。
4. **Complete (Phase 6)**: 跨文档一致性核验 + 人工 review + checklist 同步 + commit。
5. **Done**: 进入 Feature 01-10+ 的 spec 阶段。

### Why This Order

- workflow.md 先做：6 阶段名是 US2 / US3 的"时间线锚点"，先把时间线定下来，后续模块归属、schema 触发阶段都好对齐。
- architecture_modules.md 其次：模块 ID 命名空间是 US3 字段引用的对象，先稳定命名空间。
- module_schemas.md 最后：19 个 schema 是 US1 / US2 字段引用的对象，最后做可以确保所有引用都能找到目标。

---

## Notes

- 本任务列表**不写任何 Python 源代码、不创建 `langagent/` 包、不写 `tests/` 目录**（spec OOS-1..O-3 严格约束）。
- `[P]` 任务 = 不同文件 / 不同小节 / 无依赖；不标 `[P]` 的任务 = 顺序依赖前一任务。
- `[US1] / [US2] / [US3]` 标签映射 spec.md 的 3 个 User Story，用于跨任务可追溯性。
- 每个 User Story 完成后**应立即独立 review**（按 §QS-1 机械 + §QS-2 人工），不要等 3 份文档全部完成后再统一 review（早发现早修复）。
- Phase 6 完成后，**不要**自动 push git；按宪法第 VIII 条 6 款由项目维护者本人 push。
- 若 Phase 6 T055 同步 checklist 时发现 73 项之外的实际数字变化（如新增项的 [x] 出现），属正常——这是 review 后的真实反映，以 `grep` 实际输出为准。

## 本轮 /speckit.tasks 重入修复（2026-09-14）

> 本 tasks.md 由 `/speckit.tasks` 重入命令修订；针对 2 项缺陷（A7 / A8）完成以下 4 处字面同步；其余 56 个任务定义（T001–T056）经核对已与 spec.md（254 行，含 Q10）/ plan.md（277 行，含 Q10 row）/ 其余下游产物字面对齐，无需结构性修改。

| # | 缺陷 | 修订位置 | 修订内容 |
|---|---|---|---|
| **A7** | 文件头 L4-5 对 spec.md / plan.md 的行数与 Clarifications 数量字面过期 | L4-5 | `spec.md (required, 253 行；含 9 条 Clarifications Q1–Q9 + ...)` → `spec.md (required, 254 行；含 10 条 Clarifications Q1–Q10 + 8 项局部精修 + 4 项 /speckit.specify 重入缺陷修补 + Q10 /speckit.specify 追加澄清)`；`plan.md (required, 245 行；含 §Spec 同步说明 8 项精修映射表 + 后续 spec 修订溯源附录)` → `plan.md (required, 277 行；含 §Spec 同步说明 10 条 Clarifications 映射表 + 8 项局部精修 + 4 项 /speckit.specify 重入缺陷溯源 + /speckit.plan 重入 6 处修订记录)`。 |
| **A8** | T011（写 workflow.md 退出码表）未显式引用 Q10 多阶段映射澄清 | L118 (T011) | 任务描述追加 Q10 字面："触发阶段列允许多阶段映射（Q10）：多阶段时以 `/` 分隔（如 `dir_load / config_resolve`），或以'所有阶段'统称 6 个阶段；总行数仍严格 = 12，每个退出码对应恰好 1 行（多阶段映射不影响行数）；语义为'该退出码在所列任一阶段触发时即返回'；阶段名集合严格属于 6 阶段之一或'所有阶段'"；FR-013 措辞升级为 `FR-013 + Q4 + Q10`。 |
| **—** | T015（运行 workflow.md 独立验证）未显式核验 Q10 多阶段映射约束 | L122 (T015) | 验证步骤追加 1 条："额外核验 FR-013 退出码表的'触发阶段'列符合 Q10 多阶段映射约束——总行数 = 12，每行'触发阶段'列内容仅由 6 阶段名之一或多阶段（以 `/` 分隔）或'所有阶段'组成"。 |
| **—** | 文档缺本轮重入修复的可见性记录 | L290+ (本节) | 新增"## 本轮 /speckit.tasks 重入修复（2026-09-14）"小节，记录 A7 / A8 字面同步 + 56 个任务定义的对齐核对结论；与 spec.md"## Clarifications" / plan.md"## 本轮 /speckit.plan 重入修复"形成 3 级同步闭环。 |

> **传播核对**：本次 4 处 tasks.md 字面同步触发以下下游产物核对——

| 产物 / 任务段 | 是否需修改 | 核对依据 |
|---|---|---|
| `T000`（checklist 修订）| ❌ 无需修改 | T000 (a)-(e) 4 处修订已在 §预修正 checklist 节记录完整（含 L73 / 4 项修订详情）；本轮 A7 / A8 不涉及 checklist 字面变更。 |
| `T001-T003`（Phase 1 Setup）| ❌ 无需修改 | T001 读设计依据 / T002 验证目录 / T003 建速查表均与 spec / plan 当前状态兼容（命名约定 Q3 / 阶段名 FR-012 / 退出码集 FR-013 均为字面引用，未受 Q10 字面追加影响）。 |
| `T004-T006`（Phase 2 Foundational）| ❌ 无需修改 | T004 退出码表 + T005 module_id 候选 + T006 schema_id 候选：T005 / T006 与 Q10 无关；T004 退出码字面量 `{0,1,2,3,4,5,64,65,66,70,78,130}` 与 spec Q4 一致（Q10 不改变退出码集合，仅改变"触发阶段"列的语义）。 |
| `T007-T015`（US1 workflow.md）| ✅ **T011 / T015 已修订**（见上表 A8 / 第 3 行）；T007-T010 / T012-T014 无需修改 | T011 退出码表任务已追加 Q10 字面；T015 验证任务已追加 Q10 核验步骤；其余 US1 任务（T007 创建文件 / T008 元信息 / T009 CLI / T010 6 阶段 / T012 日志标签 / T013 MDA / T014 交叉引用）均与 Q10 无关。 |
| `T016-T028`（US2 architecture_modules.md）| ❌ 无需修改 | US2 不涉及退出码表 / 触发阶段 / Q10；模块依赖矩阵 / CI 校验清单 / 模块 ID 命名空间均与 Q10 无关。 |
| `T029-T052`（US3 module_schemas.md）| ❌ 无需修改 | US3 不涉及退出码表 / 触发阶段 / Q10；19 个 schema 字段级定义与 Q10 无关。 |
| `T053-T056`（Phase 6 Polish）| ❌ 无需修改 | T053 跑 quickstart §QS-1 全段机械核验 / T054 人工 review / T055 checklist 同步 / T056 commit：T053 中 quickstart.md §QS-1.5 死链扫描已包含 `{#exit-code-*}` 锚点核验（FR-013 锚点命名空间），与 Q10 多阶段映射兼容；其余 T054-T056 与 Q10 无关。 |

> **结论**：本轮 `/speckit.tasks` 重入仅触发 4 处字面同步（2 项缺陷 + 2 处一致性补丁），不引入新任务结构或删除任何任务；T001–T056 共 56 个任务定义 + T000（已完成）共 57 个任务节点全部与 spec.md L254 + plan.md L277 当前状态字面 + 语义对齐，可直接进入 Phase 1（Setup）执行。
>
> **下游一致性闭环**（spec / plan / tasks 三级同步）：
>
> - `spec.md` L25 含 Q10（/speckit.specify 重入追加，修复 A9）
> - `plan.md` L132-147 含 10 条 Clarifications 体现表 + L225 Q10 Post-Design 评注 + L250-277 "本轮 /speckit.plan 重入修复" 节（/speckit.plan 重入，修复 A1/A2/A3/A6/A10）
> - `tasks.md` 本节含 2 项缺陷 + 4 处字面同步（/speckit.tasks 重入，修复 A7/A8）
>
> 三级同步链路：spec Q10 → plan Q10 row + Q10 评注 → tasks T011 Q10 字面 + T015 Q10 核验。任何后续 `/speckit.*` 重入如涉及 Q10 / FR-013 / 退出码表，应同时同步 spec / plan / tasks 三级；仅改任一级会造成字面漂移。

## 本轮 /speckit.tasks 重入修复（2026-09-15）

> 本 tasks.md 由 `/speckit.tasks` 重入命令修订；针对 2026-09-15 /speckit.specify 重入追加的 5 处 spec 修订（Q11 + Q12 + FR-043 主条款扩 `...此处略` + FR-043 (a) 新增子条款 + E-2 v0.1.0 处理 + E-5 模式清单对齐 SC-004） + 1 处 /speckit.plan 重入触发的下游修订（`contracts/module_schemas.md.contract.md` 新增 §MC-2.6 扩展接口约定），完成以下 5 处字面同步（其中 C5 修复任务自身违反 FR-043 (a) 的占位符）+ 1 处一致性补丁；其余 56 个任务定义（T001–T056）经核对已与 spec.md（260 行）+ plan.md（305 行）+ 其余下游产物字面对齐，无需结构性修改。

| # | 缺陷 | 修订位置 | 修订内容 |
|---|---|---|---|
| **C1** | 文件头 L4 对 spec.md 行数与 Clarifications 数量字面过期（254 → 260；10 → 12 Clarifications；缺 4 项 spec 缺陷修补 2026-09-15 描述） | L4 | spec.md 字面 `254 行` → `260 行`；`10 条 Clarifications Q1–Q10` → `12 条 Clarifications Q1–Q12`（Q11 / Q12 由 /speckit.specify 2026-09-15 重入追加）；新增"4 处 spec 缺陷修补 2026-09-15（FR-043 占位词清单扩 `...此处略` + 新增 (a) 扩展占位子条款 / E-2 新增 v0.1.0 处理澄清 / E-5 硬编码模式清单对齐 SC-004 + 删除误写 `/ SC-005`）"；Q10 措辞保留 |
| **C2** | 文件头 L5 对 plan.md 行数与本轮重入记录字面过期（277 → 305；缺 /speckit.plan 重入 2026-09-15 修订记录） | L5 | plan.md 字面 `277 行` → `305 行`；`/speckit.plan 重入 6 处修订记录` → `/speckit.plan 重入 6 处修订记录（2026-09-14）+ 1 处重入修订（2026-09-15，新增 §本轮 /speckit.plan 重入修复（2026-09-15）节 + §MC-2.6 扩展接口约定 1 处下游 contracts 修订）` |
| **C3** | L22 "Spec 演化说明" 段头与 L84 T001 描述中"9 轮 clarify / 9 条 Clarifications"字面过期 | L22 / L84 | L22 "9 轮 clarify + 8 项局部精修后形成" → "12 轮 clarify + 8 项局部精修 + 4 项 /speckit.specify 重入缺陷修补 + 4 处 spec 缺陷修补（2026-09-15）后形成"；L84 T001 中"理解 9 条 Clarifications" → "理解 12 条 Clarifications Q1–Q12"；同时在 T001 描述末尾追加一句："特别注意 `contracts/module_schemas.md.contract.md` §MC-2.6 扩展接口约定——FR-043 (a) 路径 1 落盘形式契约" |
| **C4** | T044 警示文本未显式引用 FR-043 (a) / Q11 两条路径 + `contracts/module_schemas.md.contract.md` §MC-2.6 | L182 (T044) | 警示段落升级为"FR-043 + FR-043 (a) / Q11"；显式列两条路径——**路径 1（推荐，参考 §MC-2.6）**：`#### 扩展接口约定` 二级小节 + `grader_extensibility: list[str] = []`；**路径 2（fallback）**：`Literal[...]` 直接枚举 5 个当前取值，不预留扩展字段 |
| **C5** | **T048 任务描述自身违反 FR-043 (a)**：原 T048 中 `Literal["pii_leak", "unauthorized_tool", "prompt_injection", "<其它枚举>"]` 示例的 `<其它枚举>` 字面量即 FR-043 (a) 明示禁止的占位符之一；且"4 类安全事件"措辞与"3 个字面量 + 1 个 `...`"内部字面漂移 | L186 (T048) | 移除 `<其它枚举>` 字面量；"4 类安全事件" → "3 个当前安全事件类别"（与 data-model.md DM-2.17 字面对齐）；警示段落升级为"FR-043 + FR-043 (a) / Q11"，显式列两条路径——路径 1：`#### 扩展接口约定` + `category_extensibility: list[str] = []`；路径 2：`Literal["pii_leak", "unauthorized_tool", "prompt_injection"]` 直接枚举 3 个当前取值；附注说明本次修订动机（原 T048 描述本身违反 FR-043 (a)） |
| **C6** | 文档缺本轮重入修复的可见性记录 | 本节 | 新增"## 本轮 /speckit.tasks 重入修复（2026-09-15）"小节，记录 5 项字面同步（C1-C5）+ 1 处一致性补丁（C6）+ 56 个任务定义的对齐核对结论；与 spec.md "## Clarifications Q11+Q12" / plan.md "## 本轮 /speckit.plan 重入修复（2026-09-15）" / contracts "## MC-2.6 扩展接口约定" 形成 4 级同步闭环 |

> **传播核对**：本次 6 处 tasks.md 字面同步触发以下下游产物核对——
>
> | 产物 / 任务段 | 是否需修改 | 核对依据 |
> |---|---|---|
> | `T000`（checklist 修订，已完成）| ❌ 无需修改 | T000 (a)-(e) 5 处修订已于 2026-09-14 闭环；本轮 Q11/Q12/FR-043 (a)/E-2/E-5 不涉及 checklist 字面变更（checklist 占位词清单与 FR-043 主条款字面已对齐） |
> | `T001-T003`（Phase 1 Setup）| ✅ **T001 已修订**（见上表 C3）| T001 已在末尾追加 §MC-2.6 引用；T002 / T003 与本轮修订无关 |
> | `T004-T006`（Phase 2 Foundational）| ❌ 无需修改 | T004 退出码表 / T005 module_id 候选 / T006 schema_id 候选：T005 / T006 与本轮修订无关；T004 退出码字面量 `{0,1,2,3,4,5,64,65,66,70,78,130}` 与 spec Q4 + Q10 一致 |
> | `T007-T015`（US1 workflow.md）| ❌ 无需修改 | T007-T015 不涉及 schema 字段 / extensibility 路径 / migrators 字段；本轮 E-5 模式清单对齐 SC-004 已隐含在 T053 §QS-1.3 核验命令中（SC-004 是 workflow.md 写完后才核验的项） |
> | `T016-T028`（US2 architecture_modules.md）| ❌ 无需修改 | US2 不涉及 schema 字段定义 / extensibility 路径 / migrators 字段；模块依赖矩阵 / CI 校验清单 / 模块 ID 命名空间与本轮修订无关 |
> | `T029-T052`（US3 module_schemas.md）| ✅ **T044 / T048 已修订**（见上表 C4 / C5）| T044 / T048 警示段落已对齐 FR-043 (a) / Q11 / §MC-2.6；T032-T043 / T045-T047 / T049-T050 / T051 / T052 与本轮修订无关 |
> | `T053-T056`（Phase 6 Polish）| ❌ 无需修改 | T053 §QS-1.3 已覆盖 SC-004 硬编码模式核验（E-5 修订后的模式清单已在 SC-004 中）；T053 §QS-1.8 中 schema 数量检查仍为 19 个一级章节 / 22 个类型，不受 Q11 / Q12 影响；T054-T056 与本轮修订无关 |
>
> **结论**：本轮 `/speckit.tasks` 重入共触发 6 处字面同步（5 项缺陷 C1-C5 + 1 处一致性补丁 C6），不引入新任务结构或删除任何任务；T001–T056 共 56 个任务定义 + T000（已完成）共 57 个任务节点全部与 spec.md L260 + plan.md L305 + `contracts/module_schemas.md.contract.md` §MC-2.6 当前状态字面 + 语义对齐，可直接进入 Phase 1（Setup）执行。
>
> **下游一致性闭环**（spec / plan / tasks / contracts 四级同步）：
>
> - `spec.md` L26-27 含 Q11 + Q12（/speckit.specify 2026-09-15 重入追加）；L179-182 FR-043 占位词清单扩 `...此处略` + 新增 (a) 扩展占位子条款；L93 E-2 v0.1.0 处理子条款；L96 E-5 模式清单对齐 SC-004。
> - `plan.md` L132 段头更新（260 行 / 12 Clarifications / 4 项 spec 缺陷修补）；L148-149 新增 Q11 + Q12 行；L239+ 新增 §本轮 /speckit.plan 重入修复（2026-09-15）节（B1-B4 + 8 行传播核对表）。
> - `contracts/module_schemas.md.contract.md` L101-117 新增 §MC-2.6 扩展接口约定（FR-043 (a) 路径 1 落盘形式契约）。
> - `tasks.md` 本节含 5 项字面同步（C1-C5）+ 1 处一致性补丁（C6），56 个任务定义 + T000 共 57 个任务节点全部对齐。
>
> 四级同步链路：spec Q11+Q12+FR-043 (a)+E-2+E-5 → plan Q11+Q12 row + B1-B4 修订表 → contracts MC-2.6 落盘形式 → tasks T001 §MC-2.6 引用 + T044 / T048 警示段落。任何后续 `/speckit.*` 重入如涉及 extensibility / migrators / 占位词 / 硬编码模式，应同时同步 4 级；仅改任一级会造成字面漂移。

## 本轮 /speckit.tasks 重入修复（2026-09-15, 第 2 次）

> 本 tasks.md 由 `/speckit.tasks` 重入命令修订；针对 2026-09-15 /speckit.specify 第 4 次重入追加的 2 处 spec 修订（D1：Out of Scope 小节 `O-1..O-12` 前缀统一为 `OOS-1..OOS-12` 对齐 plan.md / tasks.md 既有用法 + D2：OOS-3 行内追加宪法第 VIII 条锚定句消除宪法对齐候选） + 1 处 /speckit.plan 重入触发的下游修订（`plan.md` L67 Constitution Check 第 VIII 条评注引用 spec.md OOS-3 锚定句指针 + L132 spec 修补清单由 4 项扩为 6 项 + 新增 §本轮 /speckit.plan 重入修复（2026-09-15, 第 2 次）节），完成以下 3 处字面同步；其余 56 个任务定义（T001–T056）+ T000（已完成）共 57 个任务节点经核对已与 spec.md（260 行）+ plan.md（332 行）+ 其余下游产物字面对齐，无需结构性修改。

| # | 修订 | 修订位置 | 修订内容 |
|---|---|---|---|
| **D1** | 文件头 L4 spec.md 描述缺第 4 次重入（OOS-N 统一 + OOS-3 第 VIII 条锚定）记录 | L4 | L4 末尾追加："+ **第 4 次重入 2026-09-15** Out of Scope 小节 `O-1..O-12` 前缀统一为 `OOS-1..OOS-12` 对齐 plan.md / tasks.md 既有用法 + OOS-3 行内追加宪法第 VIII 条锚定句消除宪法对齐候选" |
| **D2** | 文件头 L5 plan.md 行数（305 → 332）+ 缺 2026-09-15 第 2 次 /speckit.plan 重入记录 | L5 | `plan.md (required, 305 行;...)` → `plan.md (required, 332 行;...)`；`+ 1 处 /speckit.plan 重入修订（2026-09-15，...）` 后追加 `+ **1 处 /speckit.plan 重入修订（2026-09-15 第 2 次，新增 §本轮 /speckit.plan 重入修复（2026-09-15, 第 2 次）节，L67 Constitution Check 第 VIII 条评注引用 spec.md OOS-3 锚定句指针 + L132 spec 修补清单由 4 项扩为 6 项）**` |
| **D3** | 文档缺本轮重入修复的可见性记录 | 本节 | 新增"## 本轮 /speckit.tasks 重入修复（2026-09-15, 第 2 次）"小节，记录 2 项 spec 修订（D1 + D2）+ 1 处 plan 下游修订触发 + 3 处字面同步 + 57 个任务定义的对齐核对结论；与 spec.md "## Out of Scope OOS-3 第 VIII 条锚定" / plan.md "## 本轮 /speckit.plan 重入修复（2026-09-15, 第 2 次）" 形成 3 级同步闭环 |

> **传播核对**：本次 3 处 tasks.md 字面同步触发以下下游产物核对——
>
> | 产物 / 任务段 | 是否需修改 | 核对依据 |
> |---|---|---|
> | `T000`（checklist 修订，已完成）| ❌ 无需修改 | T000 涉及的是占位词清单 / module 数 / 字段数等内部 spec 字面修订；本轮 D1 / D2 是 OOS 编号格式 + 宪法锚定句，与 checklist 无关 |
> | `T001-T003`（Phase 1 Setup）| ❌ 无需修改 | T001 关注 §MC-2.6 引用 + 12 Clarifications 理解（已闭环于 C3 修订）；D1 / D2 不影响 Setup 段 |
> | `T004-T006`（Phase 2 Foundational）| ❌ 无需修改 | T004 退出码表 / T005 module_id 候选 / T006 schema_id 候选：与 OOS 编号 / 宪法第 VIII 条锚定无关 |
> | `T007-T015`（US1 workflow.md）| ❌ 无需修改 | US1 写 workflow.md 6 阶段 + 4 CLI 子命令 + 12 退出码表 + 日志标签表 + MDA 对照表；与 OOS 编号格式 / 宪法第 VIII 条锚定无关 |
> | `T016-T028`（US2 architecture_modules.md）| ❌ 无需修改 | US2 写 5 层模块 + 依赖矩阵 + Feature 拆分 + CI 清单；与 OOS 编号 / 宪法第 VIII 条无关 |
> | `T029-T052`（US3 module_schemas.md）| ❌ 无需修改 | US3 写 19 schema 字段定义；T044 / T048 警示段落已在 C4 / C5 修订中闭环；D1 / D2 不影响 schema 字段定义 |
> | `T053-T056`（Phase 6 Polish）| ❌ 无需修改 | T053 §QS-1 机械核验覆盖 SC-001..SC-008；D1 / D2 不引入新的 SC 项（OOS-N 统一是编号格式问题，不影响 SC；OOS-3 第 VIII 条锚定是 spec 内部字面修订，不影响 SC） |
>
> **结论**：本轮 `/speckit.tasks` 重入（第 2 次）共触发 3 处字面同步（D1 / D2 / D3），不引入新任务结构、不删除任何任务、不修改 T001–T056 任何任务定义；T001–T056 共 56 个任务定义 + T000（已完成）共 57 个任务节点全部与 spec.md L260 + plan.md L332 当前状态字面 + 语义对齐，可继续按原计划从 Phase 1（Setup）开始执行。
>
> **下游一致性闭环**（spec / plan / tasks 三级同步）：
>
> - `spec.md` L249-260 Out of Scope 小节 `O-1..O-12` 前缀统一为 `OOS-1..OOS-12`；L251 OOS-3 行内追加宪法第 VIII 条锚定句（spec.md 仍为 260 行）。
> - `plan.md` L67 Constitution Check 第 VIII 条评注改为引用 spec.md OOS-3 锚定句指针 + L132 spec 修补清单由 4 项扩为 6 项 + 新增 §本轮 /speckit.plan 重入修复（2026-09-15, 第 2 次）节（plan.md 由 305 行扩为 332 行）。
> - `tasks.md` 本节（D1 + D2 + D3）记录本轮 spec / plan 修订对 tasks.md 的传播核对，57 个任务节点全部对齐。
>
> 五级同步链路（含前一轮）：spec Q11+Q12+FR-043 (a)+E-2+E-5+OOS-N+OOS-3 第 VIII 条 → plan Q11+Q12 row + B1-B4 + C1+C2 修订表 → contracts MC-2.6 落盘形式 → tasks T001 §MC-2.6 引用 + T044 / T048 警示段落 + 本节 D1+D2+D3 → checklists CHK307 第 VIII 条 TDD 项。任何后续 `/speckit.*` 重入如涉及 OOS 编号格式 / 宪法锚定 / extensibility / migrators / 占位词 / 硬编码模式，应同时同步全部 5 级；仅改任一级会造成字面漂移。
