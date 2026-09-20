# Tasks: Protocol Layer Skill + Tool Loading

**Input**: Design documents from `/specs/005-protocol-skill-tool-loader/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: This feature follows TDD approach. All tests MUST be written FIRST and FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Module Naming**: In task descriptions, module names use simplified forms (e.g., `skill_loader`, `tool_registry`) which correspond to their full qualified names (`protocol_skill_loader`, `protocol_tool_registry`) in the spec. All modules are located in the `langagent/protocol/` directory.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- Source: `langagent/protocol/` - Protocol layer modules
- Tests: `tests/protocol/` - Test modules
- Fixtures: `tests/fixtures/sample_agent/` - Test data

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create directory structure for protocol layer modules in langagent/protocol/
- [ ] T002 Create directory structure for test fixtures in tests/fixtures/sample_agent/skills/ and tests/fixtures/sample_agent/tools/
- [ ] T003 [P] Create schema module stubs: langagent/protocol/skill_schemas.py and langagent/protocol/tool_schemas.py
- [ ] T004 [P] Create loader module stubs: langagent/protocol/skill_loader.py and langagent/protocol/tool_registry.py
- [ ] T005 [P] Create custom exception classes in langagent/protocol/skill_schemas.py (SkillFrontmatterParseError with exit_code=65)
- [ ] T006 [P] Create custom exception classes in langagent/protocol/tool_schemas.py (ToolIdDuplicateError with exit_code=70)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 Define SkillFrontmatter dataclass (frozen) in langagent/protocol/skill_schemas.py with fields: name, description, version, author, tags, requires
- [ ] T008 Define SkillSpec dataclass (frozen) in langagent/protocol/skill_schemas.py with all SkillFrontmatter fields + body_path, enabled
- [ ] T009 Define ToolSpec Pydantic BaseModel in langagent/protocol/tool_schemas.py with fields: tool_id, tool_name, description, args_schema, enabled, requires_approval
- [ ] T010 Add semver regex validation constant (^v\d+\.\d+\.\d+$) in langagent/protocol/skill_schemas.py
- [ ] T011 Add JSON Schema Draft 7 minimal fallback constant in langagent/protocol/tool_schemas.py
- [ ] T012 Verify F02 cross_cutting_logger is available for import (check langagent/cross_cutting/logger.py exists)
- [ ] T013 Verify F03 protocol_event_bus is available for import (check langagent/protocol/event_bus.py exists)
- [ ] T014 Verify F01 primitives_langchain_types.BaseTool is available for import (check langagent/primitives/langchain_types.py exists)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Load Skills from Agent Directory (Priority: P1) 🎯 MVP

**Goal**: Parse YAML frontmatter from SKILL.md files and produce SkillSpec objects with semver validation

**Independent Test**: Create sample agent directory with 1-3 skills, call `protocol_skill_loader.load_all(skills_dir)`, verify returned SkillSpec list matches expectations

### Tests for User Story 1 (TDD - Write these tests FIRST) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T015 [P] [US1] Test fixture: Create tests/fixtures/sample_agent/skills/test/SKILL.md with valid YAML frontmatter (all required + optional fields)
- [ ] T016 [P] [US1] Test fixture: Create tests/fixtures/sample_agent/skills/malformed/SKILL.md missing required name field
- [ ] T017 [P] [US1] Test fixture: Create tests/fixtures/sample_agent/skills/invalid_semver/SKILL.md with version="1.0" (not semver)
- [ ] T018 [P] [US1] Test: test_load_all_empty_dir in tests/protocol/test_skill_loader.py - verify empty list when skills/ doesn't exist
- [ ] T019 [P] [US1] Test: test_load_all_single_skill in tests/protocol/test_skill_loader.py - verify 1 SkillSpec returned with all fields populated
- [ ] T020 [P] [US1] Test: test_load_all_multiple_skills in tests/protocol/test_skill_loader.py - create 3 skill fixtures, verify 3 SkillSpec returned in traversal order
- [ ] T021 [P] [US1] Test: test_parse_frontmatter_valid in tests/protocol/test_skill_loader.py - verify SkillFrontmatter instance returned
- [ ] T022 [P] [US1] Test: test_parse_frontmatter_missing_name in tests/protocol/test_skill_loader.py - verify SkillFrontmatterParseError raised with exit_code=65
- [ ] T023 [P] [US1] Test: test_parse_frontmatter_missing_description in tests/protocol/test_skill_loader.py - verify SkillFrontmatterParseError raised
- [ ] T024 [P] [US1] Test: test_parse_frontmatter_version_not_semver in tests/protocol/test_skill_loader.py - verify error for "1.0"
- [ ] T025 [P] [US1] Test: test_parse_frontmatter_invalid_yaml in tests/protocol/test_skill_loader.py - verify yaml.YAMLError wrapped as SkillFrontmatterParseError
- [ ] T026 [P] [US1] Test: test_skill_body_path_resolved in tests/protocol/test_skill_loader.py - verify SkillSpec.body_path is absolute
- [ ] T027 [P] [US1] Test: test_skill_enabled_default_true in tests/protocol/test_skill_loader.py - verify enabled=True when not in frontmatter
- [ ] T028 [P] [US1] Test: test_skill_publishes_skill_loaded_event in tests/protocol/test_skill_loader.py - mock event bus, verify skill_loaded event
- [ ] T029 [P] [US1] Test: test_skill_publishes_skill_load_failed_event in tests/protocol/test_skill_loader.py - verify skill_load_failed event for missing field

### Implementation for User Story 1

- [ ] T030 [US1] Implement parse_frontmatter() in langagent/protocol/skill_loader.py - extract YAML from Markdown, validate required fields
- [ ] T031 [US1] Add semver regex validation to parse_frontmatter() - raise SkillFrontmatterParseError if version doesn't match ^v\d+\.\d+\.\d+$
- [ ] T032 [US1] Add default value handling for optional fields (author=None, tags=[], requires=[]) in parse_frontmatter()
- [ ] T033 [US1] Implement load_all() in langagent/protocol/skill_loader.py - scan skills_dir subdirectories for SKILL.md files
- [ ] T034 [US1] Add fail-soft error handling to load_all() - skip individual failures, continue loading others
- [ ] T035 [US1] Add event bus integration to load_all() - publish skill_loaded for success, skill_load_failed for failures
- [ ] T036 [US1] Add logging integration to load_all() - log with tag la.runtime.skill_load_failed for failures
- [ ] T037 [US1] Add body_path resolution to load_all() - use os.path.abspath() for SkillSpec.body_path
- [ ] T038 [US1] Run test suite - verify all User Story 1 tests pass: pytest tests/protocol/test_skill_loader.py -v

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Load Tools from Agent Directory (Priority: P1)

**Goal**: Dynamically import Python modules, extract BaseTool instances, produce ToolSpec objects with args_schema and requires_approval metadata

**Independent Test**: Create sample `tools/echo.py` with LangChain BaseTool subclass, call `protocol_tool_registry.register_all(tools_dir)`, verify returned ToolSpec list matches expectations

### Tests for User Story 2 (TDD - Write these tests FIRST) ⚠️

- [ ] T039 [P] [US2] Test fixture: Create tests/fixtures/sample_agent/tools/echo.py with BaseTool instance named echo
- [ ] T040 [P] [US2] Test fixture: Create tests/fixtures/sample_agent/tools/dangerous.py with REQUIRES_APPROVAL=True
- [ ] T041 [P] [US2] Test fixture: Create tests/fixtures/sample_agent/tools/safe.py without REQUIRES_APPROVAL constant
- [ ] T042 [P] [US2] Test fixture: Create tests/fixtures/sample_agent/tools/duplicate_echo.py with same tool_id as echo.py
- [ ] T043 [P] [US2] Test: test_register_all_empty_dir in tests/protocol/test_tool_registry.py - verify empty list when tools/ doesn't exist
- [ ] T044 [P] [US2] Test: test_register_all_single_tool in tests/protocol/test_tool_registry.py - verify 1 ToolSpec with tool_id=="echo"
- [ ] T045 [P] [US2] Test: test_register_all_multiple_tools in tests/protocol/test_tool_registry.py - create 3 tool fixtures, verify 3 ToolSpec returned
- [ ] T046 [P] [US2] Test: test_tool_requires_approval_default_false in tests/protocol/test_tool_registry.py - verify requires_approval==False for safe.py
- [ ] T047 [P] [US2] Test: test_tool_requires_approval_from_constant in tests/protocol/test_tool_registry.py - verify requires_approval==True for dangerous.py
- [ ] T048 [P] [US2] Test: test_tool_args_schema_extracted in tests/protocol/test_tool_registry.py - verify args_schema contains $schema=="http://json-schema.org/draft-07/schema#"
- [ ] T049 [P] [US2] Test: test_tool_id_duplicate in tests/protocol/test_tool_registry.py - verify ToolIdDuplicateError raised with exit_code=70
- [ ] T050 [P] [US2] Test: test_tool_dynamic_import_no_sys_path_pollution in tests/protocol/test_tool_registry.py - verify sys.path length unchanged
- [ ] T051 [P] [US2] Test: test_tool_get_by_id in tests/protocol/test_tool_registry.py - verify get_by_id("echo") returns ToolSpec, get_by_id("missing") returns None
- [ ] T052 [P] [US2] Test: test_tool_publishes_tool_registered_event in tests/protocol/test_tool_registry.py - mock event bus, verify tool_registered event

### Implementation for User Story 2

- [ ] T053 [US2] Implement _load_tool_from_file() helper in langagent/protocol/tool_registry.py - dynamic import with importlib.util.spec_from_file_location()
- [ ] T054 [US2] Add unique namespace generation to _load_tool_from_file() - use f"langagent_dynamic_tool_{tool_id}" as module name
- [ ] T055 [US2] Add strict filename matching validation to _load_tool_from_file() - verify exported variable name matches filename (e.g., echo.py must export echo)
- [ ] T056 [US2] Add REQUIRES_APPROVAL constant reading to _load_tool_from_file() - default to False if not present
- [ ] T057 [US2] Add args_schema extraction to _load_tool_from_file() - use BaseTool.args_schema.model_json_schema() with JSON Schema Draft 7
- [ ] T058 [US2] Add args_schema fallback to _load_tool_from_file() - use minimal valid JSON Schema when BaseTool.args_schema is None
- [ ] T059 [US2] Implement register_all() in langagent/protocol/tool_registry.py - scan tools_dir for .py files, call _load_tool_from_file() for each
- [ ] T060 [US2] Add tool_id uniqueness check to register_all() - maintain dict registry, raise ToolIdDuplicateError if duplicate found
- [ ] T061 [US2] Add sys.modules cleanup to register_all() - call sys.modules.pop(f"langagent_dynamic_tool_{tool_id}", None) before return
- [ ] T062 [US2] Add event bus integration to register_all() - publish tool_registered for success, tool_load_failed for failures
- [ ] T063 [US2] Add logging integration to register_all() - log with tag la.runtime.tool_load_failed for failures
- [ ] T064 [US2] Implement get_by_id() in langagent/protocol/tool_registry.py - O(1) lookup via internal dict registry
- [ ] T065 [US2] Run test suite - verify all User Story 2 tests pass: pytest tests/protocol/test_tool_registry.py -v

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Fail-Soft Loading with Event Bus Reporting (Priority: P2)

**Goal**: Skip failing items, emit diagnostic events, continue loading remaining items without blocking initialization

**Independent Test**: Create mixed directory with 1 valid skill + 1 malformed skill + 1 valid tool + 1 tool with syntax error, verify valid items returned and failed items produce `*_load_failed` events

### Tests for User Story 3 (TDD - Write these tests FIRST) ⚠️

- [ ] T066 [P] [US3] Test fixture: Create tests/fixtures/sample_agent/tools/syntax_error.py with intentional Python syntax error
- [ ] T067 [P] [US3] Test fixture: Create tests/fixtures/sample_agent/tools/import_error.py that imports non-existent module
- [ ] T068 [P] [US3] Test: test_skill_loader_handles_malformed_skill_gracefully in tests/protocol/test_skill_loader.py - 1 valid + 1 malformed → 1 SkillSpec + 1 skill_load_failed event, no exceptions
- [ ] T069 [P] [US3] Test: test_tool_registry_handles_import_error_gracefully in tests/protocol/test_tool_registry.py - 1 valid + 1 syntax_error.py → 1 ToolSpec + 1 tool_load_failed event, no exceptions
- [ ] T070 [P] [US3] Test: test_tool_registry_handles_import_error_missing_dependency in tests/protocol/test_tool_registry.py - verify ImportError caught and tool skipped
- [ ] T071 [P] [US3] Test: test_skill_load_failed_event_contains_details in tests/protocol/test_tool_registry.py - verify skill_load_failed event contains path, error message, timestamp

### Implementation for User Story 3

- [ ] T072 [US3] Add SyntaxError handling to _load_tool_from_file() in langagent/protocol/tool_registry.py - catch and emit tool_load_failed
- [ ] T073 [US3] Add ImportError handling to _load_tool_from_file() in langagent/protocol/tool_registry.py - catch and emit tool_load_failed
- [ ] T074 [US3] Add ModuleNotFoundError handling to _load_tool_from_file() in langagent/protocol/tool_registry.py - catch and emit tool_load_failed
- [ ] T075 [US3] Add detailed error message logging to _load_tool_from_file() - include exception type, message, traceback summary
- [ ] T076 [US3] Verify fail-soft behavior in load_all() - ensure YAML errors don't propagate, skill_load_failed events emitted with error details
- [ ] T077 [US3] Run test suite - verify all User Story 3 tests pass: pytest tests/protocol/test_skill_loader.py::test_skill_loader_handles_malformed_skill_gracefully -v
- [ ] T078 [US3] Run test suite - verify all User Story 3 tests pass: pytest tests/protocol/test_tool_registry.py -k "gracefully or import_error" -v

**Checkpoint**: All user stories should now handle errors gracefully without blocking

---

## Phase 6: User Story 4 - Dynamic Import with sys.modules Cleanup (Priority: P2)

**Goal**: Use unique module namespaces, clean up sys.modules entries after loading to prevent memory leaks and namespace collisions

**Independent Test**: Check sys.modules before and after `register_all()` calls, verify no `langagent_dynamic_tool_*` entries remain, sys.path length unchanged

### Tests for User Story 4 (TDD - Write these tests FIRST) ⚠️

- [ ] T079 [P] [US4] Test: test_tool_loader_cleans_sys_modules_on_register in tests/protocol/test_tool_registry.py - verify sys.modules has zero langagent_dynamic_tool_* entries after register_all()
- [ ] T080 [P] [US4] Test: test_tool_loader_cleans_sys_modules_on_failure in tests/protocol/test_tool_registry.py - verify failed tool doesn't pollute sys.modules
- [ ] T081 [P] [US4] Test: test_sys_path_length_unchanged_after_tool_loading in tests/protocol/test_tool_registry.py - verify sys.path length before == after

### Implementation for User Story 4

- [ ] T082 [US4] Verify sys.modules cleanup logic in register_all() - ensure sys.modules.pop() called for EACH loaded tool before return (success or failure)
- [ ] T083 [US4] Verify sys.path pollution prevention - ensure importlib.util.spec_from_file_location() does NOT modify sys.path
- [ ] T084 [US4] Run test suite - verify all User Story 4 tests pass: pytest tests/protocol/test_tool_registry.py -k "sys_modules or sys_path" -v

**Checkpoint**: All user stories should now be independently functional with zero resource leaks

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T085 [P] Add type hints to all public functions in langagent/protocol/skill_loader.py (load_all, parse_frontmatter)
- [ ] T086 [P] Add type hints to all public functions in langagent/protocol/tool_registry.py (register_all, get_by_id)
- [ ] T087 [P] Add docstrings to all public functions per Google Python Style Guide
- [ ] T088 [P] Add __all__ exports to langagent/protocol/skill_loader.py
- [ ] T089 [P] Add __all__ exports to langagent/protocol/tool_registry.py
- [ ] T090 [P] Add __all__ exports to langagent/protocol/skill_schemas.py
- [ ] T091 [P] Add __all__ exports to langagent/protocol/tool_schemas.py
- [ ] T092 Run mypy --strict on langagent/protocol/skill_loader.py and langagent/protocol/skill_schemas.py - verify zero type errors
- [ ] T093 Run mypy --strict on langagent/protocol/tool_registry.py and langagent/protocol/tool_schemas.py - verify zero type errors
- [ ] T094 Run full test suite with coverage: pytest tests/protocol/test_skill_loader.py tests/protocol/test_tool_registry.py -v --cov=langagent/protocol --cov-report=term-missing
- [ ] T095 Verify coverage >90% on skill_loader.py, tool_registry.py, skill_schemas.py, tool_schemas.py
- [ ] T096 Run performance benchmark: Load 100 skills, verify completes in <2s (SC-001) - Use pytest-benchmark plugin for measurement and reporting
- [ ] T097 Run performance benchmark: Load 50 tools with complex args_schema, verify completes in <3s (SC-002) - Use pytest-benchmark plugin for measurement and reporting
- [ ] T098 Run performance benchmark: Tool registry query latency, verify <1ms (SC-006)
- [ ] T099 Update langagent/protocol/__init__.py to export SkillSpec, SkillFrontmatter, ToolSpec, load_all, register_all, get_by_id
- [ ] T100 Code cleanup: Remove any debug print statements, ensure all logging uses cross_cutting_logger
- [ ] T101 Code cleanup: Ensure all exception messages are user-friendly and include actionable guidance

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User Story 1 (P1 - Skills): Can start after Foundational
  - User Story 2 (P1 - Tools): Can start after Foundational (parallel with US1)
  - User Story 3 (P2 - Fail-Soft): Depends on US1 and US2 implementations
  - User Story 4 (P2 - Cleanup): Depends on US2 implementation (tools use dynamic import)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories - CAN RUN IN PARALLEL with US1
- **User Story 3 (P2)**: Depends on US1 and US2 implementations (extends error handling for both)
- **User Story 4 (P2)**: Depends on US2 implementation (sys.modules cleanup for dynamic import)

### Within Each User Story

- Tests (fixtures + test cases) MUST be written and FAIL before implementation
- Implementation tasks must follow test order (implement to make tests pass incrementally)
- Each user story ends with running its test suite to verify completion

### Parallel Opportunities

- Phase 1 Setup: T003-T006 can run in parallel (different files)
- Phase 2 Foundational: T007-T011 can run in parallel (different schema files)
- User Story 1 Tests: T015-T029 can run in parallel (different test files/fixtures)
- User Story 2 Tests: T039-T052 can run in parallel (different test files/fixtures)
- User Story 3 Tests: T066-T071 can run in parallel (different test files/fixtures)
- User Story 4 Tests: T079-T081 can run in parallel (different test functions)
- **User Story 1 and User Story 2 can be implemented in parallel by different team members** (after Foundational phase)
- Phase 7 Polish: T085-T091 can run in parallel (different files)

---

## Parallel Example: User Story 1 and User Story 2

```bash
# Team Member A works on User Story 1 (Skills):
# Write tests T015-T029 → Implement T030-T038

