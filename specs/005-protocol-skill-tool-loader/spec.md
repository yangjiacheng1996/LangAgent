# Feature Specification: Protocol Layer Skill + Tool Loading

**Feature Branch**: `005-protocol-skill-tool-loader`

**Created**: 2026-09-20

**Status**: Draft

**Input**: User description: "F05 — Protocol 层 Skill + Tool 加载（protocol_skill_loader + protocol_tool_registry）"

## Clarifications

### Session 2026-09-20

- Q: 当 tool 文件不导出与文件名匹配的变量时，如何确定 tool_id？ → A: 严格匹配：只接受与文件名完全一致的导出变量名（`tools/echo.py` 必须导出 `echo`），其他情况跳过并记录错误
- Q: 当 BaseTool.args_schema 为 None 时，ToolSpec.args_schema 应该是什么值？ → A: 最小合法 JSON Schema：`{"type": "object", "properties": {}, "$schema": "http://json-schema.org/draft-07/schema#"}`
- Q: skill frontmatter 中的 `author` 和 `tags` 字段是否为必填？ → A: 仅 name/description/version 必填，author 和 tags 可选：缺失时 author 为 None，tags 为空列表 []
- Q: 当加载过程中遇到 Python 导入错误（ImportError）时，应该如何处理？ → A: 捕获所有导入时错误：包括 SyntaxError、ImportError、ModuleNotFoundError，跳过该 tool 并在 tool_load_failed 事件中记录详细错误信息
- Q: ToolSpec 中的 `tool_name` 字段与 `tool_id` 字段有什么区别？ → A: 两者相同：`tool_name` 和 `tool_id` 都设置为文件名（去除 .py 后缀），提供命名一致性

**Constitutional Reference**: This specification aligns with Article XV (Top-Level Design Primacy) of the LangAgent Constitution and references the following top-level design artifacts:
1. `harness/top_level_design/workflow.md#stage-dir_load` — tool_ids / skill_names field generation
2. `harness/top_level_design/architecture_modules.md#mod-protocol-skill-loader` + `#mod-protocol-tool-registry` — module responsibilities, APIs, dependency matrix
3. `harness/top_level_design/module_schemas.md#schema-skill-spec-frontmatter` + `#schema-tool-spec` — schema field constraints
4. Constitution Article V (Agent Directory Contract) — `skills/<name>/SKILL.md` layout + `tools/<name>.py` conventions

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Load Skills from Agent Directory (Priority: P1)

As a developer initializing a LangAgent runtime, when the system loads an agent directory containing skill definitions, the protocol layer must parse YAML frontmatter from SKILL.md files and produce SkillSpec objects that downstream stages can consume.

**Why this priority**: Core infrastructure capability required by F06 (dir_load stage) to construct LoadedAgent. Without skill loading, the agent cannot register any skills, blocking all dependent features.

**Independent Test**: Can be fully tested by creating a sample agent directory with 1-3 skills, calling `protocol_skill_loader.load_all(skills_dir)`, and verifying the returned SkillSpec list matches expectations. Delivers the foundational protocol layer contract for skill discovery.

**Acceptance Scenarios**:

1. **Given** an agent directory with `skills/research-assistant/SKILL.md` containing valid YAML frontmatter with all required fields (name, description, version, tags, requires), **When** `load_all(skills_dir)` is called, **Then** a SkillSpec with all fields populated is returned, and a `skill_loaded` event is published to the event bus.

2. **Given** an agent directory with 3 skill subdirectories each containing valid SKILL.md files, **When** `load_all(skills_dir)` is called, **Then** 3 SkillSpec objects are returned in directory traversal order.

3. **Given** an agent directory with `skills/malformed/SKILL.md` missing the required `name` field, **When** `load_all(skills_dir)` is called, **Then** the malformed skill is skipped, a `skill_load_failed` event is published with error details, and loading continues for remaining skills without raising exceptions.

4. **Given** a `skills/test/SKILL.md` with version field "v1.2.0", **When** `parse_frontmatter()` is called, **Then** the version passes semver validation (^v\d+\.\d+\.\d+$) and is stored in SkillFrontmatter.

5. **Given** a `skills/test/SKILL.md` with version field "1.0" (not semver), **When** `parse_frontmatter()` is called, **Then** a SkillFrontmatterParseError is raised with exit code 65.

---

### User Story 2 - Load Tools from Agent Directory (Priority: P1)

