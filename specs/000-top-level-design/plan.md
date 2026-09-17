# Implementation Plan: Feature 00 — 顶层设计（Top-Level Design）

**Branch**: `000-top-level-design` | **Date**: 2026-09-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/000-top-level-design/spec.md`

> 本文档是 Feature 00 的实施方案。Feature 00 是**纯文档 Feature**——唯一产出物是 3 份互相引用的 Markdown 设计文档（落盘于 `harness/top_level_design/`），不涉及 Python 源代码、依赖文件、测试用例。本 plan 因此相应精简。

## Summary

Feature 00 的核心任务是产出 3 份 Markdown 设计文档（`workflow.md` / `architecture_modules.md` / `module_schemas.md`），作为后续 Feature 01-10+ 拆分任务、定义类型契约、声明模块边界的事实来源。本 plan 通过 Phase 0 调研（research.md）解决 spec 中残留的隐性技术决策，通过 Phase 1 设计（data-model.md、contracts/、quickstart.md）把 3 份文档的"必备小节 / 必备字段 / 命名约定 / 锚点命名空间"等设计依据沉淀下来，由实施者按本 plan 落盘 3 份文档并由项目维护者按 quickstart.md 完成人工 review。

## Technical Context

> Feature 00 是纯文档 Feature，无运行时、无构建产物、无语言/框架约束。下述"Technical Context"按"以文档为对象"的角度填写，不引入任何代码层概念。

**Language/Version**: N/A（不涉及源代码）。文档本身使用 Markdown（CommonMark + GFM anchor `{#...}` 显式锚点扩展）。

**Primary Dependencies**: N/A（不引入运行依赖）。调研来源限于以下**项目内本地副本**：
- `harness/LangChain_doc/` —— LangChain Python 官方文档（仅作 API 形态参考，不复制其内容）。
- `harness/LangGraph_doc/` —— LangGraph Python 官方文档（同上）。
- `harness/Managed_deep_agents/langsmith/python/*.md` —— MDA 设计参考（仅作"能力对照表"引用源，不复制其章节结构）。

**Storage**: 3 份 Markdown 文件，落盘于 `harness/top_level_design/`：
- `harness/top_level_design/workflow.md`
- `harness/top_level_design/architecture_modules.md`
- `harness/top_level_design/module_schemas.md`
字符编码 UTF-8，行尾 LF，无 BOM（FR-003）。

**Testing**: 3 份文档的"产出物校验"由 `specs/000-top-level-design/checklists/requirements.md`（spec 衍生品，段 2）逐条核验——机械项用 `grep` / `ripgrep` 脚本，人工项由项目维护者 review。本 plan 范围不实施任何 `tests/` 目录或 pytest 套件（宪法第 VIII 条 TDD 约束待 Feature 01-10+ 涉及运行时代码时再触发）。

**Target Platform**: 任何支持 CommonMark + GFM anchor 的 Markdown 渲染器（VS Code / GitHub / GitLab / Obsidian / Typora 均可），不依赖特定平台。

**Project Type**: Documentation Feature（spec 模板的 5 类——`library / cli / web-service / mobile-app / compiler / desktop-app`——均不适用；按 `documentation` 处理）。

**Performance Goals**: 不适用。文档 review 时间期望：单份文档完整 review ≤ 30 分钟（项目维护者）；3 份文档交叉引用核验 ≤ 10 分钟（机械脚本）。

**Constraints**:
- 3 份文档每份行数 ≥ 200（FR-002 / SC-001）。
- FR-013 退出码表的"触发阶段"列允许多阶段映射（Q10）：一个退出码对应多个阶段时以 `/` 分隔（如 `dir_load / config_resolve`），或以"所有阶段"统称 6 个阶段；总行数仍严格 = 12，每个退出码对应表中恰好 1 行。
- 不得出现 LangSmith 相关 import / API / 环境变量名 / 镜像名（FR-051 / 宪法第 III 条）。
- 不得出现绝对路径、内网 IP、硬编码 API key（FR-052 / SC-004 / 宪法第 X 条）。
- 不得出现 `TODO` / `TBD` / `FIXME` / `XXX` / `留待决定` / `待定` / `占位` 之类占位词（FR-043 / SC-005）。
- 不写 `langagent/` 包、不写 `tests/`、不写 `pyproject.toml`、不写 `.py` 源文件（SC-008 / spec OOS-1..O-12）。
- 与宪法第 I-XIV 条无冲突（SC-006 / FR-050）。

**Scale/Scope**:
- 3 份 Markdown 文件。
- `workflow.md` 内容规模：6 阶段 × 5 栏 + 4 CLI 子命令 × 5 栏 + 12 退出码表 + N 个日志标签表 + MDA 能力对照表（≥ 10 行）+ 文档元信息。
- `architecture_modules.md` 内容规模：5 层 × ≥ 2 模块 × 4 栏 + 完整对称依赖矩阵（行数 = 模块数²）+ Feature 拆分映射表 + ≥ 12 条静态约束 CI 清单 + 文档元信息。
- `module_schemas.md` 内容规模：19 个一级章节（其中 3 个合并章节各承载 2 个类型，共 22 个类型）× 4 个二级小节（合并章节 6 个）+ Schema 总目录 + 文档元信息。
- 全部 3 份文档总字数预估：≥ 30 KB Markdown。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法条款 | 关联 | 评估 | 备注 |
|---|---|---|---|
| **第 I 条** 项目身份与边界 | FR-001 / OOS-1..O-12 | ✅ Pass | Feature 00 不发布 SDK、不暴露 importable API；3 份文档严格位于 `harness/top_level_design/` 目录，不污染 `langagent/` 包路径。 |
| **第 II 条** 技术栈与依赖范围 | A-2 / A-3 | ✅ Pass | Feature 00 不引入任何 Python 依赖；3 份文档不 import 任何代码；MDA 仅作"MDA 能力对照表"引用源，不复制其章节结构、不 pip install。 |
| **第 III 条** LangSmith 剥离原则 | FR-051 / E-7 | ✅ Pass | 3 份文档不得出现 `langsmith` import / API / 环境变量名（`LANGSMITH_API_KEY` / `LANGCHAIN_TRACING_V2` / `LANGCHAIN_API_KEY` / `LANGCHAIN_ENDPOINT`）/ 镜像名 / Helm chart 名；如必须提及，措辞为反例（`LangSmith 仅作反例：不应 ...`）。 |
| **第 IV 条** 模型抽象层 | E-7 / FR-042 | ✅ Pass | 3 份文档不硬编码 provider；本地 OpenAI Compatible（Qwen3.8-27B）与联网模型同等优先级，由 `module_schemas.md` 的 `RuntimeConfig` schema 体现 provider 可声明性。 |
| **第 V 条** 智能体目录契约 | A-4 / E-3 | ✅ Pass | `architecture_modules.md` 的 `protocol` / `cross_cutting` 层与 `module_schemas.md` 的 `SkillSpec / SkillFrontmatter` / `ToolSpec / ToolSideEffect` / `MiddlewareSpec` / `ChannelSpec` / `ChannelContext` / `SandboxSpec` / `MemorySpec` / `IdentitySpec` / `EvalTaskSpec` 等 schema 与宪法第 V 条的智能体目录布局一一对应。 |
| **第 VI 条** Agent Loop 与 State | FR-037 / Q1 | ✅ Pass（澄清后）| `module_schemas.md` 的 `AgentState` 章节显式给出 5 字段（`messages` / `todos` / `files` / `context` / `scratchpad`）的 reducer 规则；`context` 字段 reducer 仅限 `overwrite` / `merge_with_prior`（Q1 澄清）。 |
| **第 VII 条** Middleware 与工具规则 | FR-034 | ✅ Pass | `module_schemas.md` 的 `ToolSpec / ToolSideEffect` / `MiddlewareSpec` schema 体现工具副作用标注、middleware 接入方式。 |
| **第 VIII 条** 开发方法论 TDD | OOS-3 | ✅ Pass | 详见 [spec.md OOS-3 行内锚定句](./spec.md)：第 VIII 条"测试驱动开发"语义范围限定于"产生可执行代码的功能开发"；Feature 00 仅产出 Markdown 设计文档、不产生可执行代码，故第 VIII 条不触发；本 Feature 产出物验证由 `quickstart.md` §QS-1 机械脚本 + §QS-2 人工 review 共同承担（tasks.md T053 / T054）。 |
| **第 IX 条** 质量诊断能力矩阵 | FR-036 / CHK308 | ✅ Pass | `module_schemas.md` 的 `Span / Trace` / `MetricsSnapshot` / `AuditEntry` / `EvalReport` / `DoctorReport` schema 与第 IX 条 5 项子能力（Tracing / Monitoring / Evaluation / Testing / Guardrails）一一对应。 |
| **第 X 条** 安全与隐私 | FR-052 / SC-004 | ✅ Pass | 3 份文档不得出现硬编码 API key、内网 IP、绝对路径；示例必须以 `<redacted>` / `internal.example` / `path/to/agent` 占位。 |
| **第 XI 条** 打包与分发 | FR-011 / Q5 | ✅ Pass | `workflow.md` "用户视角：CLI 生命周期"覆盖 `init` / `run` / `eval` / `doctor` 4 个核心子命令（Q5 澄清），无辅助子命令预留接口。 |
| **第 XII 条** 配置与可观测契约 | FR-035 | ✅ Pass | `module_schemas.md` 的 `RuntimeConfig` schema 体现"CLI > 环境变量 > .env > 内置默认"优先级；`Span / Trace` schema 字段含 `trace_id` / `span_id` / `parent_span_id` / `name` / `start` / `end` / `attributes`（宪法第 XII 条 3 款）。 |
| **第 XIII 条** 禁止项（Hard No） | FR-051 / FR-052 | ✅ Pass | 3 份文档不依赖 LangSmith 闭源、不硬编码 API key / 模型名 / 路径、不混入外部网络地址；用 `print` / `console.log` 替代结构化日志属代码层禁止项，与本 Feature 无关。 |
| **第 XIV 条** 宪法修订程序 | A-1 | ✅ Pass | 本 Feature 期间不修改宪法；如触及宪法条款边界（如"模块 → 协议层是否属于 SDK"），3 份文档以 `与宪法第 N 条关系：...` 显式标注（FR-050）。 |

**结论**：14 条宪法条款全部通过，**无违规需在 Complexity Tracking 中说明**。可进入 Phase 0。

## Project Structure

### Documentation (this feature)

```text
specs/000-top-level-design/
├── plan.md              # 本文件（/speckit.plan 命令产出）
├── research.md          # Phase 0 产出（/speckit.plan 命令）
├── data-model.md        # Phase 1 产出（/speckit.plan 命令）
├── quickstart.md        # Phase 1 产出（/speckit.plan 命令）
├── contracts/           # Phase 1 产出（/speckit.plan 命令）
│   ├── workflow.md.contract.md
│   ├── architecture_modules.md.contract.md
│   └── module_schemas.md.contract.md
├── spec.md              # 上一阶段产出（/speckit.specify 命令）
├── checklists/
│   └── requirements.md  # 上一阶段产出（/speckit.specify 命令）
└── tasks.md             # Phase 2 产出（/speckit.tasks 命令，不在本 plan 创建）
```

### Source Code (repository root)

> Feature 00 是纯文档 Feature，**不写任何源代码**。下列树形仅说明"3 份设计文档在仓库中的落盘位置"，不涉及 `src/` / `tests/` 等代码目录。

```text
# Feature 00 在仓库根的产出物位置
harness/
└── top_level_design/                      # Feature 00 唯一产出目录
    ├── workflow.md                        # 用户视角 CLI 生命周期 + 系统视角 6 阶段
    ├── architecture_modules.md            # 5 层架构 + 模块依赖矩阵 + Feature 拆分
    └── module_schemas.md                  # 19 个 schema 一级章节（22 个类型）

# 仓库根其它目录（不在 Feature 00 范围内，不动）
.
├── .specify/                              # 基础设施
├── .git/                                  # git 仓库
├── harness/
│   ├── LangChain_doc/                     # 调研源（只读）
│   ├── LangGraph_doc/                     # 调研源（只读）
│   ├── Managed_deep_agents/               # 调研源（只读）
│   ├── example/                           # 已存在的样例（不动）
│   ├── prompt/                            # 已存在的提示词（不动）
│   ├── reports/                           # 已存在的报告（不动）
│   └── top_level_design/                  # Feature 00 唯一落盘位置
├── LICENSE
├── README.en.md
├── README.md
└── specs/                                 # 规范目录
    └── 000-top-level-design/              # 本 Feature
```

**Structure Decision**: Feature 00 采用"**纯文档型**"结构——`harness/top_level_design/` 作为 3 份设计文档的**唯一落盘位置**（spec OOS-12 显式约束"不在 harness 之外的位置创建额外设计文档"），`specs/000-top-level-design/` 作为本 Feature 的 spec / plan / research / data-model / contracts / quickstart 自身文件位置。两层目录严格分离：3 份**对外设计文档**（供后续 Feature 引用）位于 `harness/top_level_design/`；3 份**本 Feature 自身产物**（供实施者 review）位于 `specs/000-top-level-design/`。

## Spec 同步说明

> 本 plan 反映 `spec.md`（260 行）的最新状态，含 **12 条 Clarifications**（Q1–Q12；Q1–Q10 主体设计锚点，Q10 由 /speckit.specify 2026-09-14 重入追加，修复缺陷 A9；Q11–Q12 由 /speckit.specify 2026-09-15 重入追加，授权 extensibility 字段与 migrators v0.1.0 省略规则）与 **6 项 spec 缺陷修补**（2026-09-15 /speckit.specify 重入：① Q11 + Q12 共 2 条 Clarification；② FR-043 占位词清单扩 `...此处略` + 新增 (a) 扩展占位子条款；③ E-2 新增 v0.1.0 处理澄清；④ E-5 硬编码模式清单对齐 SC-004 + 删除误写 `/ SC-005`；**第 4 次重入** ⑤ Out of Scope 小节 `O-1..O-12` 前缀统一为 `OOS-1..OOS-12` 对齐 plan.md / tasks.md 既有用法；⑥ OOS-3 行内追加第 VIII 条锚定句消除宪法对齐候选）。下面列出本 plan 各章节对它们的体现位置，供 review 时溯源。

### 12 条 Clarifications 在本 plan 中的体现

| # | 决策摘要（spec L16-27） | 本 plan 体现位置 |
|---|---|---|
| Q1 | AgentState 5 字段含 `context`；reducer 仅限 `overwrite` / `merge_with_prior` | Technical Context / Phase 1 (`data-model.md` `AgentState` schema) / Constitution Check 第 VI 条评注 |
| Q2 | 19 个一级章节承载 22 个类型（3 对合并：`Span/Trace` / `SkillSpec/SkillFrontmatter` / `ToolSpec/ToolSideEffect`） | Technical Context Scale/Scope / Phase 1 (`data-model.md` `Schema 总目录`) |
| Q3 | 章节标题 PascalCase + IDs snake_case + 锚点 kebab-case | Technical Constraints 段 / Phase 1 (`contracts/*` 锚点命名空间) |
| Q4 | 12 个退出码定稿 `{0,1,2,3,4,5,64,65,66,70,78,130}` | Technical Context Scale/Scope / Phase 1 (`contracts/workflow.md.contract.md`) |
| Q5 | CLI 仅 4 个核心子命令 `init` / `run` / `eval` / `doctor`，不预留辅助子命令 | Constitution Check 第 XI 条评注 / Phase 1 |
| Q6 | 阶段锚点 `#stage-*` 前缀（`#stage-dir_load` 等 6 个） | Phase 1 (`contracts/workflow.md.contract.md` 锚点命名空间) |
| Q7 | 依赖矩阵 4 符号语义 `→` / `↔` / `×` / `–`（完整对称方阵，无回路） | Phase 1 (`contracts/architecture_modules.md.contract.md` 矩阵章节) |
| Q8 | `module_id` 全局唯一（5 层之间），冲突改名（如 `cli_runner` / `runtime_runner`） | Phase 1 (`contracts/architecture_modules.md.contract.md`) |
| Q9 | 合并章节 6 个二级小节（前 2 个共用 + 后 2 个 × 2 类型并列） | Technical Context Scale/Scope / Phase 1 (`contracts/module_schemas.md.contract.md`) |
| Q10 | FR-013 退出码表多阶段映射：每个退出码 1 行；"触发阶段"列可填 1 个或多阶段名（`/` 分隔或"所有阶段"）；总行数仍严格 = 12 | Technical Context Constraints 段（追加约束）/ Phase 1 (`contracts/workflow.md.contract.md` §WC-2.4 已按多阶段映射落盘）/ Post-Design Constitution Check 第 XII 条评注 |
| Q11 | FR-043 (a) 扩展占位禁止：禁止 `...` / `<其它枚举>` / `etc.` 占位符表达"未来可能新增的取值"；路径 1（推荐）：schema 一级章节末尾追加"扩展接口约定"二级小节 + `<字段名>_extensibility` 字段（如 `grader_extensibility: list[str] = []` / `category_extensibility: list[str] = []`）；路径 2（fallback）：直接枚举所有当前取值（Literal） | Phase 1 (`contracts/module_schemas.md.contract.md` §MC-2.3 新增"扩展接口约定"约定段) / `tasks.md` T044 (L182) / T048 (L186) 警示（已含此约定）/ 本 plan §本轮 /speckit.plan 重入修复（2026-09-15）传播核对 |
| Q12 | v0.1.0 migrators 字段可省略（无历史 schema 可迁）；后续升 schema_version 且字段变更时必须按 E-2 主条款补 migrators | Technical Context Constraints 段（隐含：22 个类型 schema_version = `v0.1.0`、均无 migrators）/ Phase 1 (`data-model.md` DM-2 全部 22 个类型 schema_version 字段均为 `v0.1.0`、均无 migrators) / 本 plan §本轮 /speckit.plan 重入修复（2026-09-15）传播核对 |

### 8 项局部精修（2026-09-14）对 plan 的下游契约约束

> 8 项精修均在 spec.md / checklist 内部完成一致性闭环，未触及主体设计。下表列出每项精修的 spec 改动与对 plan 下游产物（research / data-model / contracts / quickstart / tasks）的传播结果。

| # | 优先级 / 类别 | spec 改动 | 对 plan 下游产物的传播 |
|---|---|---|---|
| **1** | HIGH / spec 自相矛盾 | US1-4（spec L43）/ US2-6（spec L63）/ US3-6（spec L82）的相对路径引用删除 `../` 前缀（FR-040 明确"不带 `./` 前缀、不带 `../`"） | contracts WC-2.7 / AC-2.7 / MC-2.4 本就规定"不带 `./` 前缀、不带 `../` 前缀"，无需修改；spec 自洽。 |
| **2** | MEDIUM / spec 措辞歧义 | FR-011 / FR-012 末尾追加 1 句："『项』特指项目符号列表项（即 Markdown `- ...` 列表条目）" | `research.md` R-4 下界表 / `contracts/*` 中"≥ N 项"等表述已隐含"项目符号列表项"语义，无需修改；`tasks.md` 中 T009 / T010 / T019-T023 / T032-T050 的"每栏 N 项"亦无歧义。 |
| **3** | MEDIUM / spec 措辞歧义 | FR-014："日志标签表至少 15 行（推荐使用 R-5 ...）" → "至少 15 行（硬下限）；如希望充分覆盖可参考 R-5 的 25 项初始集合，但 R-5 不作为强制目标" | `tasks.md` **T012 措辞同步更新**（"推荐使用 R-5" → "参考 R-5，不作为强制目标"）；`contracts/workflow.md.contract.md` WC-2.5 本就不写"推荐"，无需修改；`research.md` R-5 的 25 项集合字面量保留为参考表。 |
| **4** | LOW / spec 措辞一致性 | FR-022：""职责"栏建议 ≥ 2 项" → ""职责"栏 ≥ 2 项"（去掉"建议"，与同句其他 3 项强制语气一致） | `research.md` **R-4 措辞同步更新**（"职责"栏建议 ≥ 2 项" → "职责"栏 ≥ 2 项"）；`contracts/architecture_modules.md.contract.md` AC-2.3 本就无"建议"，无需修改。 |
| **5** | HIGH / checklist 字面漂移 | CHK122（checklist L64）："每层下挂至少 1 个模块" → "每层下挂至少 2 个模块；总模块数 ≥ 12"（与 FR-022 对齐） | checklist 已修订；plan Scale/Scope / `research.md` R-1.3 / `contracts/architecture_modules.md.contract.md` AC-2.3 / `quickstart.md` QS-2.2 早已锁定此下界，无需修改。 |
| **6** | HIGH / checklist 字面漂移 | CHK137（checklist L79）："4 字段 reducer 规则" → "5 字段（含 `context`）reducer 规则"（与 FR-037 + Q1 对齐） | checklist 已修订；`data-model.md` DM-2.1 / `quickstart.md` QS-2.3 / `tasks.md` T032 早已锁定 5 字段结构，无需修改。 |
| **7** | HIGH / checklist 字面漂移 | CHK131（checklist L73）：4 列 → 5 列（增加 `承载类型数`）+ 表末合计行 `合计 — — — — 19 / 22`（与 FR-031 对齐） | checklist 已修订；`data-model.md` DM-1 / `contracts/module_schemas.md.contract.md` MC-2.2 早已锁定此结构，无需修改。 |
| **8** | HIGH / checklist ID 缺陷 | checklist L34 的 CHK020 重命名为 CHK021（消除与 L33 的重复 ID） | checklist 已修订；plan / research / data-model / contracts / quickstart / tasks 中无 `CHK020` / `CHK021` 引用，无需修改。 |

> **总结**：8 项精修共触发 **2 处下游产物措辞同步**——`research.md` R-4（精修项 4）+ `tasks.md` T012（精修项 3）；其余 6 项精修均在 spec.md / checklist 内部闭环。其余 6 个下游产物（`data-model.md` / `quickstart.md` / 3 份 `contracts/*.contract.md`）与精修后的 spec 已字面对齐，无需修改。
>
> **后续 spec 修订**（2026-09-14 /speckit.specify 重入后）：经 `/speckit.analyze` 发现 3 处主缺陷（算术 / 规则 / ID）+ 1 处后续修补（FR-033 计数描述），已在 `/speckit.specify` 重入时统一修订——
> - **缺陷 1 (CRITICAL)**：spec.md `FR-031` / `FR-032` / Q2 Clarification / US3 acceptance / Key Entities 共 6 处 `21 个类型` / `19 / 21` 字面量 → `22 个类型` / `19 / 22`；同步传播至 `data-model.md` DM-1 合计行 / `contracts/module_schemas.md.contract.md` MC-2.2 / `checklists/requirements.md` CHK131。**本 plan 中"8 项精修 #7"的合计行字面量同步由 `19 / 21` 更新为 `19 / 22`**（本表 L159 已修订）。
> - **缺陷 2 (HIGH)**：spec.md `FR-040` 末尾追加"跨目录相对路径"规则段；为使自检 grep `'跨目录'` 命中 1 行，处方文本"拼接跨级目录"微调为"拼接跨目录"（删 1 字"级"，语义等价）。
> - **缺陷 3 (HIGH)**：`checklists/requirements.md` L35/L36 CHK ID 重编号 CHK021 → CHK022 / CHK022 → CHK023（消除 L34/L35 重复）；本 plan 中无 `CHK021` / `CHK022` 引用，无需修改。
> - **缺陷 4 (后续修补)**：spec.md `FR-033` "19 个非合并章节" → "16 个非合并章节"（与 FR-032 / FR-041 字面对齐）。

### 不在本 plan 范围内修改的产物

下列产物由本 plan 在 Phase 0 / Phase 1 中**引用**而非**修改**，内容请直接查对应文件：

- `research.md`（Phase 0 产出）
- `data-model.md`（Phase 1 产出）
- `contracts/workflow.md.contract.md`
- `contracts/architecture_modules.md.contract.md`
- `contracts/module_schemas.md.contract.md`
- `quickstart.md`（Phase 1 产出）
- `checklists/requirements.md`（spec 阶段产出）
- `tasks.md`（Phase 2 产出，由 `/speckit.tasks` 命令生成）

## Phase 0: Outline & Research

**输出**：`research.md`（与本 plan 同目录）。

研究目标：解决 spec 中**已通过 12 轮 clarify 解决的所有歧义之外**残留的隐性技术决策，包括：
- 19 个 schema 的字段细节（必填字段、默认值、字段间约束）。
- 6 阶段 / 4 CLI 子命令的"五栏"具体内容蓝图。
- 5 层架构下的初始模块 ID 候选集合（供实施者参考）。
- MDA 能力对照表的最小行数下界。
- 静态约束 CI 校验清单的最小条数下界。

详见 [`research.md`](./research.md)。

## Phase 1: Design & Contracts

**输出**：`data-model.md`（与本 plan 同目录）、`contracts/*.contract.md`（3 份）、`quickstart.md`（与本 plan 同目录）。

设计目标：
- `data-model.md`：把 module_schemas.md 须承载的 19 个一级章节（22 个类型）的"字段 / 类型 / reducer / 磁盘格式 / LangChain/LangGraph 映射"沉淀为可机械核验的 schema 描述表。
- `contracts/`：把 workflow.md / architecture_modules.md / module_schemas.md 各自的"必备小节 / 必备字段 / 命名约定 / 锚点命名空间"沉淀为 3 份契约文件，作为实施者落盘时的格式合同。
- `quickstart.md`：把项目维护者的 review 流程（机械脚本 + 人工 review）沉淀为可一步步跑过的验证清单。

详见：
- [`data-model.md`](./data-model.md)
- [`contracts/workflow.md.contract.md`](./contracts/workflow.md.contract.md)
- [`contracts/architecture_modules.md.contract.md`](./contracts/architecture_modules.md.contract.md)
- [`contracts/module_schemas.md.contract.md`](./contracts/module_schemas.md.contract.md)
- [`quickstart.md`](./quickstart.md)

## Post-Design Constitution Check

> 重新评估 Phase 1 设计后是否引入新的宪法冲突。

| 宪法条款 | Phase 1 后的再评估 | 结论 |
|---|---|---|
| 第 I 条 / 第 III 条 | `data-model.md` 中所有 schema 的 `Python 类型签名` 小节只允许引用 LangChain / LangGraph 原生类型（`BaseChatModel` / `BaseMessage` / `CompiledStateGraph` / `StateGraph` 等），不引用 LangSmith。 | ✅ Pass |
| 第 VI 条 | `data-model.md` 中 `AgentState` schema 显式给出 5 字段 reducer，与宪法第 VI 条 2 款对齐。 | ✅ Pass |
| 第 IX 条 | `data-model.md` 中 `Span / Trace` / `MetricsSnapshot` / `AuditEntry` / `EvalReport` / `DoctorReport` schema 字段与第 IX 条 5 项子能力一一对应。 | ✅ Pass |
| 第 X 条 | `contracts/*.contract.md` 显式约束"不得出现硬编码 API key / 内网 IP / 绝对路径"。 | ✅ Pass |
| 第 XII 条 | `data-model.md` 中 `RuntimeConfig` schema 字段含 `cli_args` / `env_vars` / `dotenv_values` / `builtin_defaults` 4 字段，体现优先级链；`Span / Trace` schema 字段含 7 个宪法要求的字段。 | ✅ Pass |
| **Q10 退出码表多阶段映射** | `contracts/workflow.md.contract.md` §WC-2.4 已按多阶段映射落盘（代码 2 → `dir_load / config_resolve`、代码 3 → `config_resolve / main_loop`、代码 4 → `dir_load / exit_cleanup`、代码 130 → 所有阶段）；`research.md` R-3 退出码溯源表同步；总行数仍 = 12，每个退出码对应恰好 1 行——不与宪法任何条款冲突。 | ✅ Pass |

**结论**：Phase 1 设计未引入新的宪法冲突。

## Complexity Tracking

> **本 Feature 无任何宪法违规需说明**——14 条宪法条款全部通过，未触发 Complexity Tracking 表格填写。

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _（无）_ | _（无）_ | _（无）_ |

## 本轮 /speckit.plan 重入修复（2026-09-15）

> 本 plan 由 `/speckit.plan` 重入命令修订；针对 2026-09-15 /speckit.specify 重入追加的 4 处 spec 修订（Q11 + Q12 + FR-043 (a) + E-2 v0.1.0 + E-5）完成 plan 内部字面同步；并核对 7 个下游产物（research.md / data-model.md / 3 份 contracts/ / quickstart.md / tasks.md / checklists/）的传播结果。

| # | spec 修订 | plan 修订 | 下游产物传播结果 |
|---|---|---|---|
| **B1** | spec.md L26-27 新增 Q11 + Q12 共 2 条 Clarification | L131-132 段（254 行 → 260 行；10 条 → 12 条 Clarifications） / L134 heading / L136 行号引用（spec L16-25 → spec L16-27） / L147 后追加 Q11 + Q12 行 / L186 "10 轮" → "12 轮" | 详见下方"传播核对"表 |
| **B2** | spec.md L179-182 FR-043 占位词清单新增 `...此处略` + 新增 (a) 扩展占位子条款 | L131-132 段（4 项 spec 缺陷修补 B2 项） | `contracts/module_schemas.md.contract.md` MC-2.3 新增"扩展接口约定"约定段（FR-043 (a) 路径 1 落盘形式）；详见下方传播核对 |
| **B3** | spec.md L93 E-2 末尾新增 `v0.1.0 处理` 二级要点（来自 Q12） | L131-132 段（4 项 spec 缺陷修补 B3 项） | `data-model.md` 22 个类型 schema_version 字段均为 `v0.1.0`、均无 migrators 字段——与 E-2 v0.1.0 省略规则字面一致；无需修改 |
| **B4** | spec.md L96 E-5 硬编码模式清单对齐 SC-004（新增 `/home/<user>/...` / `C:\...` / `10.x.x.x` / `172.16-31.x.x` / `OPENAI_API_KEY=sk-...`），删除误写 `SC-004 / SC-005` 中的 `/ SC-005` | L131-132 段（4 项 spec 缺陷修补 B4 项） | `contracts/workflow.md.contract.md` WC-1.9 占位词清单已含 `...此处略`；SC-005 grep 正则未含 `...此处略` 故不动；其余 2 份 contracts 的 AC-1.7 / MC-1.7 占位词清单与 SC-005 grep 正则字面对齐，无须扩 `...此处略` |

### 传播核对（2026-09-15 重入）

| 下游产物 | 是否需修改 | 核对依据 |
|---|---|---|
| `research.md`（207 行）| ❌ 无需修改 | research.md R-1..R-5 不承载 Q11/Q12 直接内容；FR-043 (a) extensibility 路径属实施细节，不影响 R 章决策；E-2 v0.1.0 省略规则与 R-2 / R-3 字面兼容；E-5 模式清单属 SC-004 范围、不在 research.md 中 |
| `data-model.md`（855 行）| ❌ 无需修改 | DM-2 全部 22 个类型 schema_version 字段均为 `v0.1.0`、均无 migrators 字段——与 E-2 / Q12 字面一致；DM-2.13 EvalTaskSpec `grader` 字段类型 `str`（不限定枚举）、DM-2.17 AuditEntry `category` 字段类型 `str`（不限定枚举）——module_schemas.md 实施者可按 FR-043 (a) 路径 2 直接列出 5 / 4 个枚举字面量，无需 data-model.md 改动 |
| `contracts/workflow.md.contract.md`（161 行）| ❌ 无需修改 | WC-1.9 占位词清单已含 `...此处略`（与 FR-043 主条款字面一致）；WC-1.6 / WC-1.7 / WC-1.8 / WC-2.* 不涉及 E-5 / FR-043 (a) 内容 |
| `contracts/architecture_modules.md.contract.md`（114 行）| ❌ 无需修改 | AC-1.7 占位词清单未列 `...此处略`，但 SC-005 grep 正则亦未含 `...此处略`——AC-1.7 与 SC-005 字面对齐；AC-2.* 不涉及 FR-043 (a) / E-2 / E-5 |
| `contracts/module_schemas.md.contract.md`（113 行）| ✅ **需新增 1 段约定**：MC-2.3 末尾追加"扩展接口约定"约定段，明示 Q11 / FR-043 (a) 路径 1 落盘形式 | FR-043 (a) 路径 1 明示"在 schema 一级章节末尾追加'扩展接口约定'二级小节"；须在 contract 中固化此结构约束，否则实施者可能仅选路径 2 与 tasks.md T044 / T048 警示不一致；本次同步修订 |
| `quickstart.md`（255 行）| ❌ 无需修改 | quickstart.md 约束 review 流程与机械脚本；不涉及 Q11 / Q12 / FR-043 (a) / E-2 v0.1.0 / E-5 内容 |
| `tasks.md`（322 行）| ❌ 无需修改 | T044 (L182) / T048 (L186) 已含"⚠️ 警示：实施者不得保留 `...` 字面量；如需表达'未来扩展'应在该章节末尾以'扩展接口约定'小节单独列出 `grader_extensibility` / `category_extensibility` 字段而非用 `...` 占位"——与 Q11 / FR-043 (a) 字面一致；T032 等 AgentState reducer 任务不受 E-2 v0.1.0 影响 |
| `checklists/requirements.md`（spec 阶段产出）| ❌ 无需修改 | checklist 仅核验 spec FR / SC 是否实现；spec 已修订，checklist 字面与 FR-043 主条款一致 |

> **结论**：本轮 plan 重入共触发 **1 处下游产物同步修订**（`contracts/module_schemas.md.contract.md` §MC-2.3 新增"扩展接口约定"约定段）；其余 7 个下游产物（research.md / data-model.md / 2 份 contracts/architecture_modules.md.contract.md 与 contracts/workflow.md.contract.md / quickstart.md / tasks.md / checklists/requirements.md）与 spec 当前状态（含 Q11 + Q12 + FR-043 (a) + E-2 v0.1.0 + E-5）已字面对齐，无需修改。

## 本轮 /speckit.plan 重入修复（2026-09-15, 第 2 次）

> 本 plan 由 `/speckit.plan` 重入命令修订；针对 2026-09-15 /speckit.specify 第 4 次重入追加的 2 处 spec 修订（C1：OOS-N 前缀统一 + C2：OOS-3 第 VIII 条锚定句）完成 plan 内部字面同步；并核对 7 个下游产物的传播结果。

| # | spec 修订 | plan 修订 | 下游产物传播结果 |
|---|---|---|---|
| **C1** | spec.md L249-260 Out of Scope 小节 `O-1..O-12` 前缀统一为 `OOS-1..OOS-12`（消除与 plan.md / tasks.md 既有 `OOS-N` 引用不一致） | L44 / L60 / L128 原本即用 `OOS-N`，无字面修改；L132 "4 项 spec 缺陷修补" → "6 项" 并细化条目（含 ⑤ C1 + ⑥ C2） | 详见下方"传播核对"表 |
| **C2** | spec.md L251 OOS-3 行内追加 1 句锚定宪法第 VIII 条（"测试驱动开发" 语义范围限定于 "产生可执行代码的功能开发"；Feature 00 仅产出 Markdown 设计文档、不产生可执行代码，故第 VIII 条不触发） | L67 Constitution Check 第 VIII 条评注修订——原本 plan.md 独有"本 Feature 期间不写任何测试用例；TDD 刚性约束待 Feature 01-10+ 涉及运行时代码时再触发"短评注，现改为"详见 [spec.md OOS-3 行内锚定句](./spec.md)"指针 + 简短摘要；消除宪法对齐候选（避免后续 /speckit.analyze 重入再次将本项判为宪法对齐候选） | 详见下方"传播核对"表 |

### 传播核对（2026-09-15 第 2 次重入）

| 下游产物 | 是否需修改 | 核对依据 |
|---|---|---|
| `spec.md`（260 行）| ✅ **本轮 spec 修订主体** | L249-260 12 处 `O-N` → `OOS-N`；L251 OOS-3 行内追加第 VIII 条锚定句（行数仍 = 260） |
| `research.md`（207 行）| ❌ 无需修改 | research.md 不承载 OOS 编号；不涉及第 VIII 条评注（research.md 是 Phase 0 调研产物，作用域为 19 schema 字段细节 / 6 阶段 4 子命令蓝图 / 5 层初始 module_id 候选 / MDA 对照表下界 / 静态 CI 清单下界） |
| `data-model.md`（855 行）| ❌ 无需修改 | data-model.md 承载 19 schema 字段级定义，不承载 OOS 编号 / 宪法评注 |
| `contracts/workflow.md.contract.md`（161 行）| ❌ 无需修改 | 不涉及 OOS 编号 / 宪法第 VIII 条 |
| `contracts/architecture_modules.md.contract.md`（114 行）| ❌ 无需修改 | 不涉及 OOS 编号 / 宪法第 VIII 条 |
| `contracts/module_schemas.md.contract.md`（113 行）| ❌ 无需修改 | 不涉及 OOS 编号 / 宪法第 VIII 条 |
| `quickstart.md`（255 行）| ❌ 无需修改 | quickstart.md 约束 review 流程与机械脚本；不涉及 OOS 编号 / 宪法第 VIII 条 |
| `tasks.md`（358 行）| ❌ 无需修改 | tasks.md L16 / L284 已用 `OOS-N` 形式（C1 修复正好对齐 tasks.md 既有用法）；L16 已含"宪法第 VIII 条 TDD 约束待 Feature 01-10+ 涉及运行时代码时触发"与 C2 锚定句语义一致——tasks.md 不需同步修订 |
| `checklists/requirements.md`（spec 阶段产出）| ❌ 无需修改 | checklist 仅核验 spec FR / SC 是否实现；不涉及 OOS 编号 / 宪法第 VIII 条 |

> **结论**：本轮 plan 重入共触发 **3 处 plan.md 内部字面同步**（① L67 Constitution Check 第 VIII 条评注改为引用 spec.md OOS-3 锚定句指针；② L132 spec 修补清单由 4 项扩为 6 项并细化 6 个条目；③ 新增本节记录 C1 + C2 修订及传播核对）；其余 8 个产物（spec.md 自身 + 7 个下游产物）与 spec 当前状态（含 C1 + C2）已字面对齐或语义一致，无需修改。
>
> **后续 spec 修订**（2026-09-15 /speckit.specify 第 4 次重入后）：无新 spec 修订；spec L260 已是最新状态（含 Q1-Q12 + 8 项精修 + 4 项 analyze 缺陷修补 + Q11/Q12 + FR-043 (a) + E-2 v0.1.0 + E-5 + OOS-N 统一 + OOS-3 第 VIII 条锚定）。本 plan 可直接进入 `/speckit.tasks`（tasks.md 已落盘，包含本轮所有 spec / plan 修订的传播核对）。

## Phase 2: Tasks（不在本 plan 范围）

> Phase 2 由 `/speckit.tasks` 命令产出 `tasks.md`（在 `specs/000-top-level-design/` 下），本 plan 不创建该文件。

预计 tasks.md 的最小任务集（供后续 `/speckit.tasks` 参考）：
1. T-01 在 `harness/top_level_design/` 创建 `workflow.md`（按 `contracts/workflow.md.contract.md` 落盘 6 阶段 + 4 CLI 子命令 + 12 退出码 + N 日志标签 + MDA 对照表）。
2. T-02 在 `harness/top_level_design/` 创建 `architecture_modules.md`（按 `contracts/architecture_modules.md.contract.md` 落盘 5 层 + N 模块 + 完整对称依赖矩阵 + Feature 拆分映射 + 静态约束清单）。
3. T-03 在 `harness/top_level_design/` 创建 `module_schemas.md`（按 `contracts/module_schemas.md.contract.md` 落盘 19 个一级章节，按 `data-model.md` 填字段）。
4. T-04 项目维护者按 `quickstart.md` 跑机械脚本 + 人工 review，逐条核验 `specs/000-top-level-design/checklists/requirements.md` 段 2。
5. T-05 若 review 不通过，迭代修订 3 份文档直至 review 通过；若通过，进入 Feature 01-10+ 的 spec 阶段。

> 上述 5 条任务仅为占位说明；具体 TDD 红绿重构任务拆解由 `/speckit.tasks` 完成。

## 本轮 /speckit.plan 重入修复（2026-09-14）

> 本 plan 由 `/speckit.plan` 重入命令修订；针对 5 项缺陷（A1 / A2 / A3 / A6 / A10）完成以下 6 处同步修订；其余下游产物（research.md / data-model.md / 2 份 `contracts/*.contract.md` / quickstart.md / tasks.md）经核对已与 spec 当前状态（含 Q10）字面对齐，无需二次修改。

| # | 缺陷 | 修订位置 | 修订内容 |
|---|---|---|---|
| **A1** | spec.md 已追加 Q10（254 行），plan 仍写 "253 行" + "9 条 Clarifications（Q1–Q9）" | L131 | "253 行" → "254 行"；"9 条 Clarifications（Q1–Q9）" → "10 条 Clarifications（Q1–Q10）"；并标注 Q10 来源为 /speckit.specify 重入追加（修复缺陷 A9）。 |
| **A2** | Technical Context 段 L42-43 未显式包含 FR-013 / Q10 约束 | L42-43 (Constraints 段) | 追加 1 条约束："FR-013 退出码表的'触发阶段'列允许多阶段映射（Q10）：多阶段以 `/` 分隔或'所有阶段'统称；总行数仍严格 = 12，每个退出码对应恰好 1 行"。 |
| **A3** | "9 条 Clarifications 在本 plan 中的体现" 表格缺 Q10 row，且行号引用 `spec L12-24` 已下移 | L133-145 | heading "9 条" → "10 条"；行号引用 `spec L12-24` → `spec L16-25`（因 Q10 已追加至 L25）；新增 Q10 row，体现位置 = Technical Context Constraints 段 / `contracts/workflow.md.contract.md` §WC-2.4 / Post-Design Constitution Check。 |
| **A6** | "后续 spec 修订" 段开头 "3 处缺陷" 与下方列举 4 处缺陷字面漂移 | L164 | "3 处算术 / 规则 / ID 缺陷" → "3 处主缺陷（算术 / 规则 / ID）+ 1 处后续修补（FR-033 计数描述）"，与下方 4 条缺陷列举字面对齐。 |
| **A10** | Post-Design Constitution Check 5 行未显式包含 Q10 影响评注 | L218-222 | 表格末尾新增 1 行：`Q10 退出码表多阶段映射 → contracts/workflow.md.contract.md §WC-2.4 + research.md R-3 已按多阶段映射落盘（代码 2 / 3 / 4 / 130 多阶段）；总行数仍 = 12；不与宪法任何条款冲突 → ✅ Pass`。 |
| **—** | Phase 0 调研目标段 L186 措辞 "9 轮 clarify" 与 spec 现状（10 轮）不一致 | L186 | "spec 中**已通过 9 轮 clarify 解决的所有歧义之外**" → "spec 中**已通过 10 轮 clarify 解决的所有歧义之外**"。 |

> **传播核对**：本次 6 处 plan.md 字面同步触发以下下游产物核对——
>
> | 下游产物 | 是否需修改 | 核对依据 |
> |---|---|---|
> | `research.md` R-3（退出码溯源表，L124-140）| ❌ 无需修改 | R-3 表已按多阶段映射落盘（代码 2 → `dir_load / config_resolve`、代码 4 → `dir_load / exit_cleanup`、代码 130 → 所有阶段），与 Q10 字面一致。 |
> | `contracts/workflow.md.contract.md` §WC-2.4（退出码表，L99-118）| ❌ 无需修改 | WC-2.4 已按多阶段映射落盘（代码 2 → `dir_load / config_resolve`、代码 3 → `config_resolve / main_loop`、代码 4 → `dir_load / exit_cleanup`、代码 130 → 所有阶段），与 Q10 字面一致；FR-013 字面量与 Q10 兼容。 |
> | `data-model.md`（855 行）| ❌ 无需修改 | data-model.md 不承载 FR-013 退出码表内容，仅承载 19 个 schema 字段级定义；FR-013 的影响面在 workflow.md 与其 contract，与 data-model.md 无交叉。 |
> | `contracts/architecture_modules.md.contract.md`（114 行）| ❌ 无需修改 | 不涉及退出码表，仅约束模块 / 矩阵 / 拆分映射 / CI 清单。 |
> | `contracts/module_schemas.md.contract.md`（113 行）| ❌ 无需修改 | 不涉及退出码表，仅约束 19 个 schema 的章节结构与字段引用。 |
> | `quickstart.md`（255 行）| ❌ 无需修改 | 不涉及退出码表的内容生成，仅约束 review 流程与机械脚本。 |
> | `tasks.md`（289 行）| ❌ 无需修改 | tasks.md 已在 L39 "Spec 演化说明" 章节记录 /speckit.specify 重入 4 处缺陷 + Q10 的下游传播；本轮 plan 修复不影响 tasks.md 任何任务结构（tasks.md 中 FR-013 引用在 T011 处与 Q10 兼容）。 |
>
> **结论**：6 处 plan.md 字面同步全部为"plan 内部与 spec 当前状态的字面对齐"，不引入新的设计变更；与 spec.md / checklist.md / data-model.md / 3 份 contract / quickstart.md / tasks.md 全部下游产物一致。
>
> **后续 spec 修订**（2026-09-14 /speckit.plan 重入后）：无新 spec 修订；spec L254 已是最新状态（含 Q10 + 8 项精修 + 4 项 analyze 缺陷修补）。本 plan 可直接进入 `/speckit.tasks`（tasks.md 已落盘，包含本轮所有 spec / plan 修订的传播核对）。
