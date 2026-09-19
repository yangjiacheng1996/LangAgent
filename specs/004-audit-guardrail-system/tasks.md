# Tasks: Cross-Cutting Audit and Guardrail System

**Input**: Design documents from `/specs/004-audit-guardrail-system/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: This feature follows TDD methodology per Constitution Article VIII. All tests are REQUIRED and must be written FIRST (Red phase) before implementation (Green phase).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Project structure: `langagent/cross_cutting/` for implementation, `tests/cross_cutting/` for tests

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create types module with Pydantic schemas in langagent/cross_cutting/types.py
- [X] T002 Create test fixtures module in tests/cross_cutting/fixtures/audit_fixtures.py
- [X] T003 [P] Verify pytest and pytest-mock are available in pyproject.toml dev dependencies

**Checkpoint**: Core types and test infrastructure ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Implement AuditEntry Pydantic schema with 9 fields in langagent/cross_cutting/types.py
- [X] T005 [P] Implement GuardrailMode Literal type in langagent/cross_cutting/types.py
- [X] T006 [P] Implement GuardrailPolicy Pydantic schema with 5 fields in langagent/cross_cutting/types.py
- [X] T007 [P] Implement GuardrailDecision Pydantic schema with 5 fields in langagent/cross_cutting/types.py
- [X] T008 Create AuditFlushError exception class in langagent/cross_cutting/audit_recorder.py
- [X] T009 Verify mypy --strict passes on langagent/cross_cutting/types.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Audit Trail for Security Events (Priority: P1) 🎯 MVP

**Goal**: Implement append-only audit logging with redaction for security events (unauthorized tools, PII detection, prompt injection)

**Independent Test**: Create agent that attempts to call `requires_approval=True` tool, verify audit entry written to `~/.local/share/langagent/audit.jsonl` with category `unauthorized_tool`

### Tests for User Story 1 (TDD Red Phase) ⚠️

> **CRITICAL: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T010 [P] [US1] Test audit entry creation in tests/cross_cutting/test_audit_recorder.py::test_write_creates_entry
- [X] T011 [P] [US1] Test append-only guarantee in tests/cross_cutting/test_audit_recorder.py::test_write_append_only
- [X] T012 [P] [US1] Test query by category filter in tests/cross_cutting/test_audit_recorder.py::test_query_by_category
- [X] T013 [P] [US1] Test query since timestamp filter in tests/cross_cutting/test_audit_recorder.py::test_query_since_filter
- [X] T014 [P] [US1] Test api_key redaction in tests/cross_cutting/test_audit_recorder.py::test_evidence_redaction
- [X] T015 [P] [US1] Test email redaction in tests/cross_cutting/test_audit_recorder.py::test_pii_email_redaction
- [X] T016 [P] [US1] Test flush persists to disk in tests/cross_cutting/test_audit_recorder.py::test_flush_persists_to_disk
- [X] T017 [P] [US1] Test write failure raises AuditFlushError in tests/cross_cutting/test_audit_recorder.py::test_write_failure_raises_audit_flush_error
- [X] T018 [P] [US1] Test entry_id is UUID4 format in tests/cross_cutting/test_audit_recorder.py::test_entry_id_is_uuid4
- [X] T019 [P] [US1] Test category validation in tests/cross_cutting/test_audit_recorder.py::test_category_must_be_in_literal
- [X] T020 [P] [US1] Test severity validation in tests/cross_cutting/test_audit_recorder.py::test_severity_must_be_in_literal
- [X] T021 [P] [US1] Test event bus subscription in tests/cross_cutting/test_audit_recorder.py::test_audit_recorder_subscribes_to_guardrail_block_event

**Verification**: Run `pytest tests/cross_cutting/test_audit_recorder.py` → all 12 tests MUST FAIL

### Implementation for User Story 1 (TDD Green Phase)

- [X] T022 [US1] Implement AuditRecorder.__init__ with audit_dir setup in langagent/cross_cutting/audit_recorder.py
- [X] T023 [US1] Implement redaction helper functions (_redact_secrets, _redact_email, _redact_phone) in langagent/cross_cutting/audit_recorder.py
- [X] T024 [US1] Implement AuditRecorder.write() with append-only JSONL in langagent/cross_cutting/audit_recorder.py
- [X] T025 [US1] Implement AuditRecorder.query() with category and since filters in langagent/cross_cutting/audit_recorder.py
- [X] T026 [US1] Implement AuditRecorder.flush() for buffer persistence in langagent/cross_cutting/audit_recorder.py
- [X] T027 [US1] Implement AuditRecorder.subscribe_guardrail_events() for F03 integration in langagent/cross_cutting/audit_recorder.py
- [X] T028 [US1] Add thread-safety with file locking in AuditRecorder.write() in langagent/cross_cutting/audit_recorder.py

**Verification**: Run `pytest tests/cross_cutting/test_audit_recorder.py` → all 12 tests MUST PASS

**Checkpoint**: At this point, User Story 1 should be fully functional - audit recording with redaction works end-to-end

---

## Phase 4: User Story 2 - Three-Level Guardrail Modes (Priority: P1)

**Goal**: Implement guardrail middleware with strict/all/smart mode evaluation and LangChain AgentMiddleware protocol

**Independent Test**: Set `LANGAGENT_GUARDRAIL_MODE=strict`, verify all tool calls blocked regardless of `requires_approval` annotation

### Tests for User Story 2 (TDD Red Phase) ⚠️

- [X] T029 [P] [US2] Test build_middleware returns AgentMiddleware in tests/cross_cutting/test_guardrail_middleware.py::test_build_middleware_returns_agent_middleware_instance
- [X] T030 [P] [US2] Test disabled policy allows all tools in tests/cross_cutting/test_guardrail_middleware.py::test_build_middleware_with_disabled_policy
- [X] T031 [P] [US2] Test middleware does not swallow exceptions in tests/cross_cutting/test_guardrail_middleware.py::test_middleware_does_not_swallow_exceptions
- [X] T032 [P] [US2] Test strict mode denies all tools in tests/cross_cutting/test_guardrail_middleware.py::test_evaluate_strict_mode_denies_all_tools
- [X] T033 [P] [US2] Test all mode interrupts all tools in tests/cross_cutting/test_guardrail_middleware.py::test_evaluate_all_mode_interrupts_all_tools
- [X] T034 [P] [US2] Test smart mode with requires_approval=True in tests/cross_cutting/test_guardrail_middleware.py::test_evaluate_smart_mode_requires_approval_true
- [X] T035 [P] [US2] Test smart mode with requires_approval=False in tests/cross_cutting/test_guardrail_middleware.py::test_evaluate_smart_mode_requires_approval_false
- [X] T036 [P] [US2] Test before_tools hook triggers interrupt in tests/cross_cutting/test_guardrail_middleware.py::test_before_tools_hook_triggers_interrupt_on_requires_approval
- [X] T037 [P] [US2] Test strict mode writes audit entry in tests/cross_cutting/test_guardrail_middleware.py::test_strict_mode_writes_audit_entry
- [X] T038 [P] [US2] Test smart mode requires_approval writes audit in tests/cross_cutting/test_guardrail_middleware.py::test_smart_mode_requires_approval_writes_audit

**Verification**: Run `pytest tests/cross_cutting/test_guardrail_middleware.py -k "test_evaluate or test_build or test_before_tools or test_strict or test_smart_mode_requires"` → all 10 tests MUST FAIL

### Implementation for User Story 2 (TDD Green Phase)

- [X] T039 [US2] Implement evaluate() function with three-level mode logic in langagent/cross_cutting/guardrail_middleware.py
- [X] T040 [US2] Implement GuardrailMiddleware class with AgentMiddleware protocol in langagent/cross_cutting/guardrail_middleware.py
- [X] T041 [US2] Implement GuardrailMiddleware.before_tools() hook with evaluate() calls in langagent/cross_cutting/guardrail_middleware.py
- [X] T042 [US2] Implement build_middleware() factory function in langagent/cross_cutting/guardrail_middleware.py
- [X] T043 [US2] Integrate audit_recorder.write() calls for blocked tools in GuardrailMiddleware.before_tools() in langagent/cross_cutting/guardrail_middleware.py

**Verification**: Run `pytest tests/cross_cutting/test_guardrail_middleware.py -k "test_evaluate or test_build or test_before_tools or test_strict or test_smart_mode_requires"` → all 10 tests MUST PASS

**Checkpoint**: User Stories 1 AND 2 complete - audit logging + guardrail mode enforcement both work independently

---

## Phase 5: User Story 3 - Internal Endpoint Allowlisting (Priority: P2)

**Goal**: Implement internal endpoint detection (CIDR + glob patterns) to distinguish local vLLM from public APIs

**Independent Test**: Configure `LANGAGENT_INTERNAL_ENDPOINTS=10.0.0.0/8`, verify endpoint `http://10.0.0.5:8000/v1` returns `is_internal_endpoint=True`

