# Contract: `module_schemas.md`

**Owner**: Feature 00 — 顶层设计
**Source Spec**: [spec.md](../spec.md) FR-001..FR-003, FR-030..FR-037, FR-040..FR-043
**Source Plan**: [plan.md](../plan.md) §Phase 1
**Source Research**: [research.md](../research.md) R-1.1 / R-1.2 / R-2 / R-4
**Source Data Model**: [data-model.md](../data-model.md) DM-1..DM-5

> 本文件是 `harness/top_level_design/module_schemas.md` 的格式合同。`module_schemas.md` 落盘时，结构与小节顺序必须严格符合本契约。

## MC-1 文件级约束

| 编号 | 约束 | 验证方式 |
|---|---|---|
| MC-1.1 | 路径：`harness/top_level_design/module_schemas.md` | `ls` |
| MC-1.2 | 行数 ≥ 200（FR-002 / SC-001）| `wc -l` |
| MC-1.3 | 字符编码 UTF-8；行尾 LF；无 BOM（FR-003）| `file` + `hexdump` |
| MC-1.4 | 文件名严格 `module_schemas.md` | `ls` |
| MC-1.5 | 不得出现 `langsmith` / `LANGSMITH_API_KEY=` 等（FR-051）| `grep -wE` |
| MC-1.6 | 不得出现绝对路径 / 内网 IP / 硬编码密钥（FR-052）| `grep -E` |
| MC-1.7 | 不得出现 `TODO` / `TBD` / `FIXME` / `XXX` / `留待决定` / `待定` / `占位`（FR-043 / SC-005）| `grep -wE` |
| MC-1.8 | 末尾必须包含"变更日志"小节（FR-061）| `grep -E '^## 变更日志'` |

## MC-2 必备小节（按顺序）

```
# module_schemas.md
├── ## 文档元信息（FR-030）                                # MC-2.1
├── ## Schema 总目录（FR-031）                             # MC-2.2
├── ## 19 个一级章节（FR-032）                             # MC-2.3
│   ├── ### AgentState
│   ├── ### RuntimeConfig
│   ├── ### LoadedAgent
│   ├── ### SkillSpec / SkillFrontmatter（合并章节）       # FR-033 / Q9
│   ├── ### ToolSpec / ToolSideEffect（合并章节）
│   ├── ### MiddlewareSpec
│   ├── ### ChannelSpec
│   ├── ### ChannelContext
│   ├── ### SandboxSpec
│   ├── ### ScheduleSpec
│   ├── ### MemorySpec
│   ├── ### IdentitySpec
│   ├── ### EvalTaskSpec
│   ├── ### Span / Trace（合并章节）
│   ├── ### Event
│   ├── ### MetricsSnapshot
│   ├── ### AuditEntry
│   ├── ### DoctorReport
│   └── ### EvalReport
├── ## 交叉引用（FR-040..FR-043）                          # MC-2.4
└── ## 变更日志（FR-061）                                  # MC-2.5
```

## MC-2.1 文档元信息（FR-030）

字段集合同 `workflow.md` 契约 WC-2.1，但 `doc_id` 必须为 `module_schemas`。

## MC-2.2 Schema 总目录（FR-031）

表格列出全部 19 个一级章节。每行 5 列：`schema_id` / `python_kind` / `schema_version` / `disk_format` / `承载类型数`（FR-031 修订后）。

**表末必须有合计行**：`合计 — — — — 19 / 22`（FR-031 修订后）。

表内容严格与 `data-model.md` DM-1 一致。

## MC-2.3 19 个一级章节（FR-032 / FR-033 / Q9）

**16 个非合并章节**（每章下挂 4 个二级小节）：

- ### `<SchemaName> {#schema-<schema-id>}`
  - #### `Python 类型签名`
  - #### `磁盘格式与 schema_version`
  - #### `与 LangChain/LangGraph 原生类型映射`
  - #### `reducer 与不可变约束`

**3 个合并章节**（每章下挂 6 个二级小节，Q9 澄清）：

