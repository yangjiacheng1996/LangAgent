# Contract: `workflow.md`

**Owner**: Feature 00 — 顶层设计
**Source Spec**: [spec.md](../spec.md) FR-001..FR-016, FR-040..FR-043
**Source Plan**: [plan.md](../plan.md) §Phase 1
**Source Research**: [research.md](../research.md) R-1.1 / R-3 / R-4 / R-5

> 本文件是 `harness/top_level_design/workflow.md` 的格式合同。`workflow.md` 落盘时，结构与小节顺序必须严格符合本契约。

## WC-1 文件级约束

| 编号 | 约束 | 验证方式 |
|---|---|---|
| WC-1.1 | 路径：`harness/top_level_design/workflow.md`（与本 spec.md 同样位于仓库根的相对路径）| `ls` |
| WC-1.2 | 行数 ≥ 200（FR-002 / SC-001）| `wc -l` |
| WC-1.3 | 字符编码 UTF-8；行尾 LF；无 BOM（FR-003）| `file` + `hexdump` |
| WC-1.4 | 文件名严格 `workflow.md`（全小写、下划线分隔、`md` 后缀）| `ls` |
| WC-1.5 | 不得出现 `langsmith` / `LANGSMITH_API_KEY=` / `LANGCHAIN_TRACING_V2` / `LANGCHAIN_API_KEY` / `LANGCHAIN_ENDPOINT` 字面量（FR-051）| `grep -wE` |
| WC-1.6 | 不得出现 `/Users/...` / `/home/<user>/...` / `C:\...`（FR-052）| `grep -E` |
| WC-1.7 | 不得出现 `192.168.x.x` / `10.x.x.x` / `172.(1[6-9]\|2[0-9]\|3[01]).x.x`（FR-052）| `grep -E` |
| WC-1.8 | 不得出现 `sk-...` / `LANGSMITH_API_KEY=sk-` / `OPENAI_API_KEY=sk-`（FR-052）| `grep -E` |
| WC-1.9 | 不得出现 `TODO` / `TBD` / `FIXME` / `XXX` / `留待决定` / `待定` / `占位` / `...此处略`（FR-043 / SC-005）| `grep -wE` |
| WC-1.10 | 末尾必须包含"变更日志"小节，至少 1 条记录（FR-061）| `grep -E '^## 变更日志'` |

## WC-2 必备小节（按顺序）

```
# workflow.md
├── ## 文档元信息（FR-010）                                # WC-2.1
├── ## 用户视角：CLI 生命周期（FR-011）                    # WC-2.2
│   ├── ### `langagent init <name>`（FR-011 子命令 1）
│   ├── ### `langagent run [agent-dir]`（FR-011 子命令 2）
│   ├── ### `langagent eval [agent-dir]`（FR-011 子命令 3）
│   └── ### `langagent doctor`（FR-011 子命令 4）
├── ## 系统视角：6 阶段（FR-012）                          # WC-2.3
│   ├── ### `dir_load` {#stage-dir_load}（FR-012 + Q6 显式锚点）
│   ├── ### `config_resolve` {#stage-config_resolve}
│   ├── ### `model_adapt` {#stage-model_adapt}
│   ├── ### `graph_compose` {#stage-graph_compose}
│   ├── ### `main_loop` {#stage-main_loop}
│   └── ### `exit_cleanup` {#stage-exit_cleanup}
├── ## 退出码表（FR-013）                                  # WC-2.4
├── ## 日志标签表（FR-014）                                # WC-2.5
├── ## MDA 能力对照表（FR-015）                            # WC-2.6
├── ## 交叉引用（FR-040..FR-043）                          # WC-2.7
└── ## 变更日志（FR-061）                                  # WC-2.8
```

## WC-2.1 文档元信息（FR-010）

```yaml
---
doc_id: workflow
version: v0.1.0
last_updated: 2026-09-14
constitution_ref: .specify/memory/constitution.md
related_docs:
  - architecture_modules.md
  - module_schemas.md
---
```

| 字段 | 必填 | 格式 |
|---|---|---|
| `doc_id` | * | 字符串 `workflow` |
| `version` | * | `v\d+\.\d+\.\d+` |
| `last_updated` | * | `YYYY-MM-DD` |
| `constitution_ref` | * | 相对路径 |
| `related_docs` | * | 相对路径列表 |

## WC-2.2 用户视角：CLI 生命周期（FR-011）

4 个子命令，每个子命令必须给出 5 栏：`输入` / `输出` / `失败模式` / `退出码` / `日志标签`。

| 子命令 | 必填项数（每栏） | 必填退出码 |
|---|---|---|
| `langagent init <name>` | ≥ 5 | 0 / 1 / 2 / 64 / 65 / 66 / 70 / 78 / 130（按 R-4 建议）|
| `langagent run [agent-dir]` | ≥ 5 | 0 / 1 / 2 / 4 / 70 / 78 / 130 |
| `langagent eval [agent-dir]` | ≥ 3 | 0 / 1 / 70 / 78 / 130 |
| `langagent doctor` | ≥ 5 | 0 / 1 / 2 / 78 / 130 |