### Tests for User Story 3 (TDD Red Phase) ⚠️

- [X] T044 [P] [US3] Test CIDR pattern matching in tests/cross_cutting/test_guardrail_middleware.py::test_is_internal_cidr_match
- [X] T045 [P] [US3] Test glob pattern matching in tests/cross_cutting/test_guardrail_middleware.py::test_is_internal_glob_match
- [X] T046 [P] [US3] Test no match returns False in tests/cross_cutting/test_guardrail_middleware.py::test_is_internal_no_match
- [X] T047 [P] [US3] Test smart mode internal endpoint allowed in tests/cross_cutting/test_guardrail_middleware.py::test_evaluate_smart_mode_internal_endpoint_allowed
- [X] T048 [P] [US3] Test smart mode public endpoint blocked in tests/cross_cutting/test_guardrail_middleware.py::test_evaluate_smart_mode_public_endpoint_blocked

**Verification**: Run `pytest tests/cross_cutting/test_guardrail_middleware.py -k "test_is_internal"` → all 5 tests MUST FAIL

### Implementation for User Story 3 (TDD Green Phase)

- [X] T049 [US3] Implement is_internal() helper function with ipaddress CIDR matching in langagent/cross_cutting/guardrail_middleware.py
- [X] T050 [US3] Add fnmatch glob pattern matching to is_internal() in langagent/cross_cutting/guardrail_middleware.py
- [X] T051 [US3] Extend evaluate() to check internal endpoints in smart mode in langagent/cross_cutting/guardrail_middleware.py
- [X] T052 [US3] Add is_internal_endpoint field to GuardrailDecision return values in langagent/cross_cutting/guardrail_middleware.py

