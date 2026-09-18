# Tasks: F02 Phase 2 - Metrics Collector

**Input**: Design documents from `/specs/002-metrics-collector-phase2/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Tests are REQUIRED per 宪法第 VIII 条 (TDD 刚性约束). All test tasks follow Red-Green-Refactor cycle.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US4, US5)
- Include exact file paths in descriptions

## Path Conventions

- Source: `langagent/cross_cutting/metrics_collector.py`
- Tests: `tests/cross_cutting/test_metrics_collector.py`
- Fixtures: `tests/fixtures/pricing_table_*.json`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create `langagent/cross_cutting/metrics_collector.py` module file with module docstring
- [ ] T002 Create `tests/cross_cutting/test_metrics_collector.py` test file with pytest imports
- [ ] T003 [P] Create `tests/fixtures/pricing_table_default.json` with default model prices (gpt-4o, gpt-4o-mini, qwen3-8b)
- [ ] T004 [P] Create `tests/fixtures/pricing_table_test.json` with test model prices for unit tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data structures that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 [P] Define `LatencySample` dataclass with 4 fields (operation, latency_ms, timestamp, event_id) in langagent/cross_cutting/metrics_collector.py
- [ ] T006 [P] Define `TokenUsageSample` dataclass with 5 fields (model_name, prompt_tokens, completion_tokens, timestamp, event_id) in langagent/cross_cutting/metrics_collector.py
- [ ] T007 [P] Define `ErrorSample` dataclass with 3 fields (operation, timestamp, event_id) in langagent/cross_cutting/metrics_collector.py
- [ ] T008 [P] Define `MetricsSnapshot` frozen dataclass with 9 fields (Optional[float] for percentiles) in langagent/cross_cutting/metrics_collector.py
- [ ] T009 [P] Test: Write failing test for `MetricsSnapshot` immutability (`test_snapshot_returns_frozen_dataclass`) in tests/cross_cutting/test_metrics_collector.py
- [ ] T010 Initialize module-level variables: `_lock`, `_latency_samples`, `_token_samples`, `_error_samples`, `_event_id_window` in langagent/cross_cutting/metrics_collector.py
- [ ] T011 [P] Test: Write failing test for dataclass field types and defaults in tests/cross_cutting/test_metrics_collector.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 5 - Event Bus Integration (Priority: P1) 🎯 BLOCKING

**Goal**: Subscribe to event bus and automatically record metrics when events are published

**Independent Test**: Mock event bus, publish test events, verify metrics_collector internal state reflects events

**Why P1 and BLOCKING**: Without event bus integration, automatic metrics collection is impossible. This unblocks US1 (automatic collection) and US4 (percentile reporting).

### Tests for User Story 5 (TDD - Write FIRST, ensure FAIL)

- [ ] T012 [P] [US5] Test: Write failing test `test_subscribe_to_event_bus` - verify `model_response` event → `record_token_usage()` auto-called in tests/cross_cutting/test_metrics_collector.py
- [ ] T013 [P] [US5] Test: Write failing test `test_subscribe_to_event_bus_tool_call` - verify `tool_call` event → `record_latency()` auto-called in tests/cross_cutting/test_metrics_collector.py
- [ ] T014 [P] [US5] Test: Write failing test `test_malformed_event_missing_latency` - event without `latency_ms` → log warning, skip, no crash in tests/cross_cutting/test_metrics_collector.py
- [ ] T015 [P] [US5] Test: Write failing test `test_malformed_event_missing_event_id` - event without `event_id` → log warning, skip, no crash in tests/cross_cutting/test_metrics_collector.py

### Implementation for User Story 5

- [ ] T016 [P] [US5] Implement `_load_pricing_table(path: str | None) -> dict` helper function in langagent/cross_cutting/metrics_collector.py
- [ ] T017 [P] [US5] Implement `record_latency(operation: str, ms: float) -> None` with threading lock in langagent/cross_cutting/metrics_collector.py
- [ ] T018 [P] [US5] Implement `record_token_usage(model_name: str, prompt: int, completion: int) -> None` with threading lock in langagent/cross_cutting/metrics_collector.py
- [ ] T019 [P] [US5] Implement `record_error(operation: str) -> None` with threading lock in langagent/cross_cutting/metrics_collector.py
- [ ] T020 [US5] Implement event handler `_on_tool_call_event(event: dict) -> None` that calls `record_latency()` in langagent/cross_cutting/metrics_collector.py
- [ ] T021 [US5] Implement event handler `_on_model_response_event(event: dict) -> None` that calls `record_token_usage()` in langagent/cross_cutting/metrics_collector.py
- [ ] T022 [US5] Implement event handler `_on_eval_task_event(event: dict) -> None` that tracks eval task latency in langagent/cross_cutting/metrics_collector.py
- [ ] T023 [US5] Implement `initialize(event_bus: EventBusProtocol, pricing_table_path: str | None = None) -> None` that subscribes to 4 event types in langagent/cross_cutting/metrics_collector.py
- [ ] T024 [US5] Add malformed event handling: log warning via F02 Phase 1 logger when required fields missing in langagent/cross_cutting/metrics_collector.py
- [ ] T025 [US5] Run tests T012-T015 and verify they now PASS

**Checkpoint**: Event bus integration complete - automatic metrics collection is now functional

---

## Phase 4: User Story 1 - Automatic Metrics Collection (Priority: P1) 🎯 MVP

**Goal**: System automatically collects performance metrics (latency, token usage, error rate) in background without explicit configuration

**Independent Test**: Run agent with tool calls and model interactions, call `snapshot()` to verify metrics collected

**Dependencies**: US5 (event bus integration must be complete)

### Tests for User Story 1 (TDD - Write FIRST, ensure FAIL)

- [ ] T026 [P] [US1] Test: Write failing test `test_record_latency_increments_sample_count` - 100 calls → `snapshot().sample_count == 100` in tests/cross_cutting/test_metrics_collector.py
- [ ] T027 [P] [US1] Test: Write failing test `test_snapshot_token_usage_by_model` - verify per-model token aggregation in tests/cross_cutting/test_metrics_collector.py
- [ ] T028 [P] [US1] Test: Write failing test `test_snapshot_error_rate` - 5 errors in 100 ops → error_rate == 0.05 in tests/cross_cutting/test_metrics_collector.py
- [ ] T029 [P] [US1] Test: Write failing test `test_event_deduplication_within_window` - same event_id twice within 10 min → only first recorded in tests/cross_cutting/test_metrics_collector.py
- [ ] T030 [P] [US1] Test: Write failing test `test_event_deduplication_window_expiry` - event_id older than 10 min can be reused in tests/cross_cutting/test_metrics_collector.py

### Implementation for User Story 1

- [ ] T031 [US1] Implement event deduplication: add `_is_duplicate_event(event_id: str, timestamp: datetime) -> bool` helper in langagent/cross_cutting/metrics_collector.py
- [ ] T032 [US1] Implement event deduplication: add `_purge_old_event_ids(current_time: datetime) -> None` helper (remove entries > 10 min old) in langagent/cross_cutting/metrics_collector.py
- [ ] T033 [US1] Update `record_latency()` to check for duplicate event_id and skip if duplicate in langagent/cross_cutting/metrics_collector.py
- [ ] T034 [US1] Update `record_token_usage()` to check for duplicate event_id and skip if duplicate in langagent/cross_cutting/metrics_collector.py
- [ ] T035 [US1] Update `record_error()` to check for duplicate event_id and skip if duplicate in langagent/cross_cutting/metrics_collector.py
- [ ] T036 [US1] Implement `_calculate_error_rate(window_start: datetime, window_end: datetime) -> float` helper in langagent/cross_cutting/metrics_collector.py
- [ ] T037 [US1] Implement `_aggregate_token_usage(window_start: datetime, window_end: datetime) -> dict[str, int]` helper using defaultdict in langagent/cross_cutting/metrics_collector.py
- [ ] T038 [US1] Implement `snapshot(window_start: datetime, window_end: datetime) -> MetricsSnapshot` basic version (sample_count, error_rate, token_usage, cost_usd) in langagent/cross_cutting/metrics_collector.py
- [ ] T039 [US1] Add window validation in `snapshot()`: raise ValueError if `window_end < window_start` in langagent/cross_cutting/metrics_collector.py
- [ ] T040 [US1] Add timestamp filtering in `snapshot()`: only include samples where `window_start <= timestamp < window_end` in langagent/cross_cutting/metrics_collector.py
- [ ] T041 [US1] Emit `la.cross_cutting.metrics.emit` log tag when `snapshot()` is called via F02 Phase 1 logger in langagent/cross_cutting/metrics_collector.py
- [ ] T041a [US1] Implement `flush() -> None` to clear all accumulated metrics (samples + event_id deduplication window) with threading lock in langagent/cross_cutting/metrics_collector.py (required by F09)
- [ ] T041b [US1] Test: Write test for `flush()` - verify data clearing, thread safety, idempotency in tests/cross_cutting/test_metrics_collector.py
- [ ] T042 [US1] Run tests T026-T030 and verify they now PASS

**Checkpoint**: Automatic metrics collection is fully functional - can collect latency, tokens, errors, and deduplicate events

---

## Phase 5: User Story 4 - Percentile Latency Reporting (Priority: P1)

**Goal**: Provide p50/p95/p99 latency metrics to understand typical and worst-case performance

**Independent Test**: Record 100 latency samples with known distribution, verify p50/p95/p99 match expected values

**Dependencies**: US1 (basic snapshot() must be complete)

### Tests for User Story 4 (TDD - Write FIRST, ensure FAIL)

- [ ] T043 [P] [US4] Test: Write failing test `test_snapshot_p50_latency` - verify p50 ≈ 60ms for uniform 10-110ms distribution in tests/cross_cutting/test_metrics_collector.py
- [ ] T044 [P] [US4] Test: Write failing test `test_snapshot_p95_latency` - verify p95 ≈ 105ms for same distribution in tests/cross_cutting/test_metrics_collector.py
- [ ] T045 [P] [US4] Test: Write failing test `test_snapshot_p99_latency` - verify p99 ≈ 109ms for same distribution in tests/cross_cutting/test_metrics_collector.py
- [ ] T046 [P] [US4] Test: Write failing test `test_empty_snapshot_returns_none_percentiles` - no samples → p50/p95/p99 all None in tests/cross_cutting/test_metrics_collector.py

### Implementation for User Story 4

- [ ] T047 [US4] Implement `_calculate_percentiles(samples: list[float]) -> tuple[Optional[float], Optional[float], Optional[float]]` using `statistics.quantiles()` in langagent/cross_cutting/metrics_collector.py
- [ ] T048 [US4] Handle empty sample case in `_calculate_percentiles()`: return (None, None, None) when samples list is empty in langagent/cross_cutting/metrics_collector.py
- [ ] T049 [US4] Update `snapshot()` to calculate and include p50/p95/p99 latency from filtered samples in langagent/cross_cutting/metrics_collector.py
- [ ] T050 [US4] Run tests T043-T046 and verify they now PASS

**Checkpoint**: Percentile latency reporting is complete - US1 + US4 combined provide full basic observability

---

## Phase 6: User Story 2 - Time-Window Metrics Snapshots (Priority: P2)

**Goal**: Request metrics snapshots for specific time windows to understand performance trends within a single execution

**Independent Test**: Record metrics over 60s, request snapshots for [0:30] and [30:60] windows, verify only respective events included

**Dependencies**: US1 and US4 (snapshot() with window filtering must be complete)

### Tests for User Story 2 (TDD - Write FIRST, ensure FAIL)

- [ ] T051 [P] [US2] Test: Write failing test `test_snapshot_window_filter` - verify samples outside `[window_start, window_end]` excluded in tests/cross_cutting/test_metrics_collector.py
- [ ] T052 [P] [US2] Test: Write failing test for non-overlapping window snapshots - metrics over 60s split into [0:30] and [30:60] in tests/cross_cutting/test_metrics_collector.py

### Implementation for User Story 2

- [ ] T053 [US2] Verify timestamp filtering logic in `snapshot()` correctly handles edge cases (window boundaries, timezone-aware datetimes) in langagent/cross_cutting/metrics_collector.py
- [ ] T054 [US2] Add docstring examples for `snapshot()` showing time-window usage patterns in langagent/cross_cutting/metrics_collector.py
- [ ] T055 [US2] Run tests T051-T052 and verify they now PASS

**Checkpoint**: Time-window snapshots are complete - enables fine-grained performance analysis

---

## Phase 7: User Story 3 - Cost Estimation from Token Usage (Priority: P2)

**Goal**: Automatically calculate `cost_usd` based on token usage and model pricing

**Independent Test**: Provide mock pricing table, record token usage for known models, verify `cost_usd` matches expected calculation

**Dependencies**: US1 (token_usage aggregation must be complete)

### Tests for User Story 3 (TDD - Write FIRST, ensure FAIL)

- [ ] T056 [P] [US3] Test: Write failing test `test_snapshot_cost_usd` - verify cost calculation with mock pricing table in tests/cross_cutting/test_metrics_collector.py
- [ ] T057 [P] [US3] Test: Write failing test `test_pricing_table_from_json_file` - load pricing from JSON file at specified path in tests/cross_cutting/test_metrics_collector.py
- [ ] T058 [P] [US3] Test: Write failing test `test_pricing_table_default_fallback` - when path not specified, use built-in default prices in tests/cross_cutting/test_metrics_collector.py
- [ ] T059 [P] [US3] Test: Write failing test for unknown model - logs warning, contributes 0 to cost in tests/cross_cutting/test_metrics_collector.py

### Implementation for User Story 3

- [ ] T060 [US3] Implement `_calculate_cost_usd(token_usage: dict[str, int], pricing_table: dict) -> float` helper in langagent/cross_cutting/metrics_collector.py
- [ ] T061 [US3] Handle unknown models in `_calculate_cost_usd()`: log warning via F02 Phase 1 logger, contribute 0.0 to cost in langagent/cross_cutting/metrics_collector.py
- [ ] T062 [US3] Update `_load_pricing_table()` to support environment variable `LANGAGENT_PRICING_TABLE_PATH` override in langagent/cross_cutting/metrics_collector.py
- [ ] T063 [US3] Update `_load_pricing_table()` to fall back to built-in default prices if file not found in langagent/cross_cutting/metrics_collector.py
- [ ] T064 [US3] Update `snapshot()` to calculate cost_usd using pricing table loaded during `initialize()` in langagent/cross_cutting/metrics_collector.py
- [ ] T065 [US3] Run tests T056-T059 and verify they now PASS

**Checkpoint**: Cost estimation is complete - full financial impact visibility for agent runs

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements, cleanup, and final validation

- [ ] T066 [P] Test: Write thread safety test `test_emit_thread_safe` - 10 threads concurrently calling `record_*` for 1 minute, no data corruption, verify throughput >= 1000 events/second (SC-007) in tests/cross_cutting/test_metrics_collector.py
- [ ] T067 [P] Test: Write thread safety test for `snapshot()` concurrent calls - verify consistent view with locks in tests/cross_cutting/test_metrics_collector.py
- [ ] T068 [P] Test: Write thread safety test for `flush()` during event processing - verify no data loss in tests/cross_cutting/test_metrics_collector.py
- [ ] T069 [P] Add comprehensive docstrings to all public functions (initialize, record_*, snapshot, flush) in langagent/cross_cutting/metrics_collector.py
- [ ] T070 [P] Add type hints to all functions, ensure `mypy --strict` passes with no `type: ignore` comments in langagent/cross_cutting/metrics_collector.py
- [ ] T071 Verify all 18+ test cases from spec.md Test Coverage Requirements section pass in tests/cross_cutting/test_metrics_collector.py
- [ ] T072 Run `mypy --strict langagent/cross_cutting/metrics_collector.py` and fix any type errors
- [ ] T073 Run `pytest tests/cross_cutting/test_metrics_collector.py -v` and verify all tests pass
- [ ] T074 [P] Performance validation: Verify `record_latency()` completes in < 1ms (fire-and-forget)
- [ ] T075 [P] Performance validation: Verify `snapshot()` with 10K samples completes in < 100ms
- [ ] T076 Code review checklist: Verify no hard-coded paths (宪法第 XIII 条), pricing table path configurable
- [ ] T077 Code review checklist: Verify thread safety - all shared state protected by locks
- [ ] T078 Code review checklist: Verify no blocking I/O in `record_*` methods
- [ ] T079 Code review checklist: Verify MetricsSnapshot is frozen dataclass (immutable)
- [ ] T080 Integration validation: Create mock event bus, publish 100 events, verify all metrics collected correctly
- [ ] T081 [P] Test: Long-running memory leak test - Run metrics collection for 24 hours with 1M samples, verify memory growth < 2× baseline (SC-008) in tests/cross_cutting/test_metrics_collector.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 5 (Phase 3)**: Depends on Foundational - BLOCKS US1 and US4 (event bus integration required for automatic collection)
- **User Story 1 (Phase 4)**: Depends on US5 - Can proceed once event bus integration complete
- **User Story 4 (Phase 5)**: Depends on US1 - Can proceed once basic snapshot() complete
- **User Story 2 (Phase 6)**: Depends on US1 and US4 - Requires snapshot() with window filtering and percentiles
- **User Story 3 (Phase 7)**: Depends on US1 - Can proceed in parallel with US4 once token_usage aggregation complete
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 5 (P1)**: No dependencies on other stories (depends only on Foundational) - BLOCKING for US1/US4
- **User Story 1 (P1)**: Depends on US5 (event bus integration) - MVP core functionality
- **User Story 4 (P1)**: Depends on US1 (basic snapshot()) - Completes MVP observability
- **User Story 2 (P2)**: Depends on US1 + US4 (snapshot() with percentiles) - Enhancement
- **User Story 3 (P2)**: Depends on US1 (token_usage aggregation) - Can run parallel with US2

### Critical Path (MVP)

1. Setup (Phase 1) → 4 tasks
2. Foundational (Phase 2) → 7 tasks
3. US5: Event Bus Integration (Phase 3) → 14 tasks
4. US1: Automatic Collection (Phase 4) → 19 tasks (includes flush() API for F09)
5. US4: Percentile Reporting (Phase 5) → 8 tasks

**MVP Complete**: 52 tasks total (Phases 1-5)

### Parallel Opportunities

- **Setup**: T003-T004 can run in parallel (different fixture files)
- **Foundational**: T005-T007 (dataclass definitions), T009 (test) can all run in parallel
- **US5 Tests**: T012-T015 can all run in parallel (different test functions)
- **US5 Implementation**: T016-T019 can run in parallel (different functions, no dependencies)
- **US1 Tests**: T026-T030 can all run in parallel
- **US4 Tests**: T043-T046 can all run in parallel
- **US2 Tests**: T051-T052 can run in parallel
- **US3 Tests**: T056-T059 can all run in parallel
- **Polish**: T066-T072 can mostly run in parallel (different test files/functions)

Once US5 is complete, US1 and US3 can be worked on in parallel by different developers (US1 focuses on deduplication/error_rate, US3 focuses on cost calculation).

---

## Parallel Example: User Story 5 (Event Bus Integration)

```bash
# Launch all tests for User Story 5 together:
Task T012: "Test: test_subscribe_to_event_bus in tests/cross_cutting/test_metrics_collector.py"
Task T013: "Test: test_subscribe_to_event_bus_tool_call in tests/cross_cutting/test_metrics_collector.py"
Task T014: "Test: test_malformed_event_missing_latency in tests/cross_cutting/test_metrics_collector.py"
Task T015: "Test: test_malformed_event_missing_event_id in tests/cross_cutting/test_metrics_collector.py"

