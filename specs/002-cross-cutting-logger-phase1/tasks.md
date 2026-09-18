# Tasks: Cross-Cutting Logger + EventBusProtocol (F02 Phase 1)

**Input**: Design documents from `/specs/002-cross-cutting-logger-phase1/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md

**Tests**: This feature follows TDD (Test-Driven Development) per Constitution Article VIII. All tests MUST be written first and FAIL before implementation begins.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Project uses single project structure with Python:
- **Source**: `langagent/cross_cutting/` at repository root
- **Tests**: `tests/cross_cutting/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for F02 Phase 1

- [ ] T001 Create directory structure `langagent/cross_cutting/` if not exists
- [ ] T002 [P] Create `langagent/cross_cutting/__init__.py` with module exports
- [ ] T003 [P] Create `tests/cross_cutting/` directory for test files
- [ ] T004 [P] Create `tests/fixtures/` directory for test fixtures

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core types and constants that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Define `Span` dataclass with 7 fields in `langagent/cross_cutting/logger.py` (trace_id, span_id, parent_span_id, name, start, end, attributes per FR-019)
- [ ] T006 [P] Define `LogLevel` Literal type in `langagent/cross_cutting/logger.py` (DEBUG/INFO/WARNING/ERROR/CRITICAL per FR-008)
- [ ] T007 [P] Define `ALLOWED_TAGS` frozenset with 46 tags in `langagent/cross_cutting/logger.py` per research.md section 4
- [ ] T008 [P] Define custom exceptions `UnknownLogTagError` and `SpanDrainError` in `langagent/cross_cutting/logger.py`
- [ ] T009 [P] Create `_REDACT_KEYS` frozenset in `langagent/cross_cutting/logger.py` with 4 sensitive field names (api_key, password, secret, token per FR-004)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Structured Logging with Tag Whitelist (Priority: P1) 🎯 MVP

**Goal**: Enable developers to emit structured logs with validated tags to stderr in dual format (text + JSONL)

**Independent Test**: Call `emit()` with valid/invalid tags and verify stderr output contains both text and JSONL with proper validation

### Tests for User Story 1 (TDD - Write FIRST, ensure they FAIL)

- [ ] T010 [P] [US1] Write test `test_emit_with_valid_tag` in `tests/cross_cutting/test_logger.py` - verify dual format output to stderr
- [ ] T011 [P] [US1] Write test `test_emit_with_unknown_tag` in `tests/cross_cutting/test_logger.py` - verify UnknownLogTagError raised
- [ ] T012 [P] [US1] Write test `test_emit_emits_jsonl_to_stderr_not_stdout` in `tests/cross_cutting/test_logger.py` - verify no stdout pollution
- [ ] T013 [P] [US1] Write test `test_emit_thread_safe` in `tests/cross_cutting/test_logger.py` - verify 10 threads concurrent emit without interleaving
- [ ] T014 [P] [US1] Write test `test_emit_tag_whitelist_at_least_46` in `tests/cross_cutting/test_logger.py` - verify ALLOWED_TAGS has 46 items
- [ ] T015 [P] [US1] Write test `test_emit_timestamp_is_iso8601` in `tests/cross_cutting/test_logger.py` - verify timestamp format
- [ ] T016 [P] [US1] Write test `test_emit_payload_must_be_dict` in `tests/cross_cutting/test_logger.py` - verify TypeError on non-dict payload

**Checkpoint**: Run tests - all 7 tests must FAIL (Red phase)

### Implementation for User Story 1

- [ ] T017 [US1] Implement `_generate_timestamp()` function in `langagent/cross_cutting/logger.py` using datetime.now(timezone.utc).astimezone().isoformat()
- [ ] T018 [US1] Implement `_infer_tag_level()` function in `langagent/cross_cutting/logger.py` - map tags to log levels based on suffix
- [ ] T019 [US1] Implement module-level state: `_emit_lock`, `_current_level` in `langagent/cross_cutting/logger.py`
- [ ] T020 [US1] Implement `emit(tag: str, payload: dict[str, Any]) -> None` core logic in `langagent/cross_cutting/logger.py`:
  - Validate tag in ALLOWED_TAGS (FR-002, FR-003)
  - Validate payload is dict (FR-020)
  - Check log level filtering (FR-007)
  - Acquire lock
  - Generate timestamp
  - Write text format to stderr (FR-001)
  - Write JSONL format to stderr (FR-001)
  - Handle I/O errors with fire-and-forget semantics (FR-017)
- [ ] T021 [US1] Implement `set_level(level: LogLevel) -> None` in `langagent/cross_cutting/logger.py` with validation (FR-008)

**Checkpoint**: Run User Story 1 tests - all 7 tests must PASS (Green phase)

---

## Phase 4: User Story 2 - Secret Redaction (Priority: P1)

