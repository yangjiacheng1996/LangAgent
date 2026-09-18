# Tasks: F03 Protocol Event Bus

**Input**: Design documents from `/specs/003-protocol-event-bus/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: TDD approach required per Constitution Article XIII. All tests MUST be written first and verified to FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Path Conventions

Per plan.md Project Structure:
- Source code: `langagent/protocol/` (event_bus.py, event_types.py)
- Tests: `tests/protocol/` (test_event_bus.py, test_event_integration_with_metrics.py)
- Single project structure at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and module structure

- [ ] T001 Create `langagent/protocol/__init__.py` with module exports
- [ ] T002 Create `tests/protocol/__init__.py` for test module structure
- [ ] T003 [P] Verify pytest and pytest-asyncio are in pyproject.toml dev dependencies
- [ ] T004 [P] Create Event dataclass stub in langagent/protocol/event_bus.py for import by tests

**Checkpoint**: Module structure ready - test files can now import protocol.event_bus

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core entities and types that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Define ALLOWED_EVENT_TYPES frozenset (≥13 types) in langagent/protocol/event_types.py
- [ ] T006 Define UnknownEventTypeError exception class in langagent/protocol/event_bus.py
- [ ] T007 Define EventDrainError exception class in langagent/protocol/event_bus.py
- [ ] T008 [P] Define SubscriptionToken type alias in langagent/protocol/event_bus.py
- [ ] T009 [P] Create Event immutable dataclass with 6 fields in langagent/protocol/event_bus.py
- [ ] T010 Add Event.create() factory method for auto-generation of event_id and emitted_at in langagent/protocol/event_bus.py
- [ ] T011 Create EventBus class skeleton with __init__ in langagent/protocol/event_bus.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Event Publication and Subscription (Priority: P1) 🎯 MVP

**Goal**: Implement core pub/sub functionality where modules can publish events and subscribers receive them in FIFO order

**Independent Test**: Publish a single event and verify subscriber receives it exactly once

### Tests for User Story 1 (TDD - Write and verify FAIL first)

- [ ] T012 [P] [US1] Write test_publish_subscribe_basic in tests/protocol/test_event_bus.py
- [ ] T013 [P] [US1] Write test_publish_no_subscribers in tests/protocol/test_event_bus.py
- [ ] T014 [P] [US1] Write test_subscribe_returns_token in tests/protocol/test_event_bus.py
- [ ] T015 [P] [US1] Write test_unsubscribe_idempotent in tests/protocol/test_event_bus.py
- [ ] T016 [P] [US1] Write test_multiple_subscribers_same_event in tests/protocol/test_event_bus.py
- [ ] T017 [P] [US1] Write test_publish_event_type_whitelist in tests/protocol/test_event_bus.py
- [ ] T018 [US1] Run tests and verify ALL 6 tests FAIL with appropriate errors

### Implementation for User Story 1

- [ ] T019 [P] [US1] Implement EventBus._lock (threading.RLock) initialization in langagent/protocol/event_bus.py
- [ ] T020 [P] [US1] Implement EventBus._subscribers dict initialization in langagent/protocol/event_bus.py
- [ ] T021 [P] [US1] Implement EventBus._token_map dict initialization in langagent/protocol/event_bus.py
- [ ] T022 [P] [US1] Implement EventBus._next_token_id counter initialization in langagent/protocol/event_bus.py
- [ ] T023 [US1] Implement EventBus.subscribe(event_type, handler) method with token generation in langagent/protocol/event_bus.py
- [ ] T024 [US1] Implement EventBus.unsubscribe(token) method with idempotency in langagent/protocol/event_bus.py
- [ ] T025 [US1] Implement EventBus.publish(event) method with FIFO handler execution in langagent/protocol/event_bus.py
- [ ] T026 [US1] Add event_type whitelist validation to publish() using ALLOWED_EVENT_TYPES in langagent/protocol/event_bus.py
- [ ] T027 [US1] Run User Story 1 tests and verify ALL 6 tests PASS

**Checkpoint**: Basic pub/sub works - can publish events and subscribers receive them in order

---

## Phase 4: User Story 2 - Error Isolation (Priority: P1)

**Goal**: Ensure handler exceptions don't break the event pipeline - other handlers continue to execute

**Independent Test**: Register two handlers where one throws exception, verify second handler still executes

### Tests for User Story 2 (TDD - Write and verify FAIL first)

- [ ] T028 [P] [US2] Write test_publish_handler_error_isolated in tests/protocol/test_event_bus.py
- [ ] T029 [P] [US2] Write test_error_count_increments_on_handler_exception in tests/protocol/test_event_bus.py
- [ ] T030 [P] [US2] Write test_handler_exception_logged_via_f02_emit in tests/protocol/test_event_bus.py (mock F02 emit)
- [ ] T031 [US2] Run tests and verify ALL 3 tests FAIL

### Implementation for User Story 2

- [ ] T032 [US2] Add EventBus._error_count internal counter to __init__ in langagent/protocol/event_bus.py
- [ ] T033 [US2] Implement EventBus._log_handler_error(exception, token) method in langagent/protocol/event_bus.py
- [ ] T034 [US2] Add try-except block around handler execution in publish() in langagent/protocol/event_bus.py
- [ ] T035 [US2] Import emit from langagent.cross_cutting.logger in langagent/protocol/event_bus.py
- [ ] T036 [US2] Call emit(tag="la.cross_cutting.event_handler_error") in _log_handler_error in langagent/protocol/event_bus.py
- [ ] T037 [US2] Run User Story 2 tests and verify ALL 3 tests PASS

**Checkpoint**: Error isolation works - one faulty handler doesn't break the pipeline

---

## Phase 5: User Story 3 - Async Handler Support (Priority: P2)

**Goal**: Support async handlers for long-running operations via publish_async()

**Independent Test**: Register async handler, call publish_async(), verify handler properly awaited

### Tests for User Story 3 (TDD - Write and verify FAIL first)

- [ ] T038 [P] [US3] Write test_publish_async_handler in tests/protocol/test_event_bus.py
- [ ] T039 [P] [US3] Write test_publish_async_handler_exception_isolated in tests/protocol/test_event_bus.py
- [ ] T040 [P] [US3] Write test_publish_async_with_sync_handler in tests/protocol/test_event_bus.py
- [ ] T041 [P] [US3] Write test_publish_async_multiple_handlers_concurrent in tests/protocol/test_event_bus.py
- [ ] T042 [US3] Run tests and verify ALL 4 tests FAIL

### Implementation for User Story 3

- [ ] T043 [US3] Implement EventBus.publish_async(event) async method skeleton in langagent/protocol/event_bus.py
- [ ] T044 [US3] Add asyncio import in langagent/protocol/event_bus.py
- [ ] T045 [US3] Implement handler type detection (asyncio.iscoroutinefunction) in publish_async in langagent/protocol/event_bus.py
- [ ] T046 [US3] Implement sync handler wrapping via asyncio.to_thread in publish_async in langagent/protocol/event_bus.py
- [ ] T047 [US3] Implement asyncio.gather with return_exceptions=True in publish_async in langagent/protocol/event_bus.py
- [ ] T048 [US3] Add exception logging for async handlers in publish_async in langagent/protocol/event_bus.py
- [ ] T049 [US3] Run User Story 3 tests and verify ALL 4 tests PASS

**Checkpoint**: Async handlers work - both sync and async handlers can be used with publish_async()

---

## Phase 6: User Story 4 - Graceful Shutdown (Priority: P2)

**Goal**: Implement flush(timeout) to wait for pending handlers before exit_cleanup

**Independent Test**: Publish event with slow handler, call flush(), verify it blocks until handler completes

### Tests for User Story 4 (TDD - Write and verify FAIL first)

- [ ] T050 [P] [US4] Write test_flush_waits_for_pending_sync_handlers in tests/protocol/test_event_bus.py
- [ ] T051 [P] [US4] Write test_flush_timeout_emits_event_handler_error_log in tests/protocol/test_event_bus.py
- [ ] T052 [P] [US4] Write test_flush_no_pending_returns_immediately in tests/protocol/test_event_bus.py
- [ ] T053 [US4] Run tests and verify ALL 3 tests FAIL

### Implementation for User Story 4

- [ ] T054 [US4] Add EventBus._pending_futures list to __init__ in langagent/protocol/event_bus.py
- [ ] T055 [US4] Add concurrent.futures import in langagent/protocol/event_bus.py
- [ ] T056 [US4] Create ThreadPoolExecutor in __init__ for handler execution in langagent/protocol/event_bus.py
- [ ] T057 [US4] Implement EventBus.flush(timeout=5.0) method in langagent/protocol/event_bus.py
- [ ] T058 [US4] Implement concurrent.futures.wait with timeout in flush() in langagent/protocol/event_bus.py
- [ ] T059 [US4] Add timeout logging via emit() when handlers not done in flush() in langagent/protocol/event_bus.py
- [ ] T060 [US4] Modify publish() to track futures in _pending_futures in langagent/protocol/event_bus.py
- [ ] T061 [US4] Run User Story 4 tests and verify ALL 3 tests PASS

**Checkpoint**: Flush works - exit_cleanup can wait for handlers to complete

---

## Phase 7: User Story 5 - Event Drainage for Persistence (Priority: P2)

**Goal**: Implement drain_events() to extract all buffered events for JSONL persistence by F09

**Independent Test**: Publish 5 events, call drain_events(), verify returns 5 events and clears buffer

### Tests for User Story 5 (TDD - Write and verify FAIL first)

- [ ] T062 [P] [US5] Write test_drain_events_returns_accumulated in tests/protocol/test_event_bus.py
- [ ] T063 [P] [US5] Write test_drain_events_clears_buffer in tests/protocol/test_event_bus.py
- [ ] T064 [P] [US5] Write test_drain_events_empty_when_no_pending in tests/protocol/test_event_bus.py
- [ ] T065 [P] [US5] Write test_drain_events_thread_safe in tests/protocol/test_event_bus.py
- [ ] T066 [P] [US5] Write test_drain_events_with_pending_handlers_returns_after_flush in tests/protocol/test_event_bus.py
- [ ] T067 [P] [US5] Write test_drain_events_raises_event_drain_error_on_failure (mock internal exception during buffer access) in tests/protocol/test_event_bus.py
- [ ] T068 [US5] Run tests and verify ALL 6 tests FAIL

### Implementation for User Story 5

- [ ] T069 [US5] Add EventBus._event_buffer list to __init__ in langagent/protocol/event_bus.py
- [ ] T070 [US5] Modify publish() to append event to _event_buffer after handler execution in langagent/protocol/event_bus.py
- [ ] T071 [US5] Modify publish_async() to append event to _event_buffer in langagent/protocol/event_bus.py
- [ ] T072 [US5] Implement EventBus.drain_events() method with lock-protected read+clear in langagent/protocol/event_bus.py
- [ ] T073 [US5] Add try-except for EventDrainError in drain_events() in langagent/protocol/event_bus.py
- [ ] T074 [US5] Run User Story 5 tests and verify ALL 6 tests PASS

**Checkpoint**: Event drainage works - F09 can extract all events for JSONL persistence

---

## Phase 8: Additional Test Coverage & Edge Cases

**Purpose**: Complete test suite with edge cases and integration tests

- [ ] T075 [P] Write test_event_payload_must_be_dict in tests/protocol/test_event_bus.py
- [ ] T076 [P] Write test_event_payload_must_be_json_serializable in tests/protocol/test_event_bus.py
- [ ] T077 [P] Write test_event_id_is_unique in tests/protocol/test_event_bus.py
- [ ] T078 [P] Write test_event_emitted_at_is_utc_now in tests/protocol/test_event_bus.py
- [ ] T079 [P] Write test_thread_safe_publish in tests/protocol/test_event_bus.py
- [ ] T080 [P] Write test_subscribe_during_publish in tests/protocol/test_event_bus.py
- [ ] T081 [P] Write test_allowed_event_types_at_least_13 in tests/protocol/test_event_bus.py
- [ ] T082 [P] Write test_all_registered_event_types_have_documentation in tests/protocol/test_event_bus.py
- [ ] T083 [P] Write test_event_handler_error_in_whitelist in tests/protocol/test_event_bus.py
- [ ] T084 Write test_metrics_collector_receives_tool_call_event in tests/protocol/test_event_integration_with_metrics.py
- [ ] T085 [P] Write test_metrics_collector_receives_model_response_event in tests/protocol/test_event_integration_with_metrics.py
- [ ] T086 [P] Write test_metrics_collector_receives_guardrail_block_event in tests/protocol/test_event_integration_with_metrics.py
- [ ] T087 Run additional tests and verify all pass

**Checkpoint**: Full test coverage achieved (≥24 core tests + ≥3 integration tests)

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements, documentation, and validation

- [ ] T088 [P] Add type hints and mypy --strict compliance to langagent/protocol/event_bus.py
- [ ] T089 [P] Add type hints and mypy --strict compliance to langagent/protocol/event_types.py
- [ ] T090 [P] Add docstrings to all public methods in EventBus class in langagent/protocol/event_bus.py
- [ ] T091 [P] Add module-level docstring to langagent/protocol/event_bus.py
- [ ] T092 [P] Update langagent/protocol/__init__.py to export EventBus, Event, SubscriptionToken, exceptions
- [ ] T093 Run full test suite with pytest tests/protocol/ -v and verify all tests pass
- [ ] T094 Run mypy --strict langagent/protocol/event_bus.py and verify no errors
- [ ] T095 Run quickstart.md validation scenarios 1-7 and verify all pass
- [ ] T095a [P] Setup performance measurement utilities (timing helpers, event counters) in tests/protocol/test_event_bus.py for benchmarking
- [ ] T096 [P] Add performance benchmark test for SC-001 (<10ms latency) in tests/protocol/test_event_bus.py
- [ ] T097 [P] Add performance benchmark test for SC-002 (1000 events/sec) in tests/protocol/test_event_bus.py
- [ ] T098 Run performance benchmarks and verify success criteria met
- [ ] T099 Final code review: check for print statements, hardcoded paths, LangSmith imports
- [ ] T100 Commit feature with message "feat(F03): implement protocol event bus with pub/sub, error isolation, async support, flush, and drain"

**Final Checkpoint**: Feature complete, all tests pass, ready for integration with F05/F08/F09

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 (Phase 3): Core pub/sub - BLOCKS all other user stories
  - US2 (Phase 4): Depends on US1 (extends publish with error handling)
  - US3 (Phase 5): Depends on US1 (adds publish_async variant)
  - US4 (Phase 6): Depends on US1, US3 (flush needs handler tracking from both)
  - US5 (Phase 7): Depends on US1, US4 (drain needs buffer from US1, flush from US4)
- **Additional Tests (Phase 8)**: Can start after US1-US5 complete
- **Polish (Phase 9)**: Depends on all previous phases

### User Story Dependencies

```
Foundation (Phase 2)
    ↓
   US1 (Phase 3) ← Core pub/sub (BLOCKING)
    ↓
   ┌────┬────┬────┐
   ↓    ↓    ↓    ↓
  US2  US3  US4  US5