- ### `SkillSpec / SkillFrontmatter {#schema-skill-spec-frontmatter}`
  - #### `Python 类型签名`（共用）
  - #### `磁盘格式与 schema_version`（共用）
  - #### `SkillSpec 与 LangChain/LangGraph 原生类型映射`
  - #### `SkillSpec reducer 与不可变约束`
  - #### `SkillFrontmatter 与 LangChain/LangGraph 原生类型映射`
  - #### `SkillFrontmatter reducer 与不可变约束`

- ### `ToolSpec / ToolSideEffect {#schema-tool-spec-side-effect}`（6 个二级小节，结构同上）
- ### `Span / Trace {#schema-span-trace}`（6 个二级小节，结构同上）

每个一级章节的字段内容**严格与 `data-model.md` DM-2 一致**（允许 Markdown 叙述形式，不要求 verbatim 复制代码块）。

## MC-2.4 交叉引用（FR-040..FR-043）

- 引用 `workflow.md`：`workflow.md#stage-<stage-id>` / `#exit-code-<n>` / `#log-tag-<la.xx.yy.zz>`。
- 引用 `architecture_modules.md`：`architecture_modules.md#mod-<module-id>`。
- 锚点命名空间严格符合 FR-041。

## MC-2.5 变更日志（FR-061）

同 `workflow.md` 契约 WC-2.8。

## MC-2.6 扩展接口约定（FR-043 (a) 路径 1 / Q11）

> 本段是 FR-043 (a) 路径 1 的落盘形式契约。module_schemas.md 中**任一存在枚举 / 字面量候选值集合的字段**（典型如 `EvalTaskSpec.grader`、`AuditEntry.category`）如需表达"未来可能新增的取值"，**推荐**采用本约定。**禁止**使用 `...` / `<其它枚举>` / `etc.` 等省略号占位符（FR-043 / FR-043 (a) / SC-005）。

约定形式：

- 在该字段所属一级章节末尾追加一个 `#### 扩展接口约定` 二级小节（位于 `#### reducer 与不可变约束` 之后）。
- 在该小节内以 `<字段名>_extensibility` 命名约定列出一条字段，类型为 `list[str] = []`，字面量形如：

  ```python
  grader_extensibility:    list[str] = []    # 未来新增的 grader 取值应登记到此字段，禁止以 `...` 占位
  category_extensibility:  list[str] = []    # 未来新增的 category 取值应登记到此字段，禁止以 `...` 占位
  ```

- 该二级小节**不得**包含 `...` 字面量；扩展字段本身**必须**显式列出当前已知的所有枚举字面量（如 `grader: Literal["exact_match", "contains", "regex", "llm_judge", "tool_call_match"]`），且 `extensibility` 字段默认 `[]` 表示"当前无未登记扩展"。

> **fallback**：实施者可改走 FR-043 (a) 路径 2——直接以 `Literal[...]` 枚举所有当前取值，不预留 `extensibility` 字段；如需新增，必须新增 `Literal` 元素并升 schema_version（触发 E-2 的 migrators 规则）。两条路径均不得以 `...` 占位。

## MC-3 风格约束

同 `workflow.md` 契约 WC-3。补充：
- 19 个一级章节标题使用 PascalCase（贴近 LangChain / LangGraph 原生类型名）。
- 16 个单类型章节的 `schema_id` 使用英文蛇形小写，与锚点 `#schema-<schema-id>` 的短横线形式对应。
- 3 个合并章节的锚点形式：
  - `#schema-skill-spec-frontmatter`（承载 SkillSpec + SkillFrontmatter）
  - `#schema-tool-spec-side-effect`（承载 ToolSpec + ToolSideEffect）
  - `#schema-span-trace`（承载 Span + Trace）

## MC-4 验收清单

实施者交付时，须保证本契约 4 节（MC-1..MC-3）所有约束项均通过机械或人工 review。具体核验步骤见 [`quickstart.md`](../quickstart.md)。
