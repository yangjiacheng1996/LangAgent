# Implementation Plan: Protocol Layer Skill + Tool Loading

**Branch**: `005-protocol-skill-tool-loader` | **Date**: 2026-09-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-protocol-skill-tool-loader/spec.md`

**Constitutional Alignment**: This plan aligns with Article XV (Top-Level Design Primacy) of the LangAgent Constitution. All design decisions reference the three top-level design artifacts: `workflow.md`, `architecture_modules.md`, and `module_schemas.md`.

## Summary

Implement protocol layer infrastructure for loading skills and tools from agent directories during the `dir_load` stage. This feature provides:

1. **Skill Loading** (`protocol_skill_loader`): Scans `skills/<name>/SKILL.md` files, parses YAML frontmatter with semver validation, produces SkillSpec objects
2. **Tool Loading** (`protocol_tool_registry`): Dynamically imports `tools/<tool_name>.py` files using unique namespaces, extracts BaseTool instances with args_schema (JSON Schema Draft 7) and requires_approval metadata, produces ToolSpec objects
3. **Fail-Soft Error Handling**: Individual load failures emit diagnostic events without blocking remaining items
4. **sys.modules Cleanup**: Prevents memory leaks and namespace collisions in long-running processes

**Technical Approach** (from clarifications):
- Tool filename matching: Strict enforcement (`tools/echo.py` must export `echo`)
- args_schema fallback: Minimal valid JSON Schema Draft 7 when BaseTool.args_schema is None
- Skill frontmatter: Only name/description/version required; author/tags optional with defaults
- Import error handling: Catch all import-time errors (SyntaxError, ImportError, ModuleNotFoundError)
- tool_name vs tool_id: Identical values for naming consistency

## Technical Context

**Language/Version**: Python 3.10+ (as specified in `pyproject.toml`)

**Primary Dependencies**: 
- LangChain SDK (BaseTool class, Pydantic schema utilities)
- Pydantic (BaseModel.model_json_schema() for args_schema extraction)
- PyYAML (YAML frontmatter parsing)

**Storage**: N/A (protocol layer loads from filesystem but does not persist state)

**Testing**: pytest with TDD approach (17+ test cases covering all user stories)

**Target Platform**: Linux server / macOS developer workstation (Python 3.10+ runtime)

**Project Type**: Library module (protocol layer of LangAgent agent runtime)

**Performance Goals**: 
- Load 100 skills in <2s on standard developer hardware
- Load 50 tools with complex args_schema in <3s
- Tool registry query <1ms latency

**Constraints**: 
- Zero sys.path pollution (dynamic import via importlib.util)
- Zero sys.modules leakage (cleanup before function return)
- Fail-soft loading (individual failures don't block batch)
- JSON Schema Draft 7 compliance for args_schema

**Scale/Scope**: 
- Expected: 10-50 skills per agent directory
- Expected: 5-30 tools per agent directory
- Edge case: 100+ skills/tools (performance target)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article I (Project Identity & Boundaries) ✅ PASS
- **Alignment**: F05 is a protocol layer module, not exposed as SDK. No public API beyond LangAgent internal usage.
- **Non-Goals Compliance**: No cloud SaaS, no LangSmith dependency, no external network calls.

### Article II (Tech Stack & Dependencies) ✅ PASS
- **LangChain Usage**: Imports BaseTool from LangChain via `primitives_langchain_types` re-export layer.
- **Dependency Scope**: PyYAML, Pydantic already in LangChain optional dependencies.
- **Python Version**: Python 3.10+ per `pyproject.toml`.

### Article III (LangSmith Isolation) ✅ PASS
- **No LangSmith Imports**: Zero `from langsmith import` statements.
- **No Environment Variables**: Does not read LANGSMITH_API_KEY or related vars.
- **Local-Only**: All operations filesystem-local.

### Article V (Agent Directory Contract) ✅ PASS
- **Layout Compliance**: Scans `skills/<name>/SKILL.md` and `tools/<tool_name>.py` per contract.
- **SKILL.md Format**: YAML frontmatter with Markdown body.
- **Tool Export Convention**: Strict filename matching enforced (clarification #1).

### Article VII (Middleware & Tool Rules) ✅ PASS
- **Tool Schema**: Pydantic BaseModel args_schema extracted via model_json_schema().
- **No Dynamic String Schema**: All schemas typed via Pydantic.
- **No Background Tasks**: Dynamic import does not trigger __init__ side effects.

### Article XIII (Hard No) ✅ PASS
- **No Hardcoded Paths**: All paths parameterized via function arguments.
- **No LangSmith**: Zero dependencies on LangSmith.
- **TDD Enforced**: 17+ test cases written before implementation.
- **Structured Logging**: Uses `cross_cutting_logger` with `la.*` tags.

### Article XV (Top-Level Design Primacy) ✅ PASS
- **Artifacts Reviewed**: 
  - `workflow.md#stage-dir_load` - Defines tool_ids/skill_names field generation
  - `architecture_modules.md#mod-protocol-skill-loader` + `#mod-protocol-tool-registry` - Module responsibilities
  - `module_schemas.md#schema-skill-spec-frontmatter` + `#schema-tool-spec` - Schema field constraints