**Goal**: Automatically redact sensitive fields (api_key, password, secret, token) in logs to prevent credential leaks

**Independent Test**: Call `emit()` with payloads containing sensitive fields and verify output shows `***` instead of actual values

### Tests for User Story 2 (TDD - Write FIRST)

- [ ] T022 [P] [US2] Write test `test_emit_does_not_contain_secrets` in `tests/cross_cutting/test_logger.py` - verify api_key redaction
- [ ] T023 [P] [US2] Write test `test_emit_does_not_contain_password` in `tests/cross_cutting/test_logger.py` - verify password redaction
- [ ] T024 [P] [US2] Write test `test_emit_does_not_contain_secret` in `tests/cross_cutting/test_logger.py` - verify secret redaction
- [ ] T025 [P] [US2] Write test `test_emit_does_not_contain_token` in `tests/cross_cutting/test_logger.py` - verify token redaction with exact match (not substring)

**Checkpoint**: Run tests - all 4 tests must FAIL

### Implementation for User Story 2

- [ ] T026 [US2] Implement `_redact(payload: dict[str, Any]) -> dict[str, Any]` function in `langagent/cross_cutting/logger.py`:
  - Deep recursive traversal for nested dicts (FR-006)
  - Handle lists containing dicts (FR-006)
  - Exact field name matching using _REDACT_KEYS (FR-004, FR-005)
  - Return new dict (immutability)
  - Replace matched values with `"***"`
- [ ] T027 [US2] Integrate `_redact()` call into `emit()` before writing to stderr in `langagent/cross_cutting/logger.py`

**Checkpoint**: Run User Story 2 tests - all 4 tests must PASS

---

## Phase 5: User Story 3 - Log Level Filtering (Priority: P2)

**Goal**: Allow operators to adjust log verbosity at runtime to reduce noise or increase detail

**Independent Test**: Call `set_level("ERROR")` and verify INFO-level logs don't appear in stderr

### Tests for User Story 3 (TDD - Write FIRST)

- [ ] T028 [P] [US3] Write test `test_emit_filters_by_level` in `tests/cross_cutting/test_logger.py` - verify INFO logs filtered when level=ERROR
- [ ] T029 [P] [US3] Write test `test_set_level_valid_values` in `tests/cross_cutting/test_logger.py` - verify only 5 valid levels accepted

**Checkpoint**: Run tests - both tests must FAIL

### Implementation for User Story 3

- [ ] T030 [US3] Implement `_LEVEL_VALUES` dict mapping level names to numeric values in `langagent/cross_cutting/logger.py` (DEBUG=10, INFO=20, WARNING=30, ERROR=40, CRITICAL=50)
- [ ] T031 [US3] Update `set_level()` to validate level against _LEVEL_VALUES keys and update _current_level in `langagent/cross_cutting/logger.py`
- [ ] T032 [US3] Update `emit()` to call `_infer_tag_level()` and compare with _current_level before emission in `langagent/cross_cutting/logger.py`

**Checkpoint**: Run User Story 3 tests - both tests must PASS

---

## Phase 6: User Story 4 - Span Buffer for Tracing (Priority: P2)

**Goal**: Accumulate span logs in memory buffer for F09 to drain and persist to disk during exit_cleanup

**Independent Test**: Emit multiple span logs, call `drain_spans()`, verify returned list and buffer cleared

### Tests for User Story 4 (TDD - Write FIRST)

- [ ] T033 [P] [US4] Write test `test_drain_spans_returns_accumulated` in `tests/cross_cutting/test_logger.py` - verify 5 span emits return 5 Span objects
- [ ] T034 [P] [US4] Write test `test_drain_spans_filters_non_span_emits` in `tests/cross_cutting/test_logger.py` - verify non-span logs not in buffer
- [ ] T035 [P] [US4] Write test `test_drain_spans_clears_buffer` in `tests/cross_cutting/test_logger.py` - verify buffer cleared after drain
- [ ] T036 [P] [US4] Write test `test_drain_spans_empty_when_no_pending` in `tests/cross_cutting/test_logger.py` - verify empty list on empty buffer
- [ ] T037 [P] [US4] Write test `test_drain_spans_thread_safe` in `tests/cross_cutting/test_logger.py` - verify 10 threads concurrent emit+drain without data loss
- [ ] T038 [P] [US4] Write test `test_drain_spans_raises_span_drain_error_on_io_failure` in `tests/cross_cutting/test_logger.py` - verify SpanDrainError on failure and buffer not cleared

**Checkpoint**: Run tests - all 6 tests must FAIL

### Implementation for User Story 4

