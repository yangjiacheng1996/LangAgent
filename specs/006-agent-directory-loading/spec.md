# Feature Specification: Agent Directory Loading (dir_load Stage)

**Feature Branch**: `006-agent-directory-loading`

**Created**: 2026-09-20

**Status**: Draft

**Input**: User description: "F06 — 智能体目录加载（dir_load 阶段）"

**Constitutional Alignment**: This specification aligns with Constitution Article XV (Top-Level Design Primacy). All design decisions reference the authoritative artifacts in `harness/top_level_design/`.

## Clarifications

### Session 2026-09-20

- Q: 当 instructions.md 文件为空或只包含空白字符时，系统应该如何处理？ → A: 用默认提示词替换（"You are a helpful assistant."）并发出警告日志（la.runtime.dir_load.warn）
- Q: 当 skills/ 目录中存在子目录，但该子目录缺少 SKILL.md 文件时，系统应该如何处理？ → A: 跳过该子目录，发出警告日志（la.runtime.dir_load.warn），继续扫描其他 skills
- Q: 当 instructions.md 文件非常大时，系统应该设置大小限制吗？ → A: 设置 100KB 硬限制：超过时抛出 InstructionsReadError 并拒绝加载
- Q: 当系统检测到 instructions.md 文件编码不是 UTF-8 时，应该如何处理？ → A: 尝试自动检测编码并转换为 UTF-8，检测失败时才抛出错误
- Q: 当 write_template 被调用在一个已经存在内容的目录时，系统应该如何处理文件冲突？ → A: 针对每个模板文件实现幂等性 - 不存在则创建，存在则验证格式，验证失败则删除并重建

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create New Agent from Template (Priority: P1)

A developer wants to start a new agent project using the `langagent init` command. The system creates a complete, runnable agent directory with all required files and example components.

**Why this priority**: This is the primary entry point for all users. Without a working template generation, users cannot start using LangAgent. This delivers immediate value by providing a working example that demonstrates the agent directory structure.

**Independent Test**: Can be fully tested by running `langagent init my-agent`, then verifying the created directory contains all mandatory files (instructions.md, agent.py, pyproject.toml) and optional examples (skills/, tools/, middleware/), and delivers a runnable minimal agent.

**Acceptance Scenarios**:

1. **Given** a developer runs `langagent init demo-agent`, **When** the command completes, **Then** a `demo-agent/` directory exists with instructions.md, agent.py, pyproject.toml, .env.example, and example skill/tool/middleware files
2. **Given** the template is created, **When** the developer configures .env with valid model credentials, **Then** `langagent run demo-agent` successfully executes without errors
3. **Given** the template generation starts, **When** the process begins, **Then** a log entry `la.lifecycle.init.start` is emitted with the agent name and target directory

---

### User Story 2 - Load Existing Agent Directory (Priority: P1)

A developer has an existing agent directory and wants to load it for execution. The system validates the directory structure, reads the instructions, scans available tools and skills, and returns a LoadedAgent handle ready for further processing.

**Why this priority**: This is the core functionality that enables running existing agents. Every `langagent run` command depends on this capability. It must work reliably or the entire system fails.

**Independent Test**: Can be fully tested by creating a fixture agent directory with valid structure, calling the loader, and verifying the returned LoadedAgent contains correct agent_dir path, instructions content, tool_ids list, skill_names list, and metadata.

**Acceptance Scenarios**:

1. **Given** a valid agent directory with instructions.md, agent.py, and pyproject.toml, **When** the loader scans it, **Then** it returns a LoadedAgent with all 5 fields populated (agent_dir, instructions, tool_ids, skill_names, metadata)
2. **Given** an agent directory with 3 tools in tools/ and 2 skills in skills/, **When** the loader scans it, **Then** tool_ids contains 3 entries and skill_names contains 2 entries
3. **Given** a successful directory load, **When** loading completes, **Then** a log entry `la.runtime.dir_load.ok` is emitted

---

### User Story 3 - Detect Invalid Agent Directory (Priority: P2)

A developer attempts to load an agent directory that is missing required files or has an invalid structure. The system detects the problem, reports which files are missing, and exits with a clear error code.

**Why this priority**: Early validation prevents confusing errors later in the pipeline. Clear error messages improve developer experience and reduce support burden. This is secondary to the happy path but critical for usability.

**Independent Test**: Can be fully tested by creating fixture directories with various missing files (no instructions.md, no agent.py, no pyproject.toml), attempting to load each, and verifying specific error types and exit codes (65 for invalid layout, 66 for directory not found).

**Acceptance Scenarios**:

