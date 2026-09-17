# F04 — Protocol 层 Skill + Tool 加载（protocol_skill_loader + protocol_tool_registry）

> **Feature ID**: F04
> **批次**: 第 5 批（协议层）
> **依赖**: F07（event bus 发 `skill_loaded` / `tool_registered` 事件）/ F08（logger 记加载日志）/ F10（`BaseTool` / `AgentMiddleware` 类型注解）
> **被依赖**: F02（dir_load 调用 loader 扫描子目录）/ F05（main_loop 把 tool 注册到图）
> **状态**: 待启动 speckit.specify（review.md v0.4.0 修复后 v0.4.0；本 feature prompt 已应用 v0.4.0 修复：m-NEW-2 未声明 SIDE_EFFECTS fail-CLOSED + 警告日志；m-NEW-3 args_schema JSON Schema Draft 7；m-NEW-10 tool_id 异常传播路径明确）

---

## 一、Feature 概述

实现 protocol 层 2 个模块：
- **`protocol_skill_loader`**：扫描 `skills/<name>/SKILL.md`，解析 YAML frontmatter，产出 `SkillSpec` 列表。
- **`protocol_tool_registry`**：扫描 `tools/<tool_name>.py`，加载 `BaseTool` 子类，构造 `ToolSpec`（含 `side_effects` 标注）。

Middleware 加载（`middleware/<name>.py` → `MiddlewareSpec` → `AgentMiddleware` 实例）由 F10 在 graph_compose 阶段处理（详见 F10 §3.4a）；F04 仅负责 skills + tools 两个子目录。`MiddlewareSpec` schema 在 module_schemas.md 已定义，由 **F10 拥有**（**评审 s-3 修复后**），F04 仅在 §3.2 引用，不重复实现。

## 二、必读顶层设计 artefact（宪法第 XV 条）

1. `harness/top_level_design/workflow.md#stage-dir_load` —— `tool_ids` / `skill_names` 字段如何产生。
2. `harness/top_level_design/architecture_modules.md#mod-protocol-skill-loader` + `#mod-protocol-tool-registry` —— 模块职责、API、依赖矩阵。
3. `harness/top_level_design/module_schemas.md#schema-skill-spec-frontmatter` + `#schema-tool-spec-side-effect` + `#schema-middleware-spec` —— 5 个 schema 字段约束。
4. 宪法第 V 条（智能体目录契约）—— `skills/<name>/SKILL.md` 布局 + `tools/<name>.py` 约定。

## 三、本 feature 覆盖的范围

### 3.1 模块

| module_id | 关键 API | 行数估算 |
|---|---|---|
| `protocol_skill_loader` | `load_all(skills_dir: str) -> list[SkillSpec]` + `parse_frontmatter(md_path: str) -> SkillFrontmatter` | ~180 |
| `protocol_tool_registry` | `register_all(tools_dir: str) -> list[ToolSpec]` + `get_by_id(tool_id: str) -> ToolSpec \| None` | ~220 |

### 3.2 Schema

- `SkillSpec`（6 字段 + `enabled` 默认 True）
- `SkillFrontmatter`（6 字段：`name` / `description` / `version` semver / `author` / `tags` / `requires`）
- `ToolSpec`（6 字段：`tool_id` / `tool_name` / `description` / `args_schema` JSON Schema / `side_effects` / `enabled` + `requires_approval` 默认 False）
- `ToolSideEffect`（7 枚举值：`none` / `read_file` / `write_file` / `exec_shell` / `network_call` / `send_message` / `external_state`）
- `MiddlewareSpec`（**评审 s-3 修复后归 F10 拥有**：F04 仅在 §3.2 引用 schema 定义，不实现 loader；F10 §3.4a 实现完整加载协议；F04 deliverable 不再包含 MiddlewareSpec 的 Python 类型定义）
- **review.md M-2 修复后**：`register_all()` 仅接收 `tools_dir` 一个参数；移除 `extra_dirs: list[str] = []`（MCP 预留位 v1 不实现）。

### 3.3 Skill 加载协议

- **目录布局**：`skills/<skill_name>/SKILL.md`（强制）；body 必须是 Markdown。
- **frontmatter 格式**：
  ```yaml
  ---
  name: research-assistant
  description: 用于检索学术文献...
  version: v1.2.0
  author: <可选>
  tags: [research, academic]
  requires: [arxiv-search, citation-formatter]
  ---
  ```