- **Alignment Checklist**: Spec includes explicit references to all three artifacts in Constitutional Reference section.

## Project Structure

### Documentation (this feature)

```text
specs/005-protocol-skill-tool-loader/
├── spec.md              # Feature specification (completed with clarifications)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (see below)
├── data-model.md        # Phase 1 output (see below)
├── quickstart.md        # Phase 1 output (see below)
├── contracts/           # Phase 1 output (public APIs)
│   ├── skill_loader_api.md
│   └── tool_registry_api.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
langagent/
├── protocol/
│   ├── __init__.py
│   ├── event_bus.py              # Existing (F03)
│   ├── event_types.py            # Existing (F03)
│   ├── skill_loader.py           # NEW - F05 deliverable
│   ├── tool_registry.py          # NEW - F05 deliverable
│   ├── skill_schemas.py          # NEW - F05 deliverable (SkillSpec + SkillFrontmatter)
│   └── tool_schemas.py           # NEW - F05 deliverable (ToolSpec)
├── cross_cutting/
│   ├── logger.py                 # Existing (F02)
│   └── ...
├── primitives/
│   ├── langchain_types.py        # Existing (F01) - BaseTool re-export
│   └── ...
└── ...

tests/
├── protocol/
│   ├── test_skill_loader.py      # NEW - F05 test suite (11 tests)
│   └── test_tool_registry.py     # NEW - F05 test suite (10 tests)
└── fixtures/
    └── sample_agent/
        ├── skills/
        │   ├── test/
        │   │   └── SKILL.md          # NEW - test fixture
        │   └── malformed/
        │       └── SKILL.md          # NEW - test fixture (missing required fields)
        └── tools/
            ├── echo.py               # NEW - test fixture
            ├── dangerous.py          # NEW - test fixture (REQUIRES_APPROVAL=True)
            └── syntax_error.py       # NEW - test fixture (intentional Python error)
```

**Structure Decision**: Single project layout (Option 1). F05 adds 4 new source files to `langagent/protocol/` directory, following existing protocol layer module pattern established by F03 (event_bus.py, event_types.py). Test files mirror source structure under `tests/protocol/`. Test fixtures organized under `tests/fixtures/sample_agent/` to match agent directory contract layout.

## Complexity Tracking

> No violations requiring justification. All design decisions align with constitution and top-level design artifacts.

---

## Phase 0: Outline & Research

### Research Questions

1. **Dynamic Import Best Practices**
   - Question: How to use `importlib.util.spec_from_file_location()` with unique namespaces?
   - Question: What are best practices for sys.modules cleanup to prevent memory leaks?
   - Question: How to handle import errors gracefully without polluting sys.modules?