- [ ] T039 [US4] Implement module-level `_span_buffer: list[Span] = []` in `langagent/cross_cutting/logger.py`
- [ ] T040 [US4] Implement module-level `_buffer_lock = threading.Lock()` in `langagent/cross_cutting/logger.py`
- [ ] T041 [US4] Update `emit()` to detect `payload.get("kind") == "span"` and construct Span from payload fields in `langagent/cross_cutting/logger.py` (FR-009)
- [ ] T042 [US4] Update `emit()` to append Span to _span_buffer under _buffer_lock in `langagent/cross_cutting/logger.py`
- [ ] T043 [US4] Implement `drain_spans() -> list[Span]` in `langagent/cross_cutting/logger.py`:
  - Acquire _buffer_lock
  - Return empty list if buffer empty
  - Copy buffer to local variable
  - Clear _span_buffer only if no exception (FR-011)
  - Return copied spans (FR-010)

**Checkpoint**: Run User Story 4 tests - all 6 tests must PASS

---

## Phase 7: User Story 5 - EventBusProtocol Interface Definition (Priority: P3)

**Goal**: Define EventBusProtocol interface contract for F03 event bus implementation with full type safety

**Independent Test**: Create mock class implementing EventBusProtocol and verify mypy --strict passes

### Tests for User Story 5 (TDD - Write FIRST)

- [ ] T044 [P] [US5] Write test `test_event_bus_protocol_has_publish_method` in `tests/cross_cutting/test_event_bus_protocol.py` - verify Protocol has publish signature
- [ ] T045 [P] [US5] Write test `test_event_bus_protocol_has_subscribe_method` in `tests/cross_cutting/test_event_bus_protocol.py` - verify Protocol has subscribe signature returning str
- [ ] T046 [P] [US5] Write test `test_event_bus_protocol_has_unsubscribe_method` in `tests/cross_cutting/test_event_bus_protocol.py` - verify Protocol has unsubscribe signature
- [ ] T047 [P] [US5] Write test `test_event_bus_protocol_has_flush_method` in `tests/cross_cutting/test_event_bus_protocol.py` - verify Protocol has flush signature
- [ ] T048 [P] [US5] Write test `test_event_bus_protocol_mypy_strict_passes` in `tests/cross_cutting/test_event_bus_protocol.py` - verify mock implementation type checks

**Checkpoint**: Run tests - all 5 tests must FAIL

### Implementation for User Story 5

- [ ] T049 [US5] Define `EventBusProtocol` class with `@runtime_checkable` Protocol decorator in `langagent/cross_cutting/logger.py` (FR-015)
- [ ] T050 [US5] Add `publish(self, event_type: str, payload: dict[str, Any]) -> None` method signature to EventBusProtocol in `langagent/cross_cutting/logger.py`
- [ ] T051 [US5] Add `subscribe(self, event_type: str, callback: Callable[[dict[str, Any]], None]) -> str` method signature to EventBusProtocol in `langagent/cross_cutting/logger.py`
- [ ] T052 [US5] Add `unsubscribe(self, subscription_id: str) -> None` method signature to EventBusProtocol in `langagent/cross_cutting/logger.py`
- [ ] T053 [US5] Add `flush(self) -> None` method signature to EventBusProtocol in `langagent/cross_cutting/logger.py`
- [ ] T054 [US5] Add comprehensive docstrings to EventBusProtocol and all 4 methods explaining F03 implementation contract in `langagent/cross_cutting/logger.py`

**Checkpoint**: Run User Story 5 tests - all 5 tests must PASS

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, validation, and documentation