# Launch all core record_* functions together:
Task T016: "_load_pricing_table() in langagent/cross_cutting/metrics_collector.py"
Task T017: "record_latency() in langagent/cross_cutting/metrics_collector.py"
Task T018: "record_token_usage() in langagent/cross_cutting/metrics_collector.py"
Task T019: "record_error() in langagent/cross_cutting/metrics_collector.py"
```

---

## Implementation Strategy

### MVP First (User Stories 5, 1, 4 Only)

1. Complete Phase 1: Setup → 4 tasks
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories) → 7 tasks
3. Complete Phase 3: User Story 5 (Event Bus Integration) → 14 tasks
4. Complete Phase 4: User Story 1 (Automatic Collection + flush() API) → 19 tasks
5. Complete Phase 5: User Story 4 (Percentile Reporting) → 8 tasks
6. **STOP and VALIDATE**: Test MVP independently (52 tasks total)
7. Deploy/demo if ready

**MVP delivers**: Automatic metrics collection via event bus + deduplication + percentile latency + basic error_rate/token_usage/cost_usd + flush() API for F09

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (11 tasks)
2. Add US5 → Event bus integration working (25 tasks cumulative)
3. Add US1 → Automatic collection with deduplication + flush() API (44 tasks cumulative)
4. Add US4 → Percentile reporting (52 tasks cumulative) → **MVP COMPLETE**
5. Add US2 → Time-window analysis (57 tasks cumulative)
6. Add US3 → Cost estimation (67 tasks cumulative)
7. Polish → Production ready (83 tasks cumulative)

### Parallel Team Strategy

With 2 developers after Phase 3 (US5) is complete:

1. Team completes Setup + Foundational + US5 together → Event bus ready
2. Once US5 is done:
   - **Developer A**: US1 (Automatic Collection) + US4 (Percentile Reporting)
   - **Developer B**: US3 (Cost Estimation)
3. Then team together: US2 (Time-Window Snapshots) + Polish

---

## Notes

- [P] tasks = different files or functions, no dependencies
- [Story] label maps task to specific user story for traceability
- All tests follow TDD Red-Green-Refactor: Write failing test → Implement → Verify pass
- Thread safety is critical: All shared state (`_*_samples`, `_event_id_window`) protected by `_lock`
- Event deduplication window (10 min) must be maintained throughout all phases
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Total Task Count: 83 tasks

- **Setup (Phase 1)**: 4 tasks
- **Foundational (Phase 2)**: 7 tasks
- **User Story 5 - Event Bus Integration (Phase 3)**: 14 tasks
- **User Story 1 - Automatic Collection (Phase 4)**: 19 tasks (includes flush() implementation)
- **User Story 4 - Percentile Reporting (Phase 5)**: 8 tasks
- **User Story 2 - Time-Window Snapshots (Phase 6)**: 5 tasks
- **User Story 3 - Cost Estimation (Phase 7)**: 10 tasks
- **Polish & Cross-Cutting (Phase 8)**: 16 tasks

**MVP Scope**: Phases 1-5 (52 tasks) deliver core automatic metrics collection with percentile latency reporting and flush() API