2. **YAML Frontmatter Parsing**
   - Question: How to extract YAML frontmatter from Markdown files reliably?
   - Question: What are edge cases for invalid YAML syntax?
   - Question: How to validate semver regex `^v\d+\.\d+\.\d+$` robustly?

3. **Pydantic JSON Schema Extraction**
   - Question: How to force JSON Schema Draft 7 output from Pydantic v2?
   - Question: What is the fallback when BaseTool.args_schema is None?
   - Question: How to handle tools with complex nested Pydantic models?

4. **Event Bus Integration**
   - Question: What event schema fields are required for skill_loaded/tool_registered events?
   - Question: How to emit events without blocking if event bus is unavailable?

### Research Tasks

1. **Investigate `importlib.util` dynamic import patterns**
   - Research LangChain's own dynamic loading implementations
   - Study Python's import system for namespace isolation techniques
   - Identify sys.modules cleanup timing (before return vs. atexit)

2. **Study YAML frontmatter parsing libraries**
   - Evaluate python-frontmatter vs manual PyYAML usage
   - Research error handling for malformed YAML
   - Understand YAML parsing performance for 100+ files

3. **Analyze Pydantic JSON Schema generation**
   - Review Pydantic v2 `model_json_schema()` API
   - Test JSON Schema Draft 7 enforcement (`$schema` field)
   - Benchmark schema extraction for complex models

4. **Review F03 event_bus API**
   - Read `langagent/protocol/event_bus.py` implementation
   - Understand event schema from `langagent/protocol/event_types.py`
   - Confirm skill_loaded/tool_registered event types exist or need creation

**Output**: `research.md` documenting findings and decisions for all research questions.

---

## Phase 1: Design & Contracts

### 1. Data Model (`data-model.md`)

**Entities**:

1. **SkillFrontmatter** (dataclass, frozen)
   - `name: str` (required)
   - `description: str` (required)
   - `version: str` (required, semver regex validated)
   - `author: str | None` (optional, defaults to None)
   - `tags: list[str]` (optional, defaults to [])
   - `requires: list[str]` (optional, defaults to [])

2. **SkillSpec** (dataclass, frozen)
   - All fields from SkillFrontmatter
   - `body_path: str` (absolute path to SKILL.md)
   - `enabled: bool` (defaults to True)

3. **ToolSpec** (Pydantic BaseModel)
   - `tool_id: str` (derived from filename)
   - `tool_name: str` (identical to tool_id)
   - `description: str` (extracted from BaseTool.description)
   - `args_schema: dict` (JSON Schema Draft 7)
   - `enabled: bool` (defaults to False)
   - `requires_approval: bool` (defaults to False)

**Validation Rules**:
- SkillFrontmatter.version MUST match `^v\d+\.\d+\.\d+$` regex
- ToolSpec.args_schema MUST include `$schema: "http://json-schema.org/draft-07/schema#"`
- ToolSpec.tool_id MUST be unique across all registered tools
- SkillSpec.body_path MUST be absolute path (resolved via `os.path.abspath()`)

**State Transitions**: N/A (immutable data classes)

### 2. Interface Contracts (`contracts/`)

#### `skill_loader_api.md`

```python
# langagent.protocol.skill_loader

def load_all(skills_dir: str) -> list[SkillSpec]:
    """
    Load all skills from skills_dir.
    
    Args:
        skills_dir: Absolute path to agent directory's skills/ subdirectory
    
    Returns:
        List of SkillSpec objects for successfully loaded skills
        
    Side Effects:
        - Publishes skill_loaded event for each success
        - Publishes skill_load_failed event for each failure
        - Logs to la.runtime.skill_load_failed for failures
        
    Errors:
        Does not raise exceptions for individual skill failures (fail-soft).
        Returns empty list if skills_dir does not exist.
    """

def parse_frontmatter(md_path: str) -> SkillFrontmatter:
    """
    Parse YAML frontmatter from SKILL.md file.
    
    Args:
        md_path: Absolute path to SKILL.md file
        
    Returns:
        SkillFrontmatter object with parsed fields
        
    Raises:
        SkillFrontmatterParseError: If YAML is invalid or required fields missing
        - Exit code 65 (EX_DATAERR) for missing name/description/version
        - Exit code 65 for invalid semver format
    """
```