As a developer initializing a LangAgent runtime, when the system loads an agent directory containing tool definitions, the protocol layer must dynamically import Python modules, extract BaseTool instances, and produce ToolSpec objects with args_schema and requires_approval metadata.

**Why this priority**: Core infrastructure capability required by F06 (dir_load stage) to construct LoadedAgent with tool_ids. Without tool loading, the agent cannot register any tools, blocking F08 (main_loop tool injection).

**Independent Test**: Can be fully tested by creating sample `tools/echo.py` files with LangChain BaseTool subclasses, calling `protocol_tool_registry.register_all(tools_dir)`, and verifying the returned ToolSpec list matches expectations. Delivers the foundational protocol layer contract for tool discovery.

**Acceptance Scenarios**:

1. **Given** an agent directory with `tools/echo.py` exporting a LangChain BaseTool instance named `echo`, **When** `register_all(tools_dir)` is called, **Then** a ToolSpec with `tool_id == "echo"` is returned, and a `tool_registered` event is published to the event bus.

2. **Given** an agent directory with 3 tool files each exporting valid BaseTool instances, **When** `register_all(tools_dir)` is called, **Then** 3 ToolSpec objects are returned.

3. **Given** a `tools/dangerous.py` with module-level constant `REQUIRES_APPROVAL = True`, **When** `register_all(tools_dir)` is called, **Then** the returned ToolSpec has `requires_approval == True`.

4. **Given** a `tools/safe.py` without a `REQUIRES_APPROVAL` constant, **When** `register_all(tools_dir)` is called, **Then** the returned ToolSpec has `requires_approval == False` (default).

5. **Given** a tool with args_schema as a Pydantic BaseModel, **When** `register_all(tools_dir)` is called, **Then** the ToolSpec.args_schema contains a JSON Schema Draft 7 dictionary with `$schema == "http://json-schema.org/draft-07/schema#"`.

6. **Given** two tool files with the same tool_id "echo", **When** `register_all(tools_dir)` is called, **Then** a ToolIdDuplicateError is raised with exit code 70 (not wrapped in AgentDirInvalidLayoutError).

---

### User Story 3 - Fail-Soft Loading with Event Bus Reporting (Priority: P2)

As a system administrator running LangAgent, when individual skills or tools fail to load due to malformed files or import errors, the protocol layer must skip the failing items, emit diagnostic events to the event bus, and continue loading remaining items without blocking the entire initialization.

**Why this priority**: Resilience capability that prevents one bad skill/tool from breaking the entire agent. Critical for production deployments where partial degradation is preferable to total failure.

**Independent Test**: Can be fully tested by creating a mixed directory with 1 valid skill + 1 malformed skill (missing required field) + 1 valid tool + 1 tool with Python syntax error, calling load_all() and register_all(), and verifying that valid items are returned while failed items produce `*_load_failed` events without raising exceptions.

**Acceptance Scenarios**:

1. **Given** an agent directory with 1 valid skill and 1 skill with missing `description` field, **When** `load_all(skills_dir)` is called, **Then** 1 SkillSpec is returned for the valid skill, 1 `skill_load_failed` event is published with error details, and no exceptions are raised.

2. **Given** an agent directory with 1 valid tool and 1 tool file with Python syntax error, **When** `register_all(tools_dir)` is called, **Then** 1 ToolSpec is returned for the valid tool, 1 `tool_load_failed` event is published, and no exceptions are raised.

3. **Given** an agent directory with 1 valid tool and 1 tool file with import error (missing dependency), **When** `register_all(tools_dir)` is called, **Then** 1 ToolSpec is returned for the valid tool, 1 `tool_load_failed` event is published with the ImportError details, and no exceptions are raised.

3. **Given** a skill load failure during `load_all()`, **When** the event bus subscriber queries events, **Then** the `skill_load_failed` event contains the skill directory path, error message, and timestamp.

---

### User Story 4 - Dynamic Import with sys.modules Cleanup (Priority: P2)

As a system operator running LangAgent in a long-lived process, when the protocol layer loads tools and skills via dynamic import, the system must use unique module namespaces and clean up sys.modules entries after loading to prevent memory leaks and namespace collisions.

**Why this priority**: Prevents resource leaks in long-running processes and avoids namespace collisions when multiple agent directories contain tools/skills with identical filenames but different implementations.

