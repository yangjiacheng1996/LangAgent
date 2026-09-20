# Implementation Plan: Agent Directory Loading (dir_load Stage)

**Branch**: `006-agent-directory-loading` | **Date**: 2026-09-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-agent-directory-loading/spec.md`

## Summary

This feature implements the first stage (dir_load) of the LangAgent 6-stage runtime pipeline. It provides functionality to:

1. **Load existing agent directories**: Validate directory structure, read instructions.md, scan tools and skills, return a LoadedAgent handle
2. **Generate agent templates**: Create complete, runnable agent directories via `langagent init` command with idempotent behavior
3. **Enforce stage boundaries**: Implement cross-cutting stage guard mechanism to prevent operations outside the dir_load stage scope
4. **Handle edge cases**: Empty files, encoding detection, size limits, missing subdirectory components

The technical approach centers on a RuntimeDirLoader class with four primary methods (load, validate_layout, read_instructions, write_template) and a shared cross_cutting_stage_guard_decorator that will be reused by F01, F07, F08, F09.

## Technical Context

**Language/Version**: Python 3.11+ (per pyproject.toml requires-python)

**Primary Dependencies**: 
- LangChain (primitives layer imports)
- LangGraph (for template agent.py generation)
- chardet or charset-normalizer (for encoding detection - FR-041)
- Standard library: sys.addaudithook, pathlib, os

**Storage**: Filesystem-based (agent directories, no database)

**Testing**: pytest with fixtures (single-threaded, no pytest-xdist per FR-037)

**Target Platform**: Linux server (primary), cross-platform file I/O compatible (macOS, Windows via pathlib)

**Project Type**: CLI tool (langagent binary with subcommands: init, run, eval, doctor)

**Performance Goals**: 
- Template generation: <5 seconds (SC-001)
- Directory loading: <100ms for typical agents (SC-003)
- Invalid directory detection: <50ms (SC-004)
- Stage guard overhead: <10ms (SC-006)

**Constraints**:
- Single-threaded execution only (v1 constraint, FR-037)
- 100KB hard limit on instructions.md (FR-039, clarification Q3)
- No .env reading during dir_load stage (stage boundary enforcement)
- No model instantiation or graph compilation (deferred to F01, F07)

**Scale/Scope**: 
- Typical agent: <10 skills, <20 tools (SC-003 baseline)
- Template files: 8-10 files per agent directory
- LoadedAgent schema: 5 fields (agent_dir, instructions, tool_ids, skill_names, metadata)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Alignment with Constitution Articles

✅ **Article I (Project Identity)**: F06 delivers CLI functionality (`langagent init`), not SDK. Template generation creates agent directories as the user's primary interface.

✅ **Article II (Tech Stack)**: Uses LangChain primitives (langchain_types), LangGraph (template agent.py), no new dependencies beyond encoding detection library.

✅ **Article III (LangSmith剥离)**: Stage guard explicitly blocks LangSmith-related operations; no LANGSMITH_* env vars read; no tracing dependencies.

✅ **Article V (Agent Directory Contract)**: 
- Enforces 3 mandatory files (instructions.md, agent.py, pyproject.toml)
- Treats skills/, tools/, middleware/ as optional layout conventions
- Template generation follows exact structure specified in Article V Section 1

✅ **Article VI (Agent Loop & State)**: Template agent.py includes AgentState TypedDict with all 5 fields (messages, todos, files, context, scratchpad) per FR-031.

✅ **Article VIII (TDD)**: Spec includes 5 user stories with acceptance scenarios; plan will generate test fixtures before implementation (Red-Green-Refactor).

✅ **Article X (Security)**: 
- No .env reading in dir_load stage (deferred to F07)
- Template .env.example uses placeholders, no localhost/internal IPs (FR-026)
- File size limit prevents DoS via huge instructions.md (FR-039)

✅ **Article XIII (Prohibitions)**:
- No hardcoded paths in templates (SC-007 portability)
- No LangSmith dependencies
- TDD enforced (all tests in Phase 0/1 before implementation)

✅ **Article XV (Top-Level Design Primacy)**: 
- Spec references harness/top_level_design/ artifacts
- LoadedAgent schema aligns with module_schemas.md (5 fields, schema_version 0.2.0)
- Stage boundaries align with workflow.md dir_load definition

### Gate Violations

**None**. All Constitution requirements satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/006-agent-directory-loading/
├── plan.md              # This file
├── research.md          # Phase 0 output (encoding detection, monkeypatch techniques)
├── data-model.md        # Phase 1 output (LoadedAgent, StageCapabilityViolationError schemas)
├── quickstart.md        # Phase 1 output (validation scenarios)
├── contracts/           # Phase 1 output (RuntimeDirLoader API, stage_guard_decorator signature)
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
langagent/
├── runtime/
│   └── dir_loader.py              # RuntimeDirLoader class (FR-001 to FR-004)
├── cross_cutting/
│   ├── stage_guard.py             # @cross_cutting_stage_guard_decorator (FR-015)
│   ├── stage_guard_monkeypatch.py # Monkeystack, patch/restore functions (FR-018)
│   └── stage_guard_audit.py       # AuditHookManager (FR-019)
└── primitives/
    ├── langchain_types.py         # BaseMessage, add_messages (already exists, used by template)
    └── state_reducers.py          # replace_with_merge, merge_dict, etc. (already exists)

tests/
├── runtime/
│   ├── test_dir_loader.py         # ≥15 test cases (spec §四.1, §四.2)
│   └── test_write_template.py     # ≥8 test cases (spec §四.4)
├── cross_cutting/
│   ├── test_stage_guard.py        # ≥8 test cases (spec §四.3)
│   ├── test_stage_guard_monkeypatch.py  # ≥3 test cases
│   └── test_stage_guard_audit_hook.py   # ≥3 test cases
└── fixtures/
    ├── sample_agent/              # Complete valid agent directory
    └── broken_agent/              # Missing instructions.md (negative test)
```