- **缺失字段**：跳过该 skill 并发 `skill_load_failed` 事件 + `la.runtime.skill_load_failed` 日志（不阻塞主流程）。
- **version 校验**：`version` 字段必须匹配正则 `^v\d+\.\d+\.\d+$`，否则抛 `SkillFrontmatterParseError`，退出码 65。

### 3.4 Tool 加载协议

- **目录布局**：`tools/<tool_name>.py`，导出名为 `<tool_name>` 的 LangChain `BaseTool` 子类实例（或 `@tool` 装饰器函数）。
- **side_effects 标注（review.md v0.4.0 m-NEW-2 修复后 fail-CLOSED 倾向）**：每个 tool 必须有 `SIDE_EFFECTS: list[str] = ["..."]` 模块级常量（由实现者声明）。**未声明 SIDE_EFFECTS** → F04 默认填 `[ToolSideEffect.NONE]`，并通过 `from langagent.cross_cutting.logger import emit` 发 `la.tool.suspicious_missing_side_effects` 警告日志（**review.md v0.1.0 R-001 修复后**：该 tag 是 tool 静态属性警告，**走 logger 路径不通过 event bus**；F08 `ALLOWED_TAGS` 集合 45 → 46 项；F09 guardrail 在拦截决策时对未声明 SIDE_EFFECTS 的 tool 触发"deny by default"——详见 F09 §三.4 决策矩阵）。
- **requires_approval 标注**：`REQUIRES_APPROVAL: bool = True/False` 模块级常量（默认 False）。
- **args_schema**：从 `BaseTool.args_schema` 自动提取（`pydantic.BaseModel.model_json_schema()`，**review.md m-3 修复后**：强制 JSON Schema Draft 7；用 `pydantic.json_schema.PydanticJsonSchema` + `mode='serialization'` 输出）。
- **dynamic import**：用 `importlib.util.spec_from_file_location()` + `module_from_spec()` 加载；不污染 sys.path。**review.md v1.0.0 P2-9 修复新增命名空间约定**：`spec.name` 必须使用 unique 命名空间避免与其他模块冲突：
  - tool 加载：`spec = importlib.util.spec_from_file_location(f"langagent_dynamic_tool_{tool_id}", path)`
  - skill 加载：`spec = importlib.util.spec_from_file_location(f"langagent_dynamic_skill_{skill_name}", path)`
  - 加载完成后由 loader 负责清理（`del sys.modules[spec.name]` 或保留到进程结束）；`spec_from_file_location` 的 `name` 参数**必须**是 unique 字符串，禁止使用裸文件名（如 `"echo"`）以避免与用户 `tools/echo.py` 同名但内容不同的情况冲突。
- **sys.modules 清理策略（review.md v2.2.0 P2-4 修复新增）**：
  - F04 tool_loader 在 `register_all()` 返回前对每个成功加载的 tool 调 `sys.modules.pop(f"langagent_dynamic_tool_{tool_id}", None)`（立即释放）；失败 tool 不注册不需清理。
  - F04 skill_loader 同理：`sys.modules.pop(f"langagent_dynamic_skill_{skill_name}", None)`。
  - 进程退出前由 F06 `exit_handler.cleanup()` 兜底扫描：清空 `sys.modules` 中所有前缀 `langagent_dynamic_` 的 entry（防止中途异常导致泄漏）；兜底清理放在 §3.3 关闭顺序 step 4（`checkpoint_adapter.close`）之后、step 5（`metrics_collector.snapshot`）之前执行。
  - F10 middleware_loader 在 `state_graph_builder.build()` 返回前清理（详见 F10 §3.4a）：`sys.modules.pop(f"langagent_dynamic_middleware_{name}", None)`；命名空间前缀 `langagent_dynamic_middleware_` 与 F04 不同，**避免 tool / middleware 同名时冲突**。
  - 测试覆盖：F04 §四.2 `test_tool_dynamic_import_no_sys_path_pollution` 已存在；新增 `test_tool_loader_cleans_sys_modules_on_register` + `test_tool_loader_cleans_sys_modules_on_skill_load_failed`。
- **tool_id 唯一性（review.md v0.4.0 m-NEW-10 修复后异常传播路径明确）**：重复 `tool_id` 抛 `ToolIdDuplicateError`，**不包装为 F02 `AgentDirInvalidLayoutError`**，**不归类为目录布局错误**。F02 调用 `protocol_tool_registry.register_all()` 时捕获 `ToolIdDuplicateError` → 重新抛出（不包装），退出码 70 由 F01 dispatch 捕获并返回。