**Independent Test**: Can be fully tested by checking sys.modules before and after `register_all()` calls, verifying that no `langagent_dynamic_tool_*` entries remain, and that sys.path length is unchanged.

**Acceptance Scenarios**:

1. **Given** an agent directory with `tools/echo.py`, **When** `register_all(tools_dir)` completes successfully, **Then** `sys.modules` does not contain any key starting with `langagent_dynamic_tool_`, and sys.path length is unchanged from before the call.

2. **Given** a tool file that raises an import error, **When** `register_all(tools_dir)` handles the failure, **Then** sys.modules is not polluted with the failed module's entry.

---

### Edge Cases

- What happens when `skills/` or `tools/` directory does not exist? (Return empty list, no error)
- What happens when a SKILL.md file contains syntactically invalid YAML? (Wrap yaml.YAMLError as SkillFrontmatterParseError, exit code 65)
- What happens when a tool file has a Python syntax error or import error? (Catch SyntaxError, ImportError, ModuleNotFoundError; skip tool and emit `tool_load_failed` event with detailed error information)
- What happens when a tool file exists but does not export a variable matching the filename? (Skip tool, emit `tool_load_failed` event with error message specifying the expected variable name)
- What happens when `version` field contains "v1.2.0.1" (4 segments)? (Fail semver validation, raise SkillFrontmatterParseError)
- What happens when args_schema extraction fails because BaseTool.args_schema is None? (ToolSpec.args_schema is set to minimal valid JSON Schema Draft 7: `{"type": "object", "properties": {}, "$schema": "http://json-schema.org/draft-07/schema#"}`)
- What happens when two tools have different filenames but dynamically resolve to the same tool_id? (ToolIdDuplicateError raised)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `protocol_skill_loader.load_all(skills_dir: str) -> list[SkillSpec]` function that scans `skills/<name>/SKILL.md` files and returns SkillSpec objects.

- **FR-002**: System MUST provide a `protocol_skill_loader.parse_frontmatter(md_path: str) -> SkillFrontmatter` function that extracts YAML frontmatter from a SKILL.md file.

- **FR-003**: System MUST validate that SkillFrontmatter.version matches the semver regex `^v\d+\.\d+\.\d+$`, raising SkillFrontmatterParseError (exit code 65) if invalid.

- **FR-004**: System MUST skip skills with missing required fields (name, description, version) without blocking other skills, and MUST publish a `skill_load_failed` event for each skipped skill. Optional fields (author, tags, requires) default to None or empty list when not present.

- **FR-005**: System MUST provide a `protocol_tool_registry.register_all(tools_dir: str) -> list[ToolSpec]` function that dynamically imports `tools/<tool_name>.py` files and returns ToolSpec objects. Each tool file MUST export a BaseTool instance with a variable name exactly matching the filename (e.g., `tools/echo.py` must export `echo`); files not meeting this requirement are skipped with a `tool_load_failed` event. System MUST catch all import-time errors (SyntaxError, ImportError, ModuleNotFoundError) and skip the failing tool without blocking other tools.

- **FR-006**: System MUST extract `args_schema` from BaseTool instances using `pydantic.BaseModel.model_json_schema()` with JSON Schema Draft 7 output (`$schema == "http://json-schema.org/draft-07/schema#"`). If BaseTool.args_schema is None, system MUST use minimal valid JSON Schema: `{"type": "object", "properties": {}, "$schema": "http://json-schema.org/draft-07/schema#"}`.

- **FR-007**: System MUST read module-level constant `REQUIRES_APPROVAL: bool` from tool files, defaulting to False if not present, and store in ToolSpec.requires_approval.

- **FR-008**: System MUST raise `ToolIdDuplicateError` (exit code 70) when two tools have the same tool_id, without wrapping in AgentDirInvalidLayoutError.

- **FR-009**: System MUST use `importlib.util.spec_from_file_location(f"langagent_dynamic_tool_{tool_id}", path)` for tool imports to create unique module namespaces and prevent collisions.

- **FR-010**: System MUST clean up sys.modules entries after loading by calling `sys.modules.pop(f"langagent_dynamic_tool_{tool_id}", None)` in `register_all()` before returning to prevent memory leaks and namespace collisions.

- **FR-011**: System MUST NOT pollute sys.path during dynamic import operations; sys.path length before and after loading must be identical.

- **FR-012**: System MUST publish `skill_loaded` events to the event bus for each successfully loaded skill, containing skill_name and metadata.