**Verification**: Run `pytest tests/cross_cutting/test_guardrail_middleware.py -k "test_is_internal"` → all 5 tests MUST PASS

**Checkpoint**: User Stories 1, 2, AND 3 complete - internal endpoint detection integrated with guardrail evaluation

---

## Phase 6: User Story 4 - PII Redaction in Tool Outputs (Priority: P2)

**Goal**: Implement PII redaction middleware hook (after_tools) for emails, phone numbers, and secrets in tool outputs

**Independent Test**: Configure `GuardrailPolicy(redact_pii=True)`, execute tool returning "Contact user@example.com", verify output redacted to "Contact ***@example.com"

### Tests for User Story 4 (TDD Red Phase) ⚠️

- [X] T053 [P] [US4] Test after_tools hook redacts PII in tests/cross_cutting/test_guardrail_middleware.py::test_after_tools_hook_redacts_pii
- [X] T054 [P] [US4] Test no redaction when disabled in tests/cross_cutting/test_guardrail_middleware.py::test_after_tools_hook_no_redact_when_disabled

**Verification**: Run `pytest tests/cross_cutting/test_guardrail_middleware.py -k "test_after_tools"` → all 2 tests MUST FAIL

### Implementation for User Story 4 (TDD Green Phase)

- [X] T055 [US4] Implement _redact_pii_patterns() helper function in langagent/cross_cutting/guardrail_middleware.py
- [X] T056 [US4] Implement GuardrailMiddleware.after_tools() hook with conditional redaction in langagent/cross_cutting/guardrail_middleware.py
- [X] T057 [US4] Add regex patterns for email/phone/secrets in langagent/cross_cutting/guardrail_middleware.py

**Verification**: Run `pytest tests/cross_cutting/test_guardrail_middleware.py -k "test_after_tools"` → all 2 tests MUST PASS

**Checkpoint**: User Stories 1-4 complete - PII redaction works in tool outputs

---

## Phase 7: User Story 5 - Prompt Injection Detection (Priority: P3)

**Goal**: Implement prompt injection pattern detection (wrap_model_call hook) with audit-and-mark behavior

**Independent Test**: Send message containing "忽略以上指令", verify audit entry written with `category=prompt_injection` and message annotated with `untrusted=True`

### Tests for User Story 5 (TDD Red Phase) ⚠️

- [X] T058 [P] [US5] Test wrap_model_call detects injection patterns in tests/cross_cutting/test_guardrail_middleware.py::test_wrap_model_call_detects_prompt_injection