# Team Member B works on User Story 2 (Tools) IN PARALLEL:
# Write tests T039-T052 → Implement T053-T065

# Both stories complete independently, then merge
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Skills) **OR** Phase 4: User Story 2 (Tools) - either one is MVP
4. **STOP and VALIDATE**: Test selected story independently
5. Optional: Complete the other P1 story for full MVP (Skills + Tools)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (Skills) → Test independently → MVP Checkpoint
3. Add User Story 2 (Tools) → Test independently → MVP Complete
4. Add User Story 3 (Fail-Soft) → Test independently → Production Ready
5. Add User Story 4 (Cleanup) → Test independently → Long-Running Process Ready
6. Add Phase 7 (Polish) → Full Feature Complete

### Parallel Team Strategy

With 2+ developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Skills) - T015-T038
   - Developer B: User Story 2 (Tools) - T039-T065
3. Both stories complete independently, then merge
4. Team completes User Story 3 & 4 together (builds on both US1 and US2)
5. Team completes Polish phase together

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **TDD MANDATORY**: Verify tests fail (RED) before implementing (GREEN)
- Commit after each logical group of tasks (e.g., after all tests for a story, after implementation for a story)
- Stop at any checkpoint to validate story independently
- **User Stories 1 and 2 are both P1 and can be developed in parallel** - they are the dual MVP (Skills + Tools)
- User Stories 3 and 4 enhance resilience and production-readiness but are not blocking for initial functionality
- Total estimated tasks: 101 tasks
- Estimated MVP (US1 + US2): ~70 tasks
- Estimated time (single developer, sequential): 5-7 days
- Estimated time (2 developers, parallel US1/US2): 3-4 days