- **FR-013**: System MUST publish `tool_registered` events to the event bus for each successfully registered tool, containing tool_id and metadata.

- **FR-014**: System MUST provide a `protocol_tool_registry.get_by_id(tool_id: str) -> ToolSpec | None` function that retrieves a registered ToolSpec by tool_id.

- **FR-015**: System MUST set SkillSpec.enabled to True by default when not explicitly specified in frontmatter.

- **FR-016**: System MUST set ToolSpec.enabled to False by default (tools are disabled unless explicitly enabled by runtime config).

- **FR-017**: System MUST resolve SkillSpec.body_path to the absolute path of the SKILL.md file.

- **FR-018**: System MUST NOT implement middleware loading (middleware loading is owned by F01 and occurs during graph_compose stage).

- **FR-019**: System MUST NOT implement MCP connector loading (MCP is not part of v1, reserved for future versions).

- **FR-020**: System MUST log skill load failures with tag `la.runtime.skill_load_failed` and tool load failures with tag `la.runtime.tool_load_failed`.

### Key Entities *(include if feature involves data)*

- **SkillSpec**: Represents a loaded skill with fields: name (str), description (str), version (str), author (str | None), tags (list[str]), requires (list[str]), body_path (str), enabled (bool).

- **SkillFrontmatter**: Represents parsed YAML frontmatter with fields: name (str, required), description (str, required), version (str, required), author (str | None, optional, defaults to None), tags (list[str], optional, defaults to []), requires (list[str], optional, defaults to []).

- **ToolSpec**: Represents a registered tool with fields: tool_id (str), tool_name (str, always equal to tool_id for naming consistency), description (str), args_schema (dict), enabled (bool), requires_approval (bool).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Loading 100 skills from a valid agent directory completes in under 2 seconds on standard developer hardware.

- **SC-002**: Loading 50 tools with complex Pydantic args_schema definitions completes in under 3 seconds on standard developer hardware.

- **SC-003**: When 10% of skills have malformed frontmatter, the system successfully loads the remaining 90% without exceptions.

- **SC-004**: After loading 100 tools, sys.modules contains zero entries with prefix `langagent_dynamic_tool_`.

- **SC-005**: All skill load successes and failures are observable via event bus subscriptions with structured event data.

- **SC-006**: Tool registry returns correct ToolSpec within 1ms when queried by tool_id after registration.

- **SC-007**: System passes mypy --strict validation with zero type errors.

## Assumptions

- Agent directories follow the layout defined in Constitution Article V (Agent Directory Contract).
- Skills use YAML frontmatter format as specified in `module_schemas.md#schema-skill-spec-frontmatter`.
- Tools export LangChain BaseTool instances or @tool decorator functions with the export name exactly matching the filename (strict matching enforced).
- Event bus (F03) is already initialized and available for publishing events.
- Logger (F02) is already initialized and available for logging diagnostic messages.
- F06 (runtime_dir_loader) will call these protocol layer functions during the dir_load stage.
- The system uses Python 3.10+ with support for importlib.util dynamic imports.
- JSON Schema Draft 7 is the standard format for args_schema serialization.
- Exit codes follow the BSD sysexits.h convention (65 = EX_DATAERR, 70 = EX_SOFTWARE).
- Middleware loading is handled separately by F01 during graph_compose stage, not by F05.
- MCP (Model Context Protocol) connectors are not implemented in v1, reserved for future expansion.

## Dependencies

- **F02 (cross_cutting_logger)**: Used to log skill_load_failed and tool_load_failed events with structured tags.
- **F03 (protocol_event_bus)**: Used to publish skill_loaded, tool_registered, skill_load_failed, and tool_load_failed events.
- **F01 (primitives_langchain_types)**: Provides BaseTool type annotations and LangChain type re-exports.
- **LangChain SDK**: Required for BaseTool class and Pydantic schema utilities.
- **Pydantic**: Required for BaseModel.model_json_schema() to extract args_schema.
- **PyYAML**: Required for parsing YAML frontmatter from SKILL.md files.

## Out of Scope

- Middleware loading (owned by F01, occurs during graph_compose stage)
- LoadedAgent construction (owned by F06)
- MCP client integration (v1 does not implement MCP)
- Channel / Identity / Memory / Sandbox loading (owned by F13)
- EvalTaskSpec loading (owned by F11)
- Tool execution (owned by F08 main_loop)
- Skill body interpretation (skills are loaded as metadata only, not executed)