### 3.5 MCP 连接器（**review.md M-2 修复后**）

> **v1 不实现 MCP**；宪法第 V 条 1 款强制布局 + 顶层设计三件均无 `.langagent/mcp.yaml` / `connectors/` 目录约定。F04 仅加载 `tools/<tool_name>.py` 与 `skills/<skill_name>/SKILL.md` 两种内置来源。v2+ feature 加 MCP 客户端时，再扩展 `register_all(extra_dirs=...)` 接口。

## 四、TDD 测试用例先行

### 4.1 `protocol_skill_loader` 测试

- [ ] `test_load_all_empty_dir`：`skills/` 目录不存在或为空 → 返回空 list。
- [ ] `test_load_all_single_skill`：构造 `skills/test/SKILL.md` + 合法 frontmatter → 返回 1 个 SkillSpec。
- [ ] `test_load_all_multiple_skills`：3 个 skill 子目录 → 返回 3 个 SkillSpec，顺序与目录遍历一致。
- [ ] `test_parse_frontmatter_valid`：合法 YAML → 返回 SkillFrontmatter 实例。
- [ ] `test_parse_frontmatter_missing_name`：缺 `name` 字段 → 抛 `SkillFrontmatterParseError`，退出码 65。
- [ ] `test_parse_frontmatter_missing_description`：缺 `description` → 同上。
- [ ] `test_parse_frontmatter_version_not_semver`：`version: "1.0"` → 抛错。
- [ ] `test_parse_frontmatter_invalid_yaml`：YAML 语法错 → 抛 `yaml.YAMLError` 包装为 SkillFrontmatterParseError。
- [ ] `test_skill_body_path_resolved`：SkillSpec.body_path 指向 `skills/<name>/SKILL.md` 绝对路径。
- [ ] `test_skill_enabled_default_true`：未指定 enabled → True。
- [ ] `test_skill_publishes_skill_loaded_event`：mock event bus → `skill_loaded` 事件被 publish。
- [ ] `test_skill_publishes_skill_load_failed_event`：缺 frontmatter 字段 → `skill_load_failed` 事件被 publish。

### 4.2 `protocol_tool_registry` 测试

- [ ] `test_register_all_empty_dir`：tools 目录空 → 返回空 list。
- [ ] `test_register_all_single_tool`：构造 `tools/echo.py` 含 `echo = SomeBaseTool(...)` → 返回 1 个 ToolSpec，`tool_id == "echo"`。
- [ ] `test_register_all_multiple_tools`：3 个 tool 文件 → 返回 3 个 ToolSpec。
- [ ] `test_tool_side_effects_default_empty`：tool 无 `SIDE_EFFECTS` 常量 → `side_effects == [ToolSideEffect.NONE]`，且 F08 logger 收到 `la.tool.suspicious_missing_side_effects` 警告日志（**review.md v0.1.0 R-001 修复后**：通过 `cross_cutting_logger.emit()` 调 logger，不通过 event_bus.publish；**v0.4.0 m-NEW-2 修复后**：fail-OPEN 默认 + 警告日志；F09 guardrail 仍按 deny-by-default 处理未声明 side_effects 的 tool）。
- [ ] `test_tool_side_effects_from_constant`：tool 含 `SIDE_EFFECTS = ["write_file", "exec_shell"]` → ToolSpec.side_effects 正确解析。
- [ ] `test_tool_side_effects_invalid_value`：含 `"unknown_side_effect"` → 抛 `ToolSideEffectParseError`，退出码 65。
- [ ] `test_tool_requires_approval_default_false`：tool 无 `REQUIRES_APPROVAL` → False。
- [ ] `test_tool_requires_approval_from_constant`：`REQUIRES_APPROVAL = True` → ToolSpec.requires_approval == True。
- [ ] `test_tool_args_schema_extracted`：tool 的 args_schema 是 Pydantic BaseModel → ToolSpec.args_schema 形如 `{"type": "object", "properties": {...}}`，且 `$schema == "http://json-schema.org/draft-07/schema#"`（**v0.4.0 m-NEW-3 修复后**：JSON Schema Draft 7 强制校验）。
- [ ] `test_tool_id_duplicate`：两个 tool 文件同 tool_id → 抛 `ToolIdDuplicateError`，退出码 70（**v0.4.0 m-NEW-10 修复后**：异常不包装为 F02 `AgentDirInvalidLayoutError`；F02 register_all() 直接重新抛出）。
- [ ] `test_tool_dynamic_import_no_sys_path_pollution`：测试前后 `sys.path` 长度不变。
- [ ] `test_tool_get_by_id`：register 后 `get_by_id("echo")` 返回对应 ToolSpec；不存在返回 None。
- [ ] `test_tool_publishes_tool_registered_event`：mock event bus → `tool_registered` 事件被 publish。