- [ ] T055 [P] Update `langagent/cross_cutting/__init__.py` to export public API: emit, set_level, drain_spans, EventBusProtocol, Span, LogLevel, UnknownLogTagError, SpanDrainError
- [ ] T056 [P] Run mypy --strict on `langagent/cross_cutting/logger.py` and fix any type errors (SC-003)
- [ ] T057 [P] Run all 28 tests (13 logger + 6 drain_spans + 4 redaction + 5 EventBusProtocol) and verify 100% pass rate
- [ ] T058 [P] Create performance benchmark script in `tests/cross_cutting/benchmark_logger.py` - verify <5ms per emit (SC-004)
- [ ] T059 [P] Create concurrency stress test in `tests/cross_cutting/stress_test_logger.py` - verify 10,000 concurrent emits from 100 threads (SC-007)
- [ ] T060 Add inline code comments explaining lock usage, redaction algorithm, and span filtering logic in `langagent/cross_cutting/logger.py`
- [ ] T061 Verify all 46 tags from workflow.md are present in ALLOWED_TAGS (SC-006) - create validation script in `tests/cross_cutting/validate_tags.py`
- [ ] T062 Create fixture file `tests/fixtures/log_tags_whitelist.json` with all 46 tags for test validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User Story 1 (P1): No dependencies on other stories
  - User Story 2 (P1): Depends on User Story 1 (needs emit() function)
  - User Story 3 (P2): Depends on User Story 1 (extends emit() logic)
  - User Story 4 (P2): Depends on User Story 1 (extends emit() logic)
  - User Story 5 (P3): Independent - pure interface definition
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories ✅ Independent
- **User Story 2 (P1)**: Requires US1 emit() function to exist, but redaction logic is independent ⚠️ Sequential after US1
- **User Story 3 (P2)**: Requires US1 emit() function, adds level filtering ⚠️ Sequential after US1
- **User Story 4 (P2)**: Requires US1 emit() function, adds span buffer ⚠️ Sequential after US1
- **User Story 5 (P3)**: Completely independent - pure type definition ✅ Can run in parallel

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD Red phase)
- Implementation makes tests pass (TDD Green phase)
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1 (Setup)**: All 4 tasks can run in parallel (different files)
- **Phase 2 (Foundational)**: Tasks T006-T009 can run in parallel (different definitions in same file, no conflicts)
- **User Story Tests**: All tests within same user story can be written in parallel (e.g., T010-T016 for US1)
- **User Story 1 + User Story 5**: US5 (EventBusProtocol) can be implemented in parallel with US1-4 since it's pure interface
- **Phase 8 (Polish)**: Tasks T055-T059 can run in parallel (different files/concerns)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (TDD Red phase):
Task: "Write test_emit_with_valid_tag in tests/cross_cutting/test_logger.py"
Task: "Write test_emit_with_unknown_tag in tests/cross_cutting/test_logger.py"
Task: "Write test_emit_emits_jsonl_to_stderr_not_stdout in tests/cross_cutting/test_logger.py"
Task: "Write test_emit_thread_safe in tests/cross_cutting/test_logger.py"
Task: "Write test_emit_tag_whitelist_at_least_46 in tests/cross_cutting/test_logger.py"
Task: "Write test_emit_timestamp_is_iso8601 in tests/cross_cutting/test_logger.py"
Task: "Write test_emit_payload_must_be_dict in tests/cross_cutting/test_logger.py"

# Implementation tasks are sequential (T017-T021) since they build on each other
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Structured Logging)
4. Complete Phase 4: User Story 2 (Secret Redaction)
5. **STOP and VALIDATE**: Test US1+US2 independently with 11 tests
6. This gives you a working, secure logger ready for use

### Incremental Delivery (Recommended)

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently (7 tests) → Core logging works ✅
3. Add User Story 2 → Test independently (4 tests) → Secure logging works ✅
4. Add User Story 3 → Test independently (2 tests) → Configurable logging works ✅
5. Add User Story 4 → Test independently (6 tests) → Tracing-ready logging works ✅
6. Add User Story 5 → Test independently (5 tests) → F03 contract ready ✅
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers after Foundational phase completes:

1. **Developer A**: User Story 1 (T010-T021) - Core logging
2. **Developer B**: User Story 5 (T044-T054) - EventBusProtocol (independent)
3. After A completes:
   - **Developer A**: User Story 2 (T022-T027) - Redaction
   - **Developer C**: User Story 3 (T028-T032) - Level filtering (can start after A finishes US1)
4. After A completes US2:
   - **Developer A**: User Story 4 (T033-T043) - Span buffer
5. All converge on Phase 8 Polish

---

## Summary & Notes

**Total Task Count: 62 tasks**

- **Setup**: 4 tasks
- **Foundational**: 5 tasks
- **User Story 1**: 12 tasks (7 tests + 5 implementation)
- **User Story 2**: 6 tasks (4 tests + 2 implementation)
- **User Story 3**: 5 tasks (2 tests + 3 implementation)
- **User Story 4**: 11 tasks (6 tests + 5 implementation)
- **User Story 5**: 11 tasks (5 tests + 6 implementation)
- **Polish**: 8 tasks

**Suggested MVP Scope**: Phase 1 + Phase 2 + Phase 3 + Phase 4 = 27 tasks (Setup + Foundational + US1 + US2) delivers secure, validated structured logging.

**Implementation Notes**:

- **TDD Enforcement**: Constitution Article VIII mandates Red-Green-Refactor cycle. All test tasks explicitly require failures before implementation.
- **Thread Safety**: All concurrent tests use 10 threads minimum to stress-test lock implementation per research.md.
- **File Paths**: Single module file `langagent/cross_cutting/logger.py` contains all implementation (~170 LOC per research.md estimate).
- **Test Coverage**: 28 total tests across 5 user stories = comprehensive coverage for SC-001 and SC-002.
- **[P] tasks**: Marked for truly independent file/definition work only. Most tasks are sequential due to TDD dependencies.
- **Commit Frequency**: Recommend commit after each user story phase completes (post-checkpoint validation).
- **mypy --strict**: SC-003 requires zero type errors - T056 enforces this before considering feature complete.