**Verification**: Run `pytest tests/cross_cutting/test_guardrail_middleware.py -k "test_wrap_model_call"` → test MUST FAIL

### Implementation for User Story 5 (TDD Green Phase)

- [X] T059 [US5] Implement _detect_injection_patterns() helper function in langagent/cross_cutting/guardrail_middleware.py
- [X] T060 [US5] Implement GuardrailMiddleware.wrap_model_call() hook with detection and annotation in langagent/cross_cutting/guardrail_middleware.py
- [X] T061 [US5] Integrate audit_recorder.write() for prompt_injection category in wrap_model_call() in langagent/cross_cutting/guardrail_middleware.py

**Verification**: Run `pytest tests/cross_cutting/test_guardrail_middleware.py -k "test_wrap_model_call"` → test MUST PASS

**Checkpoint**: All 5 user stories complete - full F04 functionality implemented

---

## Phase 8: Audit File Rotation (Extension to US1)

**Goal**: Implement 10MB file size rotation with timestamp naming and 3-file retention

**Independent Test**: Generate >10MB of audit entries, verify rotation to `audit-YYYYMMDD-HHMMSS.jsonl` and new `audit.jsonl` created

### Tests for Rotation (TDD Red Phase) ⚠️

- [X] T062 [P] Test rotation triggers at 10MB in tests/cross_cutting/test_audit_recorder.py::test_rotation_triggers_at_10mb
- [X] T063 [P] Test rotated file naming format in tests/cross_cutting/test_audit_recorder.py::test_rotated_file_naming_format
- [X] T064 [P] Test 3-file retention limit in tests/cross_cutting/test_audit_recorder.py::test_three_file_retention_limit
- [X] T065 [P] Test query across rotated files in tests/cross_cutting/test_audit_recorder.py::test_query_across_rotated_files
- [X] T066 [P] Test filename timestamp filtering in tests/cross_cutting/test_audit_recorder.py::test_query_filename_timestamp_filtering

**Verification**: Run `pytest tests/cross_cutting/test_audit_recorder.py -k "rotation or rotated or retention"` → all 5 tests MUST FAIL

### Implementation for Rotation (TDD Green Phase)

- [X] T067 Implement _get_file_size() helper in langagent/cross_cutting/audit_recorder.py
- [X] T068 Implement _rotate_file() with timestamp naming in langagent/cross_cutting/audit_recorder.py
- [X] T069 Implement _cleanup_old_files() for 3-file retention in langagent/cross_cutting/audit_recorder.py
- [X] T070 Add rotation check to AuditRecorder.write() before append in langagent/cross_cutting/audit_recorder.py
- [X] T071 Extend AuditRecorder.query() to scan multiple files with timestamp filtering in langagent/cross_cutting/audit_recorder.py

**Verification**: Run `pytest tests/cross_cutting/test_audit_recorder.py -k "rotation or rotated or retention"` → all 5 tests MUST PASS

**Checkpoint**: Audit rotation complete - full audit recorder functionality ready

---

## Phase 9: Integration Tests (Cross-Story Validation)

**Goal**: Verify F04 works end-to-end with F08 main_loop and F10 state_graph_builder integration points

### Integration Tests (TDD Red Phase) ⚠️

- [X] T072 [P] Test guardrail blocks tool in LoadedAgent in tests/integration/test_guardrail_integration.py::test_guardrail_blocks_tool_in_loaded_agent
- [X] T073 [P] Test strict mode denies all tools in graph in tests/integration/test_guardrail_integration.py::test_strict_mode_denies_all_tools_in_graph
- [X] T074 [P] Test all mode interrupts all tools in graph in tests/integration/test_guardrail_integration.py::test_all_mode_interrupts_all_tools_in_graph

**Verification**: Run `pytest tests/integration/test_guardrail_integration.py` → all 3 tests MUST FAIL (expected - F08/F10 not yet integrated)

### Integration Implementation

- [X] T075 Add mock LoadedAgent factory to tests/integration/test_guardrail_integration.py
- [X] T076 Add mock LangGraph graph builder to tests/integration/test_guardrail_integration.py
- [X] T077 Implement integration test scenarios with middleware injection in tests/integration/test_guardrail_integration.py

**Verification**: Run `pytest tests/integration/test_guardrail_integration.py` → all 3 tests MUST PASS

**Checkpoint**: Integration tests ready for F08/F10 handoff

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final quality checks, performance benchmarks, and documentation