### 4.3 集成测试（F02 之后跑）

- [ ] `test_skill_loader_handles_malformed_skill_gracefully`：构造 1 个合法 + 1 个非法 skill → 返回 1 个 SkillSpec + 1 条 `skill_load_failed` 事件；不抛异常。
- [ ] `test_tool_registry_handles_import_error_gracefully`：构造 1 个有 Python 语法错误的 tool → 跳过 + 发 `tool_load_failed` 事件（待与 F07 协调新事件类型）。

## 五、关键约束

1. **dynamic import 不污染 sys.path**：必须用 `importlib.util.spec_from_file_location()`。
2. **版本 semver 严格校验**：`^v\d+\.\d+\.\d+$` 正则，缺位 / 多位 / 非数字字符全报错。
3. **side_effects 标注刚性**：tool 必须显式声明 `SIDE_EFFECTS`；缺省默认 `[ToolSideEffect.NONE]`，但鼓励显式声明。
4. **fail-soft 加载**：单个 skill / tool 加载失败不阻塞其它加载；发 `*_load_failed` 事件即可。
5. **不依赖 LangSmith**：skill / tool 不读 LangSmith；MCP 预留位**v1 不实现**（review.md M-2 修复）。
6. **依赖方向**：protocol 层不依赖 runtime / cli / primitives（仅 cross_cutting_logger + protocol_event_bus）。
7. **TDD 刚性**：先 Red 后 Green 再 Refactor；测试 fixture 提供 `tests/fixtures/sample_agent/skills/` + `tools/`。
8. **第 XV 条对齐清单**：与宪法第 V 条（智能体目录契约）/ 第 VII 条（Middleware 与工具规则）/ 第 XIII 条逐项对齐。

## 六、本 feature 不包含

- 不实现 middleware 加载（→ F10；F10 在 graph_compose 阶段读 `middleware/<name>.py`）。
- 不实现 LoadedAgent 构造（→ F02）。
- **不实现 MCP 客户端**（v1 不实现；review.md M-2 修复后整个 MCP 子节移除）。
- 不实现 channel / identity / memory / sandbox 加载（→ F12）。
- 不实现 EvalTaskSpec 加载（→ F11）。

## 七、Deliverable 清单

- [ ] `langagent/protocol/skill_loader.py` + `tool_registry.py`。
- [ ] `langagent/protocol/skill_schemas.py` + `tool_schemas.py`（**review.md v1.0.0 P2-4 修复**：原 `schemas.py` 单文件拆分为两个文件，按"skill vs tool"职责分离）：
  - `langagent/protocol/skill_schemas.py`：`SkillSpec` + `SkillFrontmatter` 2 个 Pydantic / dataclass 类型。
  - `langagent/protocol/tool_schemas.py`：`ToolSpec` + `ToolSideEffect` 2 个 Pydantic / dataclass 类型。
  - **不导出 `MiddlewareSpec`**（review.md s-3 修复后归 F10）。
- [ ] `tests/protocol/test_skill_loader.py` + `test_tool_registry.py`：≥20 个测试用例。
- [ ] `tests/fixtures/sample_agent/skills/test/SKILL.md` + `tools/echo.py`：测试用 fixture。
- [ ] `mypy --strict` 通过。
- [ ] spec / plan / tasks 顶部引用宪法第 XV 条。

## 八、与其它 feature 的边界

- **F02**：`runtime_dir_loader.load(agent_dir)` 调用 `protocol_skill_loader.load_all(skills_dir)` 与 `protocol_tool_registry.register_all(tools_dir)`；产出 `LoadedAgent.tool_ids` + `skill_names`。
- **F05**：F05 在 main_loop 中通过 `tool_registry.get_by_id(tool_id)` 获取 `BaseTool` 实例列表，注入到 LangGraph 图。
- **F09**：F09 的 guardrail_middleware 读取 `ToolSpec.side_effects` + `ToolSpec.requires_approval` 字段做决策。
- **F10**：F10 在 graph_compose 阶段读 `middleware/<name>.py` 并实现 MiddlewareSpec loader（**评审 s-3 修复后**：F10 是 MiddlewareSpec 的实际拥有者；F04 仅引用 schema）。