> 不为 `version` / `tui` / `serve` / `clean` 等辅助子命令预留接口（Q5 澄清）。

## WC-2.3 系统视角：6 阶段（FR-012 / Q6）

6 阶段，每阶段 5 栏： `输入` / `输出` / `失败模式` / `退出码` / `日志标签`；每栏 ≥ 3 项（research R-4 下界）。

| 阶段 | 锚点（`#stage-*`，Q6 显式形式）| 必填退出码 |
|---|---|---|
| `dir_load` | `#stage-dir_load` | 0 / 1 / 2 / 4 / 64 / 66 / 78 / 130 |
| `config_resolve` | `#stage-config_resolve` | 0 / 1 / 2 / 5 / 64 / 65 / 78 / 130 |
| `model_adapt` | `#stage-model_adapt` | 0 / 1 / 70 / 78 / 130 |
| `graph_compose` | `#stage-graph_compose` | 0 / 1 / 70 / 78 / 130 |
| `main_loop` | `#stage-main_loop` | 0 / 1 / 70 / 130 |
| `exit_cleanup` | `#stage-exit_cleanup` | 0 / 1 / 4 / 130 |

> 每阶段必须以 `### <stage_name> {#stage-<stage_name>}` 显式锚点形式书写，**禁止依赖 Markdown 自动生成**（FR-016 / Q6）。

## WC-2.4 退出码表（FR-013）

严格 12 行，列：`退出码` / `含义` / `触发阶段`。

| 退出码 | 含义（spec Q4 锁定）| 触发阶段 |
|---|---|---|
| 0 | 成功 | 所有阶段 |
| 1 | 通用失败 | 所有阶段 |
| 2 | 用法错误（shell 惯例）| `dir_load` / `config_resolve` |
| 3 | 数据错误（自定义）| `config_resolve` / `main_loop` |
| 4 | I/O 错误（自定义）| `dir_load` / `exit_cleanup` |
| 5 | 配置错误（自定义）| `config_resolve` |
| 64 | `EX_USAGE`（sysexits.h）| `dir_load` |
| 65 | `EX_DATAERR`（sysexits.h）| `config_resolve` |
| 66 | `EX_NOINPUT`（sysexits.h）| `dir_load` |
| 70 | `EX_SOFTWARE`（sysexits.h）| `main_loop` |
| 78 | `EX_CONFIG`（sysexits.h）| `config_resolve` |
| 130 | SIGINT（128+2）| 所有阶段 |

每个退出码须有显式锚点：`#exit-code-<n>`（FR-016 / FR-041）。

## WC-2.5 日志标签表（FR-014）

每行： `日志标签` / `含义` / `触发阶段`。**最少 15 行**（research R-5 下界），前缀 `la.`。

每行须有显式锚点：`#log-tag-<la.xx.yy.zz>`（点号替换为短横线，FR-016 / FR-041）。

## WC-2.6 MDA 能力对照表（FR-015 / R-1.2）

**最少 10 行**，每行 4 列：`mda_capability` / `mda_source_path` / `langagent_equivalent_stage` / `notes`。

`mda_source_path` 必须为 `harness/Managed_deep_agents/langsmith/python/<file>.md` 形式的相对路径。`langagent_equivalent_stage` 取值限于 6 阶段之一；`notes` 列允许"v1 占位" / "本项目剥离"等显式标注。

## WC-2.7 交叉引用（FR-040..FR-043）

- 引用 `architecture_modules.md` 时使用相对路径 `architecture_modules.md#mod-<module-id>`。
- 引用 `module_schemas.md` 时使用相对路径 `module_schemas.md#schema-<schema-id>`。
- 不带 `./` 前缀、不带 `../` 前缀。
- 锚点形式严格符合 FR-041 命名空间（`#stage-*` / `#mod-*` / `#schema-*` / `#exit-code-*` / `#log-tag-*`）。
- 任何引用必须能机械核验（SC-002 无死链）。

## WC-2.8 变更日志（FR-061）

```markdown
## 变更日志

| 日期 | 版本 | 修订摘要 | 作者 |
| --- | --- | --- | --- |
| 2026-09-14 | v0.1.0 | Feature 00 初版 | 项目维护者 |
```

## WC-3 风格约束

- 文档语言：中文（章节标题、叙述、表格文字、注释）。
- 代码示例、类型名、字段名：英文。
- ID / 锚点：蛇形小写 / 短横线 kebab-case（Q3 澄清）。
- 阶段名、退出码、日志标签、模块 ID、schema ID：英文蛇形（FR-021 / FR-022 / FR-032 / FR-041）。
- 章节标题：英文 PascalCase + 中文释义（如 `### dir_load {#stage-dir_load}（目录加载）`）。
- 不得使用 `<待本 Feature 实施时填充>` 之类的占位表述（FR-043）；如某栏确实不适用，注明"此处不适用，因为 ..."并给出理由。

## WC-4 验收清单

实施者交付时，须保证本契约 4 节（WC-1..WC-3）所有约束项均通过机械或人工 review。具体核验步骤见 [`quickstart.md`](../quickstart.md)。