1. **Given** an agent directory missing instructions.md, **When** the loader validates it, **Then** it raises AgentDirInvalidLayoutError listing "instructions.md" as missing and exits with code 65
2. **Given** an agent directory missing agent.py, **When** the loader validates it, **Then** it raises AgentDirInvalidLayoutError listing "agent.py" as missing and exits with code 65
3. **Given** a path that points to a file instead of a directory, **When** the loader attempts to load it, **Then** it raises AgentDirNotDirectoryError and exits with code 66
4. **Given** any validation failure, **When** the error occurs, **Then** a log entry `la.runtime.dir_load.fail` is emitted with error details

---

### User Story 4 - Enforce Stage Capability Boundaries (Priority: P2)

During the dir_load stage, the system must prevent operations that belong to later stages (reading .env files, instantiating models, compiling graphs). If any code attempts these operations, the system immediately detects and blocks them.

**Why this priority**: Stage isolation is a core architectural principle that prevents tangled dependencies and ensures predictable behavior. While less visible than loading itself, it's critical for maintainability and correctness of the 6-stage pipeline.

**Independent Test**: Can be fully tested by wrapping test functions with the stage_guard decorator, attempting blacklisted operations (open .env, BaseChatModel init, StateGraph.compile), and verifying each raises StageCapabilityViolationError with exit code 1.

**Acceptance Scenarios**:

1. **Given** the dir_load stage is active with stage guards enabled, **When** code attempts to open a .env file, **Then** the audit hook intercepts it and raises StageCapabilityViolationError
2. **Given** the dir_load stage is active with stage guards enabled, **When** code attempts to instantiate BaseChatModel, **Then** the monkeypatch system intercepts it and raises StageCapabilityViolationError
3. **Given** the dir_load stage is active with stage guards enabled, **When** code attempts to call StateGraph.compile(), **Then** the monkeypatch system intercepts it and raises StageCapabilityViolationError
4. **Given** the stage guard decorator wraps a function, **When** the function completes or raises an exception, **Then** all monkeypatches and audit hooks are restored to original state

---

### User Story 5 - Support Minimal Valid Agent (Priority: P3)

A developer creates an agent with only the three mandatory files (instructions.md, agent.py, pyproject.toml) and no optional directories. The system recognizes this as valid and loads it successfully.

**Why this priority**: Supporting minimal configurations demonstrates the system doesn't impose unnecessary complexity. This validates the "layout convention" vs "mandatory file" distinction and ensures the system scales down gracefully.

**Independent Test**: Can be fully tested by creating a fixture with only instructions.md, agent.py, and pyproject.toml (no skills/, tools/, middleware/ directories), loading it, and verifying LoadedAgent is returned with empty tool_ids and skill_names lists.

**Acceptance Scenarios**:

1. **Given** an agent directory with only instructions.md, agent.py, and pyproject.toml, **When** the loader validates it, **Then** validation passes with no missing files reported
2. **Given** a minimal agent directory with no skills/ directory, **When** the loader scans it, **Then** skill_names is an empty list and no error is raised
3. **Given** a minimal agent directory with no tools/ directory, **When** the loader scans it, **Then** tool_ids is an empty list and no error is raised

---

### Edge Cases