(Error)(Async)(Flush)(Drain)
```

- **US1**: Must complete first (foundation for all other stories)
- **US2**: Can start after US1 (adds error handling to publish)
- **US3**: Can start after US1 (adds publish_async)
- **US4**: Can start after US1 + US3 (flush needs both sync and async tracking)
- **US5**: Can start after US1 + US4 (drain needs buffer from US1, flush from US4)

### Within Each User Story

1. **Tests FIRST** (TDD): Write tests → Run → Verify FAIL
2. **Implementation**: Implement feature
3. **Validation**: Run tests → Verify PASS
4. **Checkpoint**: Verify story independently testable

### Parallel Opportunities

**Phase 1 (Setup)**:
- T001, T002, T003, T004 can all run in parallel

**Phase 2 (Foundational)**:
- T005 (event_types.py) independent
- T006, T007 (exceptions) can run in parallel
- T008, T009, T010 can run in parallel after T006/T007

**Within User Stories**:
- All test writing tasks marked [P] can run in parallel
- Model/entity creation tasks marked [P] can run in parallel
- Tests must run sequentially to see failures before implementation

**Phase 8 (Additional Tests)**:
- All test writing tasks (T075-T086) can run in parallel

**Phase 9 (Polish)**:
- T088, T089, T090, T091, T092 can run in parallel
- T096, T097 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all test writing for User Story 1 together:
Task: "Write test_publish_subscribe_basic in tests/protocol/test_event_bus.py"
Task: "Write test_publish_no_subscribers in tests/protocol/test_event_bus.py"
Task: "Write test_subscribe_returns_token in tests/protocol/test_event_bus.py"
Task: "Write test_unsubscribe_idempotent in tests/protocol/test_event_bus.py"
Task: "Write test_multiple_subscribers_same_event in tests/protocol/test_event_bus.py"
Task: "Write test_publish_event_type_whitelist in tests/protocol/test_event_bus.py"

# Then run T018 sequentially to verify all fail

# Launch all state initialization tasks together:
Task: "Implement EventBus._lock (threading.RLock) initialization"
Task: "Implement EventBus._subscribers dict initialization"
Task: "Implement EventBus._token_map dict initialization"
Task: "Implement EventBus._next_token_id counter initialization"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Core pub/sub)
4. **STOP and VALIDATE**: Run US1 tests independently
5. Deploy/demo basic event bus if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP - basic pub/sub works!)
3. Add User Story 2 → Test independently → Deploy/Demo (error isolation added)
4. Add User Story 3 → Test independently → Deploy/Demo (async support added)
5. Add User Story 4 → Test independently → Deploy/Demo (graceful shutdown added)
6. Add User Story 5 → Test independently → Deploy/Demo (persistence drainage added)
7. Each story adds value without breaking previous stories

### Sequential Strategy (Single Developer)

1. Team completes Setup + Foundational together
2. Then complete user stories in priority order:
   - US1 (P1) → US2 (P1) → US3 (P2) → US4 (P2) → US5 (P2)
3. Each story builds on previous (dependencies captured above)
4. Validate independently after each story

---

## Notes

- [P] tasks = different files or independent operations, no dependencies
- [Story] label maps task to specific user story for traceability
- TDD mandatory per Constitution Article XIII - tests MUST fail before implementation
- Each user story should be independently completable and testable
- Verify tests fail before implementing (Red → Green → Refactor)
- Commit after each user story checkpoint
- Stop at any checkpoint to validate story independently
- US1 is blocking for US2-US5 (all extend US1's publish mechanism)
- Performance benchmarks (SC-001, SC-002) validated in Phase 9
- Total tasks: 100 (Setup: 4, Foundation: 7, US1: 16, US2: 10, US3: 12, US4: 12, US5: 13, Tests: 13, Polish: 13)

---

## Validation Checklist

Before marking feature complete:

- [ ] All 100 tasks completed
- [ ] All ≥27 tests pass (24 core + 3 integration)
- [ ] mypy --strict passes with no errors
- [ ] All 7 quickstart.md scenarios pass
- [ ] Performance benchmarks meet success criteria (SC-001: <10ms, SC-002: 1000 events/sec)
- [ ] No print statements in code
- [ ] No hardcoded paths
- [ ] No LangSmith imports
- [ ] F02 logger integration working (emit() called for errors)
- [ ] All public methods have docstrings
- [ ] Type hints on all functions
- [ ] ALLOWED_EVENT_TYPES has ≥13 entries
- [ ] Event buffer accumulated correctly
- [ ] Thread safety verified via test_thread_safe_publish