#### `tool_registry_api.md`

```python
# langagent.protocol.tool_registry

def register_all(tools_dir: str) -> list[ToolSpec]:
    """
    Register all tools from tools_dir via dynamic import.
    
    Args:
        tools_dir: Absolute path to agent directory's tools/ subdirectory
        
    Returns:
        List of ToolSpec objects for successfully registered tools
        
    Side Effects:
        - Dynamically imports tools with unique namespace (langagent_dynamic_tool_{tool_id})
        - Cleans up sys.modules entries before return
        - Does NOT pollute sys.path
        - Publishes tool_registered event for each success
        - Publishes tool_load_failed event for each failure
        - Logs to la.runtime.tool_load_failed for failures
        
    Errors:
        Raises ToolIdDuplicateError (exit code 70) if duplicate tool_id detected.
        Does not raise exceptions for individual tool import failures (fail-soft).
        Returns empty list if tools_dir does not exist.
    """

def get_by_id(tool_id: str) -> ToolSpec | None:
    """
    Retrieve registered ToolSpec by tool_id.
    
    Args:
        tool_id: Tool identifier (filename without .py extension)
        
    Returns:
        ToolSpec if found, None otherwise
        
    Performance:
        O(1) lookup via internal dict registry
    """
```

### 3. Quickstart Validation Guide (`quickstart.md`)

```markdown
# F05 Quickstart: Validating Skill + Tool Loading

## Prerequisites

- Python 3.10+ installed
- LangAgent repository cloned
- Dependencies installed (`pip install -e .`)
- Pytest installed (`pip install pytest pytest-cov`)

## Validation Scenario 1: Load Skills from Sample Agent

### Setup
```bash
# Create sample agent directory with test skills
mkdir -p tests/fixtures/sample_agent/skills/test
cat > tests/fixtures/sample_agent/skills/test/SKILL.md << 'EOF'
---
name: test-skill
description: A test skill for validation
version: v1.0.0
tags: [test, validation]
requires: []
---
# Test Skill Body
This is the skill body content.
EOF
```

### Test Command
```bash
pytest tests/protocol/test_skill_loader.py::test_load_all_single_skill -v
```

### Expected Outcome
- Test passes with 1 SkillSpec returned
- SkillSpec.name == "test-skill"
- SkillSpec.enabled == True
- skill_loaded event published to event bus

## Validation Scenario 2: Load Tools from Sample Agent

### Setup
```bash
# Create sample tool file
cat > tests/fixtures/sample_agent/tools/echo.py << 'EOF'
from langchain.tools import BaseTool

class EchoTool(BaseTool):
    name = "echo"
    description = "Echoes input text"
    
    def _run(self, text: str) -> str:
        return text