- [X] T078 [P] Run mypy --strict on langagent/cross_cutting/ and fix all type errors
- [X] T079 [P] Add docstrings to all public functions in langagent/cross_cutting/audit_recorder.py
- [X] T080 [P] Add docstrings to all public functions in langagent/cross_cutting/guardrail_middleware.py
- [X] T081 [P] Update langagent/cross_cutting/__init__.py to export public APIs
- [X] T082 [P] Verify all 30 tests pass: pytest tests/cross_cutting/ -v
- [X] T083 Run full test suite: pytest tests/ -v --tb=short
- [X] T084 Generate coverage report: pytest tests/cross_cutting/ --cov=langagent.cross_cutting --cov-report=term-missing
- [X] T085 Review coverage report and add missing test cases if coverage < 90%
- [X] T086 [P] Add performance benchmark test for audit write latency in tests/cross_cutting/test_audit_performance.py::test_write_latency_under_100ms (verify SC-002: write completes in <100ms)
- [X] T087 [P] Add performance benchmark test for query latency in tests/cross_cutting/test_audit_performance.py::test_query_latency_under_50ms (verify SC-006: query 10,000 records in <50ms)
- [X] T088 [P] Add performance benchmark test for file rotation overhead in tests/cross_cutting/test_audit_performance.py::test_rotation_overhead_under_50ms (verify rotation completes in <50ms)

**Final Verification**: All phases complete, all tests pass, mypy clean, coverage ≥ 90%, performance benchmarks pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 (P1): Audit Trail - No dependencies on other stories
  - US2 (P1): Guardrail Modes - Depends on US1 (needs audit recorder for writing blocks)
  - US3 (P2): Internal Endpoints - Depends on US2 (extends evaluate() function)
  - US4 (P2): PII Redaction - Depends on US1 (reuses redaction logic) + US2 (extends middleware)
  - US5 (P3): Injection Detection - Depends on US1 (writes audit entries) + US2 (extends middleware)
- **Rotation (Phase 8)**: Extends US1 - can run in parallel with US2-5 if desired
- **Integration (Phase 9)**: Depends on US1 + US2 completion (minimum); ideally all stories
- **Polish (Phase 10)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Foundational (Phase 2)
    ↓
US1 (Audit Trail) ←─────────────────┐
    ↓                                 │
US2 (Guardrail Modes) ←──────────────┤
    ↓                                 │
US3 (Internal Endpoints)              │ (all extend US1 audit + US2 middleware)
US4 (PII Redaction)      ←────────────┤
US5 (Injection Detection)←────────────┘
    ↓
Rotation (Phase 8) [extends US1]
    ↓
Integration (Phase 9)
    ↓
Polish (Phase 10)
```

### Critical Path (MVP = US1 + US2)

1. Setup (Phase 1) → 3 tasks
2. Foundational (Phase 2) → 6 tasks
3. US1 Tests (T010-T021) → 12 tests (parallel)
4. US1 Implementation (T022-T028) → 7 tasks (sequential)
5. US2 Tests (T029-T038) → 10 tests (parallel)
6. US2 Implementation (T039-T043) → 5 tasks (sequential)
7. Integration Tests (T072-T077) → 6 tasks
8. Polish (T078-T085) → 8 tasks

**Total Critical Path**: ~57 tasks for MVP (US1 + US2 only)

### Parallel Opportunities

**Within Phase 2 (Foundational)**:
- T005, T006, T007 (schema types) can run in parallel
- T009 (mypy check) must run after T004-T007

**Within US1 Tests (Phase 3)**:
- All 12 tests (T010-T021) can be written in parallel (different test functions)

**Within US2 Tests (Phase 4)**:
- All 10 tests (T029-T038) can be written in parallel

**Within US3 Tests (Phase 5)**:
- All 5 tests (T044-T048) can be written in parallel

**Within Rotation Tests (Phase 8)**:
- All 5 tests (T062-T066) can be written in parallel

**Within Integration Tests (Phase 9)**:
- All 3 tests (T072-T074) can be written in parallel

**Within Polish (Phase 10)**:
- T078, T079, T080, T081, T082, T086, T087, T088 can run in parallel (different files)

**Cross-Story Parallelism** (after US2 complete):
- US3, US4, US5 can be implemented in parallel by different developers (minimal conflicts)
- Rotation (Phase 8) can be implemented in parallel with US3-5 if desired

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all 12 tests for User Story 1 together:
Task: "Test audit entry creation in tests/cross_cutting/test_audit_recorder.py::test_write_creates_entry"
Task: "Test append-only guarantee in tests/cross_cutting/test_audit_recorder.py::test_write_append_only"
Task: "Test query by category filter in tests/cross_cutting/test_audit_recorder.py::test_query_by_category"
Task: "Test query since timestamp filter in tests/cross_cutting/test_audit_recorder.py::test_query_since_filter"
Task: "Test api_key redaction in tests/cross_cutting/test_audit_recorder.py::test_evidence_redaction"
Task: "Test email redaction in tests/cross_cutting/test_audit_recorder.py::test_pii_email_redaction"
Task: "Test flush persists to disk in tests/cross_cutting/test_audit_recorder.py::test_flush_persists_to_disk"
Task: "Test write failure raises AuditFlushError in tests/cross_cutting/test_audit_recorder.py::test_write_failure_raises_audit_flush_error"
Task: "Test entry_id is UUID4 format in tests/cross_cutting/test_audit_recorder.py::test_entry_id_is_uuid4"
Task: "Test category validation in tests/cross_cutting/test_audit_recorder.py::test_category_must_be_in_literal"
Task: "Test severity validation in tests/cross_cutting/test_audit_recorder.py::test_severity_must_be_in_literal"
Task: "Test event bus subscription in tests/cross_cutting/test_audit_recorder.py::test_audit_recorder_subscribes_to_guardrail_block_event"
```