**Structure Decision**: Single project structure. LangAgent uses a layered architecture (primitives → runtime → cross_cutting → cli). F06 adds runtime/dir_loader.py and cross_cutting/stage_guard*.py modules. Templates generated by write_template follow Constitution Article V layout.

## Complexity Tracking

> No Constitution violations detected. This section is not applicable.

---

# Phase 0: Outline & Research

## Research Tasks

Based on Technical Context unknowns and functional requirements:

1. **Encoding Detection Library Selection**
   - **Need**: Auto-detect file encoding for instructions.md (FR-041, clarification Q4)
   - **Options**: chardet, charset-normalizer, Python standard library codecs.BOM_*
   - **Criteria**: Accuracy on Chinese/English mixed content, performance (<10ms overhead), license compatibility

2. **Monkeypatch Techniques for Method Interception**
   - **Need**: Intercept BaseChatModel.__init__, StateGraph.compile without modifying LangChain/LangGraph source (FR-018)
   - **Research**: Python descriptor protocol, class.__dict__ manipulation, try/finally safety, nested decorator behavior
   - **Validate**: Monkeypatch restore after exception, no memory leaks

3. **sys.addaudithook Limitations**
   - **Need**: Understand CPython audit hook single-hook constraint (spec §3.4a)
   - **Research**: PEP 578, hook registration lifecycle, blacklist event types (open, import, compile, exec)
   - **Validate**: Hook cleanup on decorator exit, no interference with pytest audit hooks

4. **Template Validation Functions Design**
   - **Need**: Idempotent write_template with per-file create/validate pairs (FR-043, FR-044, clarification Q5)
   - **Research**: Validation strategies for .py (AST parse), .md (non-empty), .toml (TOML parse), .env.example (placeholder regex)
   - **Pattern**: validate_xxx() returns bool + error message; create_xxx() writes file content

5. **Pytest Single-Thread Enforcement**
   - **Need**: Prevent pytest-xdist from running tests concurrently (FR-037, spec §3.4a review.md v1.0.0 P2-2)
   - **Research**: pyproject.toml [tool.pytest.ini_options] addopts, threading.current_thread() assertion in decorator
   - **Decision**: Document in pyproject.toml or implement runtime check

## Research Consolidation (research.md)

*Full research.md to be generated after research tasks complete. Key decisions placeholder:*

- **Encoding Detection**: TBD (chardet vs charset-normalizer benchmark)
- **Monkeypatch Safety**: TBD (descriptor protocol vs direct __dict__ assignment)
- **Template Validation**: TBD (AST vs simple import check for .py files)

---

# Phase 1: Design & Contracts

## Prerequisites

- research.md complete with all NEEDS CLARIFICATION resolved

## Deliverables

### 1. data-model.md

Define schemas for:

- **LoadedAgent** (5 fields per FR-013)
  - agent_dir: str (absolute path)
  - instructions: str (file content, max 100KB)
  - tool_ids: list[str] (from tools/ scan)
  - skill_names: list[str] (from skills/ scan)
  - metadata: dict (contains schema_version="0.2.0")

- **StageCapabilityViolationError** (3 fields per Key Entities)
  - stage_name: str
  - target: str (class/module name)
  - operation: str (method name like "__init__")

- **AgentDirectoryTemplate** (structure per FR-023 to FR-033)
  - Mandatory: instructions.md, agent.py, pyproject.toml
  - Optional: skills/, tools/, middleware/, channels/, sandbox/
  - Generated content rules (placeholders, imports, AgentState definition)

### 2. contracts/

Define public API contracts:

- **contracts/runtime_dir_loader.md**
  ```python
  class RuntimeDirLoader:
      @staticmethod
      def load(agent_dir: str) -> LoadedAgent:
          """FR-001: Validate and load agent directory"""
          
      @staticmethod
      def validate_layout(agent_dir: str) -> list[str]:
          """FR-002: Check mandatory files, return missing items"""
          
      @staticmethod
      def read_instructions(agent_dir: str) -> str:
          """FR-003: Read instructions.md with encoding detection and size limit"""
          
      @staticmethod
      def write_template(target_dir: str, name: str) -> None:
          """FR-004: Generate agent directory template idempotently"""
  ```

- **contracts/stage_guard_decorator.md**
  ```python
  def cross_cutting_stage_guard_decorator(
      stage_name: str,
      *,
      monkeypatch_blacklist: list[type] | None = None,
      audit_event_blacklist: list[str] | None = None
  ) -> Callable:
      """FR-015, FR-016: Enforce stage capability boundaries"""
  ```

- **contracts/error_codes.md**
  - Exit code 1: StageCapabilityViolationError
  - Exit code 4: InstructionsReadError (permissions, I/O, size limit, encoding)
  - Exit code 65: AgentDirInvalidLayoutError (missing mandatory files)
  - Exit code 66: AgentDirNotFoundError, AgentDirNotDirectoryError

### 3. quickstart.md

Validation scenarios:

**Scenario 1: Generate and Load Template**
```bash
# Prerequisites: Python 3.11+, LangAgent installed
langagent init demo-agent
cd demo-agent
# Edit .env with valid MODEL_PROVIDER, MODEL_BASE_URL, OPENAI_API_KEY
langagent run .
# Expected: Agent runs without errors, emits la.lifecycle.init.start and la.runtime.dir_load.ok logs
```

**Scenario 2: Load Minimal Agent**
```bash
# Create minimal fixture: only instructions.md, agent.py, pyproject.toml
mkdir minimal-agent
echo "You are a helpful assistant." > minimal-agent/instructions.md
# (Copy minimal agent.py and pyproject.toml from template)
langagent run minimal-agent
# Expected: LoadedAgent returned with empty tool_ids and skill_names
```

**Scenario 3: Stage Guard Violation Detection**
```python
# In test suite
from langagent.cross_cutting.stage_guard import cross_cutting_stage_guard_decorator

@cross_cutting_stage_guard_decorator('dir_load', monkeypatch_blacklist=[BaseChatModel])
def test_no_model_instantiation():
    model = BaseChatModel()  # Should raise StageCapabilityViolationError

# Expected: Test passes (exception raised), exit code 1
```

**Scenario 4: Idempotent Template Generation**
```bash
langagent init my-agent
# Corrupt instructions.md
echo "INVALID" > my-agent/instructions.md
langagent init my-agent  # Run again
# Expected: Validation fails, instructions.md deleted and recreated, no error
```

References:
- Data model details: [data-model.md](./data-model.md)
- API contracts: [contracts/](./contracts/)
- Error codes: [contracts/error_codes.md](./contracts/error_codes.md)

---

# Constitution Check (Post-Design)

*Re-evaluate Constitution alignment after Phase 1 design complete.*

All Article alignments from initial gate check remain valid. No new violations introduced during design phase.

---

# Next Steps

After Phase 1 completion:
1. Run `/speckit.tasks` to generate tasks.md from this plan
2. Proceed to implementation phase following TDD workflow (Red-Green-Refactor)
3. Create test fixtures (sample_agent, broken_agent) before implementation
4. Implement RuntimeDirLoader and stage_guard modules
5. Verify all 44 functional requirements (FR-001 to FR-044) with corresponding tests
