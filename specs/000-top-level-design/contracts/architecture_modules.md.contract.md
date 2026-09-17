# Contract: `architecture_modules.md`

**Owner**: Feature 00 — 顶层设计
**Source Spec**: [spec.md](../spec.md) FR-001..FR-003, FR-020..FR-026, FR-040..FR-043
**Source Plan**: [plan.md](../plan.md) §Phase 1
**Source Research**: [research.md](../research.md) R-1.1 / R-1.3 / R-4

> 本文件是 `harness/top_level_design/architecture_modules.md` 的格式合同。`architecture_modules.md` 落盘时，结构与小节顺序必须严格符合本契约。

## AC-1 文件级约束

| 编号 | 约束 | 验证方式 |
|---|---|---|
| AC-1.1 | 路径：`harness/top_level_design/architecture_modules.md` | `ls` |
| AC-1.2 | 行数 ≥ 200（FR-002 / SC-001）| `wc -l` |
| AC-1.3 | 字符编码 UTF-8；行尾 LF；无 BOM（FR-003）| `file` + `hexdump` |
| AC-1.4 | 文件名严格 `architecture_modules.md` | `ls` |
| AC-1.5 | 不得出现 `langsmith` / `LANGSMITH_API_KEY=` 等（FR-051）| `grep -wE` |
| AC-1.6 | 不得出现绝对路径 / 内网 IP / 硬编码密钥（FR-052）| `grep -E` |
| AC-1.7 | 不得出现 `TODO` / `TBD` / `FIXME` / `XXX` / `留待决定` / `待定` / `占位`（FR-043 / SC-005）| `grep -wE` |
| AC-1.8 | 末尾必须包含"变更日志"小节（FR-061）| `grep -E '^## 变更日志'` |

## AC-2 必备小节（按顺序）

```
# architecture_modules.md
├── ## 文档元信息（FR-020）                              # AC-2.1
├── ## 5 层架构总览（FR-021）                            # AC-2.2
│   ├── ### `cli` 层
│   ├── ### `runtime` 层
│   ├── ### `protocol` 层
│   ├── ### `cross_cutting` 层
│   └── ### `primitives` 层
├── ## 模块清单（FR-022）                                # AC-2.3
│   ├── ### 模块 1（任一层）
│   ├── ### 模块 2
│   ├── ...（≥ 12 个模块，每层 ≥ 2 个，research R-1.3 下界）
│   └── ### 模块 N
├── ## 模块间依赖矩阵（FR-023）                          # AC-2.4
├── ## 模块到 Feature 拆分映射表（FR-024）                # AC-2.5
├── ## 静态约束 CI 校验清单（FR-025）                    # AC-2.6
├── ## 交叉引用（FR-040..FR-043）                        # AC-2.7
└── ## 变更日志（FR-061）                                # AC-2.8
```

## AC-2.1 文档元信息（FR-020）

字段集合同 `workflow.md` 契约 WC-2.1，但 `doc_id` 必须为 `architecture_modules`。

## AC-2.2 5 层架构总览（FR-021）

5 层，**英文蛇形**严格为 `cli` / `runtime` / `protocol` / `cross_cutting` / `primitives`。

每层一级章节下挂"职责概述"二级小节（≥ 3 项）说明本层的关注点。

## AC-2.3 模块清单（FR-022 / Q8 / R-1.3）

每层下挂 ≥ 2 个模块（research R-1.3 下界）；总模块数 ≥ 12。

每个模块一级章节下挂 4 栏：
- `职责`（≥ 2 项）
- `关键 API`（≥ 1 项）
- `允许的依赖方向`（≥ 1 项）
- `禁止的依赖方向`（≥ 1 项）

每个模块必须有**显式锚点** `### <module_id> {#mod-<module-id>}`，其中 `<module-id>` 为英文蛇形小写且**在 5 层之间全局唯一**（Q8 澄清）。

## AC-2.4 模块间依赖矩阵（FR-023 / Q7）

完整对称方阵，行列均为 module_id。单元格从 4 符号中选取：

| 符号 | 语义 |
|---|---|
| `→` | 强单向允许依赖（行可调列，反之不可）|
| `↔` | 双向允许依赖（互为接口）|
| `×` | 明确禁止依赖 |
| `–` | 无依赖关系（默认；对角线亦为 `–`）|

**每行每列每个单元格必须填满一个符号**（不留空白、不留 NA）。`→` 与 `↔` 的边集合必须无回路（机械：构造有向图跑拓扑排序）。

## AC-2.5 模块到 Feature 拆分映射表（FR-024）

每行 4 列：`module_id` / `feature_id`（`F01`..`F10+`）/ `职责` / `依赖的下游模块`。`feature_id` 列**不得**出现 `F00`。

## AC-2.6 静态约束 CI 校验清单（FR-025 / R-1.2）

**最少 12 条**（research R-1.2 下界）。每条以 `- ID: CHK-AR-NNN | 约束描述 | 实现方式（grep / ripgrep / AST）` 形式书写。实现方式列不得包含"人工"二字。

必须覆盖：
- 3 条文档存在性 / 行数 / 字符编码（`wc -l` / `file` / `hexdump`）。
- 3 条锚点命名空间（grep `#stage-*` / `#mod-*` / `#schema-*` / `#exit-code-*` / `#log-tag-*`）。
- 2 条依赖矩阵（grep 4 符号 + 拓扑排序）。
- 2 条 module_id 全局唯一性（`grep -oE 'module_id = .*' | sort -u | uniq -d`）。
- 2 条与宪法一致性（`grep -E 'langsmith|LANGSMITH_|LANGCHAIN_TRACING'` 不得出现）。

## AC-2.7 交叉引用（FR-040..FR-043）

- 引用 `workflow.md`：`workflow.md#stage-<stage-id>`。
- 引用 `module_schemas.md`：`module_schemas.md#schema-<schema-id>`。
- 锚点命名空间严格符合 FR-041。

## AC-2.8 变更日志（FR-061）

同 `workflow.md` 契约 WC-2.8。

## AC-3 风格约束

同 `workflow.md` 契约 WC-3。补充：
- 5 层名（`cli` / `runtime` / `protocol` / `cross_cutting` / `primitives`）严格英文蛇形小写。
- module_id 严格英文蛇形小写，全局唯一（Q8 澄清）。

## AC-4 验收清单

实施者交付时，须保证本契约 4 节（AC-1..AC-3）所有约束项均通过机械或人工 review。具体核验步骤见 [`quickstart.md`](../quickstart.md)。