- **Empty instructions.md**: If instructions.md exists but is empty or contains only whitespace, the system replaces it with a default prompt ("You are a helpful assistant.") and emits a warning log (la.runtime.dir_load.warn)
- **Missing SKILL.md in skill directory**: If a subdirectory exists in skills/ but lacks a SKILL.md file, the system skips that subdirectory, emits a warning log (la.runtime.dir_load.warn), and continues scanning other skills
- **Large instructions.md files**: System enforces a 100KB hard limit on instructions.md size. Files exceeding this limit trigger InstructionsReadError with exit code 4
- **Non-UTF-8 encoding**: System attempts to auto-detect the file encoding and convert to UTF-8. If detection fails, it raises InstructionsReadError with exit code 4
- **Circular symbolic links**: System should detect and skip circular symlinks in skills/ or tools/ directories to prevent infinite loops
- **File permission errors**: If instructions.md cannot be read due to permissions, system raises InstructionsReadError with exit code 4
- **Concurrent loader calls**: v1 does not support concurrent calls from multiple threads; system should document this limitation
- **Directory deleted during load**: If the agent directory is deleted during loading, system raises AgentDirNotFoundError with exit code 66

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `RuntimeDirLoader.load(agent_dir: str) -> LoadedAgent` function that validates directory structure and returns a LoadedAgent handle
- **FR-002**: System MUST provide a `RuntimeDirLoader.validate_layout(agent_dir: str) -> list[str]` function that checks for mandatory files and returns a list of missing items
- **FR-003**: System MUST provide a `RuntimeDirLoader.read_instructions(agent_dir: str) -> str` function that reads and returns the content of instructions.md
- **FR-004**: System MUST provide a `RuntimeDirLoader.write_template(target_dir: str, name: str)` function that creates a complete agent directory template
- **FR-005**: System MUST validate that instructions.md, agent.py, and pyproject.toml exist; if any are missing, raise AgentDirInvalidLayoutError with exit code 65
- **FR-006**: System MUST treat skills/, tools/, and middleware/ directories as optional; their absence is valid and results in empty lists for corresponding LoadedAgent fields
- **FR-007**: System MUST scan tools/ directory and populate LoadedAgent.tool_ids with discovered tool names
- **FR-008**: System MUST scan skills/ directory and populate LoadedAgent.skill_names with discovered skill directory names
- **FR-009**: System MUST emit `la.runtime.dir_load.ok` log on successful load with LoadedAgent details
- **FR-010**: System MUST emit `la.runtime.dir_load.fail` log on any load failure with error type and details
- **FR-011**: System MUST emit `la.lifecycle.init.start` log when write_template begins with target directory and agent name
- **FR-012**: System MUST NOT emit `la.lifecycle.init.end` log (this is handled by F09 exit_cleanup stage)
- **FR-013**: LoadedAgent MUST contain exactly 5 fields: agent_dir (str), instructions (str), tool_ids (list[str]), skill_names (list[str]), metadata (dict)
- **FR-014**: LoadedAgent MUST NOT contain a compiled_graph field (graph compilation is handled by F01 in a later stage)
- **FR-015**: System MUST provide a `@cross_cutting_stage_guard_decorator` that enforces stage capability boundaries using monkeypatch and audit hook mechanisms
- **FR-016**: The stage guard decorator MUST accept parameters: stage_name (str), monkeypatch_blacklist (list[type] | None), audit_event_blacklist (list[str] | None)
- **FR-017**: During dir_load stage, system MUST prevent: reading .env files, instantiating BaseChatModel, calling StateGraph.compile(), calling RuntimeConfigResolver.resolve()
- **FR-018**: Stage guard MUST use monkeypatch to intercept class methods (BaseChatModel.__init__, StateGraph.compile)
- **FR-019**: Stage guard MUST use sys.addaudithook to intercept file operations (open .env, import, compile, exec)
- **FR-020**: When a blacklisted operation is attempted, system MUST raise StageCapabilityViolationError with stage name, target, and operation details, and exit with code 1
- **FR-021**: Stage guard decorator MUST restore all monkeypatches and audit hooks when the decorated function exits (normal or exception)
- **FR-022**: System MUST provide a STAGE_BLACKLIST_TABLE dictionary mapping stage names to their capability restrictions
- **FR-023**: Template MUST create agent.py that exports a variable named `agent` (CompiledStateGraph type)
- **FR-024**: Template MUST create instructions.md with minimal system prompt using `<your-...>` placeholder format
- **FR-025**: Template MUST create .env.example with MODEL_PROVIDER=openai-compatible and `<your-...>` placeholders for sensitive values
- **FR-026**: Template .env.example MUST NOT contain localhost, 127.0.0.1, or any internal IP addresses
- **FR-027**: Template MUST include example-skill in skills/ directory with SKILL.md
- **FR-028**: Template MUST include example tool in tools/ directory demonstrating @tool decorator
- **FR-029**: Template MUST include example middleware in middleware/ directory
- **FR-030**: Template MUST create empty channels/ and sandbox/ directories (v1 reserved, no content)
- **FR-031**: Template agent.py MUST define AgentState TypedDict with all 5 fields: messages, todos, files, context, scratchpad
- **FR-032**: Template agent.py MUST import state reducers from langagent.primitives.state_reducers (replace_with_merge, merge_dict, overwrite_or_merge)
- **FR-033**: Template agent.py MUST import LangChain types from langagent.primitives.langchain_types (BaseMessage, add_messages)
- **FR-034**: System MUST verify directory path exists before loading; if not found, raise AgentDirNotFoundError with exit code 66
- **FR-035**: System MUST verify directory path is actually a directory; if it's a file, raise AgentDirNotDirectoryError with exit code 66
- **FR-036**: If instructions.md read fails due to permissions or I/O error, system MUST raise InstructionsReadError with exit code 4
- **FR-037**: Stage guard MUST enforce single-threaded execution; concurrent calls in v1 are not supported
- **FR-038**: System MUST detect main thread execution in stage guard decorator; non-main-thread calls should document the limitation
- **FR-039**: System MUST enforce a 100KB hard limit on instructions.md file size; files exceeding this limit MUST trigger InstructionsReadError with exit code 4
- **FR-040**: When instructions.md is empty or contains only whitespace, system MUST replace content with default prompt ("You are a helpful assistant.") and emit warning log (la.runtime.dir_load.warn)
- **FR-041**: System MUST attempt to auto-detect file encoding for instructions.md and convert to UTF-8; if detection fails, raise InstructionsReadError with exit code 4
- **FR-042**: When scanning skills/ directory, system MUST skip subdirectories lacking SKILL.md file and emit warning log (la.runtime.dir_load.warn) for each skipped directory
- **FR-043**: write_template function MUST implement idempotent behavior: for each template file, create if missing, validate format if exists, delete and recreate if validation fails
- **FR-044**: Each template file MUST have a corresponding create function (create_xxx) and validation function (validate_xxx) to support idempotent template generation