echo = EchoTool()
EOF
```

### Test Command
```bash
pytest tests/protocol/test_tool_registry.py::test_register_all_single_tool -v
```

### Expected Outcome
- Test passes with 1 ToolSpec returned
- ToolSpec.tool_id == "echo"
- ToolSpec.requires_approval == False
- sys.modules has zero `langagent_dynamic_tool_*` entries after test

## Validation Scenario 3: Fail-Soft Error Handling

### Setup
```bash
# Create malformed skill (missing required field)
mkdir -p tests/fixtures/sample_agent/skills/malformed
cat > tests/fixtures/sample_agent/skills/malformed/SKILL.md << 'EOF'
---
description: Missing name field
version: v1.0.0
---
# Malformed Skill
EOF
```

### Test Command
```bash
pytest tests/protocol/test_skill_loader.py::test_skill_loader_handles_malformed_skill_gracefully -v
```

### Expected Outcome
- Test passes with empty SkillSpec list (or partial list if mixed with valid skills)
- skill_load_failed event published with error details
- No exceptions raised (fail-soft behavior)

## Full Test Suite

Run all F05 tests:
```bash
pytest tests/protocol/test_skill_loader.py tests/protocol/test_tool_registry.py -v --cov=langagent/protocol
```

Expected: 17+ tests passing, >90% coverage on skill_loader.py and tool_registry.py

## Integration Validation

Once F06 is implemented, validate end-to-end:
```bash
pytest tests/integration/test_dir_load_stage.py -v
```

Expected: F06 calls F05 APIs during dir_load stage, produces LoadedAgent with populated tool_ids and skill_names fields.
```

---

## Next Steps

After Phase 1 design artifacts are generated:

1. **Review Constitution Check**: Re-evaluate all gates against Phase 1 design decisions
2. **Proceed to `/speckit.tasks`**: Generate task breakdown for TDD implementation
3. **Begin Red-Green-Refactor Cycle**: Write failing tests first, implement to pass, refactor

---

## Dependencies & Integration Points

### Upstream Dependencies (F05 depends on)

- **F02 (cross_cutting_logger)**: Used for `la.runtime.skill_load_failed` and `la.runtime.tool_load_failed` logging
- **F03 (protocol_event_bus)**: Used to publish skill_loaded, tool_registered, skill_load_failed, tool_load_failed events
- **F01 (primitives_langchain_types)**: Provides BaseTool type annotations via re-export layer

### Downstream Dependents (F05 provides to)

- **F06 (runtime_dir_loader)**: Calls `skill_loader.load_all()` and `tool_registry.register_all()` during dir_load stage to produce LoadedAgent.tool_ids and LoadedAgent.skill_names
- **F08 (runtime_main_loop_dispatcher)**: Calls `tool_registry.get_by_id()` to retrieve ToolSpec objects for injection into LangGraph graph

### Integration Constraints

- F05 MUST NOT depend on F06 (protocol layer cannot depend on runtime layer per architecture_modules.md dependency matrix)
- F05 MUST NOT instantiate LangGraph or LangChain objects beyond BaseTool type annotations
- F05 MUST clean up sys.modules before returning from register_all() to prevent leakage into F06

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Dynamic import fails for tools with complex dependencies | Medium | High | Catch all import-time errors (SyntaxError, ImportError, ModuleNotFoundError), emit tool_load_failed event, continue loading |
| Memory leak from sys.modules pollution | Medium | Medium | Explicit cleanup in register_all() before return; F09 exit_handler兜底扫描 `langagent_dynamic_*` entries |
| YAML parsing fails for edge-case frontmatter | Low | Medium | Wrap yaml.YAMLError as SkillFrontmatterParseError with exit code 65; log detailed error message |
| JSON Schema Draft 7 not enforced | Low | Low | Validate `$schema` field in ToolSpec construction; use Pydantic json_schema with mode='serialization' |
| tool_id collision across multiple tool files | Low | High | Raise ToolIdDuplicateError (exit code 70) immediately; do not wrap in AgentDirInvalidLayoutError |

---

## Success Metrics (from spec.md)

- **SC-001**: Loading 100 skills completes in <2s ✓
- **SC-002**: Loading 50 tools completes in <3s ✓
- **SC-003**: 10% malformed skills → 90% loaded successfully ✓
- **SC-004**: Zero sys.modules entries with `langagent_dynamic_tool_` prefix after loading ✓
- **SC-005**: All load events observable via event bus ✓
- **SC-006**: Tool registry query latency <1ms ✓
- **SC-007**: mypy --strict passes with zero type errors ✓