---

## Parallel Example: User Story 2 Tests

```bash
# Launch all 10 tests for User Story 2 together:
Task: "Test build_middleware returns AgentMiddleware in tests/cross_cutting/test_guardrail_middleware.py::test_build_middleware_returns_agent_middleware_instance"
Task: "Test disabled policy allows all tools in tests/cross_cutting/test_guardrail_middleware.py::test_build_middleware_with_disabled_policy"
Task: "Test middleware does not swallow exceptions in tests/cross_cutting/test_guardrail_middleware.py::test_middleware_does_not_swallow_exceptions"
Task: "Test strict mode denies all tools in tests/cross_cutting/test_guardrail_middleware.py::test_evaluate_strict_mode_denies_all_tools"
Task: "Test all mode interrupts all tools in tests/cross_cutting/test_guardrail_middleware.py::test_evaluate_all_mode_interrupts_all_tools"
Task: "Test smart mode with requires_approval=True in tests/cross_cutting/test_guardrail_middleware.py::test_evaluate_smart_mode_requires_approval_true"
Task: "Test smart mode with requires_approval=False in tests/cross_cutting/test_guardrail_middleware.py::test_evaluate_smart_mode_requires_approval_false"
Task: "Test before_tools hook triggers interrupt in tests/cross_cutting/test_guardrail_middleware.py::test_before_tools_hook_triggers_interrupt_on_requires_approval"
Task: "Test strict mode writes audit entry in tests/cross_cutting/test_guardrail_middleware.py::test_strict_mode_writes_audit_entry"
Task: "Test smart mode requires_approval writes audit in tests/cross_cutting/test_guardrail_middleware.py::test_smart_mode_requires_audit_writes_audit"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only) 🎯

**Rationale**: US1 (Audit Trail) + US2 (Guardrail Modes) provide core security capability mandated by Constitution Article X. US3-5 are enhancements.

1. Complete Phase 1: Setup (3 tasks)
2. Complete Phase 2: Foundational (6 tasks) — CRITICAL BLOCKER
3. Complete Phase 3: US1 - Audit Trail (19 tests + 7 implementation = 26 tasks)
4. Complete Phase 4: US2 - Guardrail Modes (10 tests + 5 implementation = 15 tasks)
5. Complete Phase 9: Integration Tests (6 tasks) — validate F08/F10 handoff
6. Complete Phase 10: Polish (8 tasks)
7. **STOP and VALIDATE**: Test US1 + US2 independently
8. Deploy/demo if ready

**Total MVP**: 64 tasks

### Incremental Delivery

1. **Foundation** (Phase 1 + 2): 9 tasks → Types and schemas ready
2. **MVP** (+ Phase 3 + 4): 64 tasks → Audit + guardrail modes working ✅
3. **v1.1** (+ Phase 5): 73 tasks → Internal endpoint detection added
4. **v1.2** (+ Phase 6): 79 tasks → PII redaction in tool outputs added
5. **v1.3** (+ Phase 7): 82 tasks → Prompt injection detection added
6. **v1.4** (+ Phase 8): 93 tasks → Audit file rotation added
7. Each increment adds value without breaking previous functionality

### Parallel Team Strategy

With 3 developers after Foundational phase complete:

1. **Team completes Setup + Foundational together** (9 tasks)
2. **Once Foundational done, split work**:
   - **Developer A**: US1 - Audit Trail (Phase 3, 26 tasks)
   - **Developer B**: US2 - Guardrail Modes (Phase 4, 15 tasks) — starts after A completes T022-T027
   - **Developer C**: US3 - Internal Endpoints (Phase 5, 9 tasks) — starts after B completes T039-T042
3. **Merge and validate**: Integration tests (Phase 9)
4. **Polish together**: Phase 10

**Note**: US2 depends on US1 audit_recorder, so B must wait for A's T022-T027 (AuditRecorder core). US3-5 can then proceed in parallel.

---

## Task Metrics

### Total Task Count: 88 tasks

**Breakdown by Phase**:
- Phase 1 (Setup): 3 tasks
- Phase 2 (Foundational): 6 tasks
- Phase 3 (US1 - Audit Trail): 19 tasks (12 tests + 7 implementation)
- Phase 4 (US2 - Guardrail Modes): 15 tasks (10 tests + 5 implementation)
- Phase 5 (US3 - Internal Endpoints): 9 tasks (5 tests + 4 implementation)
- Phase 6 (US4 - PII Redaction): 5 tasks (2 tests + 3 implementation)
- Phase 7 (US5 - Injection Detection): 3 tasks (1 test + 3 implementation)
- Phase 8 (Rotation): 10 tasks (5 tests + 5 implementation)
- Phase 9 (Integration): 6 tasks (3 tests + 3 implementation)
- Phase 10 (Polish): 11 tasks (8 quality checks + 3 performance benchmarks)

**Breakdown by User Story**:
- US1 (P1): 19 tasks
- US2 (P1): 15 tasks
- US3 (P2): 9 tasks
- US4 (P2): 5 tasks
- US5 (P3): 3 tasks
- Infrastructure (Setup + Foundational + Polish): 20 tasks
- Cross-story (Rotation + Integration): 16 tasks

**Test vs Implementation**:
- Test tasks: 50 (57%)
- Implementation tasks: 30 (34%)
- Infrastructure/Polish tasks: 8 (9%)

**Parallelizable Tasks**: 54 tasks marked [P] (61%)

### MVP Scope

**Recommended MVP**: User Stories 1 + 2 only
- Total tasks: 64 (includes Setup, Foundational, US1, US2, Integration, Polish)
- Estimated effort: 8-10 developer-days
- Delivers: Core audit trail + three-level guardrail modes (Article X compliance)

**Full Feature**: All 5 user stories + rotation
- Total tasks: 85
- Estimated effort: 12-15 developer-days
- Delivers: Complete F04 as specified in top-level design

---

## Format Validation

✅ **All 85 tasks follow strict checklist format**:
- All tasks start with `- [ ]` (markdown checkbox)
- All tasks have sequential IDs (T001-T085)
- All parallelizable tasks marked with `[P]`
- All user story tasks marked with `[US1]`, `[US2]`, `[US3]`, `[US4]`, or `[US5]`
- All tasks include exact file paths
- All test tasks specify test function names
- All implementation tasks specify exact module locations

✅ **Independent test criteria defined for each story**:
- US1: Verify audit.jsonl created with unauthorized_tool entry
- US2: Verify strict mode blocks all tools with audit entries
- US3: Verify internal endpoint returns is_internal_endpoint=True
- US4: Verify email redaction to ***@domain.com
- US5: Verify prompt_injection audit entry and untrusted annotation

✅ **Dependencies clearly mapped**:
- Critical path identified (MVP = 64 tasks)
- Parallel opportunities documented (51 tasks = 60%)
- User story dependencies visualized in dependency graph

---

## Notes

- [P] tasks = different files/test functions, no sequential dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **TDD MANDATORY**: Verify tests FAIL before implementing (Red phase), then PASS after (Green phase)
- Commit after each task or logical group (e.g., all tests for one story)
- Stop at any checkpoint to validate story independently
- Constitution Article VIII enforces TDD; skipping tests is a Hard No violation