### Key Entities

- **LoadedAgent**: Represents a validated agent directory ready for further processing
  - agent_dir (str): Absolute path to the agent directory
  - instructions (str): Content of instructions.md file
  - tool_ids (list[str]): List of discovered tool names from tools/ directory
  - skill_names (list[str]): List of discovered skill directory names from skills/ directory
  - metadata (dict): Additional metadata about the agent (version, schema_version=0.2.0)

- **StageCapabilityViolationError**: Exception raised when code attempts operations outside its stage boundaries
  - stage_name (str): Name of the stage where violation occurred
  - target (str): Class or operation that was blocked
  - operation (str): Specific operation attempted (e.g., "__init__", "compile")

- **AgentDirectoryTemplate**: Represents the structure and content of a newly created agent directory
  - Mandatory files: instructions.md, agent.py, pyproject.toml
  - Optional layout: skills/, tools/, middleware/, channels/, sandbox/
  - Configuration: .env.example with provider-agnostic placeholders

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can create a new agent directory in under 5 seconds by running `langagent init <name>`
- **SC-002**: Generated templates are immediately runnable after configuring .env with valid credentials (zero additional setup required)
- **SC-003**: Agent directory loading completes in under 100ms for typical agent directories (< 10 skills, < 20 tools)
- **SC-004**: Invalid agent directories are detected within 50ms with clear error messages indicating exactly which files are missing
- **SC-005**: 100% of stage capability violations are caught at runtime before causing side effects (no .env reads, no model instantiations, no graph compilations during dir_load)
- **SC-006**: Stage guard overhead adds less than 10ms to directory loading time
- **SC-007**: All template files are portable across machines (no absolute paths, localhost references, or machine-specific assumptions)
- **SC-008**: Minimal agent directories (3 mandatory files only) load successfully with zero errors or warnings
- **SC-009**: Template generation includes working examples that demonstrate all major agent capabilities (skills, tools, middleware)
- **SC-010**: Error messages include actionable guidance (which file is missing, what the expected structure should be)

## Assumptions

- **Layout Conventions**: The skills/, tools/, and middleware/ directories are layout conventions, not mandatory. Their absence is valid and results in empty capability lists. This aligns with Constitution Article V which specifies only 3 mandatory files.
- **Single-Threaded Execution**: The v1 implementation assumes single-threaded sequential execution of the 6-stage pipeline. Concurrent or nested stage execution is out of scope and will be addressed in v2 with hook/patch stacks.
- **File System Access**: The system has read/write access to the file system for loading agent directories and creating templates. Network file systems and containerized environments are supported as long as standard Python file I/O works.
- **Python Environment**: The loader runs within a Python environment where LangChain and LangGraph are already installed. The loader does not manage Python package installation.
- **File Encoding**: The system attempts to auto-detect file encoding for instructions.md and convert to UTF-8. If auto-detection fails, it raises InstructionsReadError. Other text files (SKILL.md, tool files) are assumed to be UTF-8 encoded.
- **No .env Reading**: The dir_load stage explicitly does NOT read .env files. Environment configuration is handled by F07 (config_resolve stage) after directory loading completes.
- **Model Independence**: Directory loading does not depend on model availability or credentials. An agent directory can be loaded and validated even when models are unreachable.
- **Graph Compilation Deferred**: The loader does NOT compile the LangGraph graph from agent.py. Graph compilation is handled by F01 (graph_compose stage) and the compiled graph is held by F10 dispatch, not stored in LoadedAgent.
- **Metadata Defaults**: The metadata field in LoadedAgent contains at minimum a schema_version indicator (0.2.0) but may be extended with additional fields by future features without breaking compatibility.
- **Template Overwrite Behavior**: write_template implements idempotent behavior. For each template file: if missing, create it; if exists, validate its format; if validation fails, delete and recreate. This ensures repeated calls to langagent init are safe and can repair corrupted files while preserving valid user modifications.
- **Cross-Feature Stage Guard**: The stage_guard.py module is implemented in langagent/cross_cutting/ and is reused by F06, F07, F08, F09, and F01. F06 is responsible for implementing this shared module first, and other features will consume it.
- **Checkpoint Storage External**: LoadedAgent does not contain checkpoint state or compiled graph instances. These runtime artifacts are managed by F01 and F10, keeping LoadedAgent focused on static agent definition data.
