**修订理由（先写一段）**：我相信"没有大局观的程序员，不是优秀的程序员"。top level design
（LangAgent 智能体工作流 / 架构与模块划分 / 模块间交互数据格式 ）承载了
对整个系统的全局视角。任何 feature 的 spec/plan/tasks/implement 一旦脱离这层约束，就会
从单点出发、看不到自己在 LangAgent 全图里的位置、与已有模块的契约冲突，最终造成架构漂移。
因此，顶层设计 MUST 在每个 speckit 阶段开始前被先读、且在交付物中被显式引用。

**新增原则**，Top-Level Design Primacy"（顶层设计优先）。

### Top-Level Design Primacy

LangAgent 的顶层设计是 feature 实施的上游契约。任何 feature 的 speckit 流水线
（`/speckit.specify`、`/speckit.clarify`、`/speckit.plan`、`/speckit.tasks`、
`/speckit.analyze`、`/speckit.implement`）执行人在进入本阶段工作之前，MUST 先顺序读取
`harness/top_level_design/` 目录下的全部五份 artifact，并对该 feature 的设计主张与本 Constitution
的对齐点形成书面化的"对齐清单"，随后方可进入本阶段的实际产出。

强制读取的顶层设计 artefact 清单（顺序即为读取顺序）：

1. `harness/top_level_design/workflow.md` — Agent Loop 端到端业务流。
3. `harness/top_level_design/architecture_modules.md` — 模块拆分、依赖方向、CLI↔module 映射、
   T1/T2/T3 持久化布局、Tool Market、HITL 双轴、与 Constitution 的映射表。
4. `harness/top_level_design/module_schemas.md` — schema 对象的字段约束、JSON Schema literal、
   anti-corruption 规则、命名与版本策略。

约束细则：

- 读取可在阶段开始时完成一次性加载。