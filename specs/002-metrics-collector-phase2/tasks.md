# Tasks: F02 Phase 2 - Metrics Collector

**Input**: Design documents from `/specs/002-metrics-collector-phase2/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md

**Tests**: Test tasks included per TDD requirement in F02 Feature Prompt §四.2 (18+ test cases)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Per plan.md project structure:
- Source: `langagent/cross_cutting/metrics_collector.py`
- Tests: `tests/cross_cutting/test_metrics_collector.py`
- Fixtures: `tests/fixtures/pricing_table_default.json`, `tests/fixtures/pricing_table_test.json`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and test fixtures

- [x] T001 Create pricing table fixtures: runtime default at ~/.local/share/langagent/pricing.json with gpt-4o, gpt-4o-mini, qwen3-8b prices (used by production code); test fixture at tests/fixtures/pricing_table_test.json with mock prices (used by unit tests only)
- [x] T002 [P] Create test pricing table fixture in tests/fixtures/pricing_table_test.json with mock prices for testing
- [x] T003 [P] Create test file tests/cross_cutting/test_metrics_collector.py with pytest imports and setup

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data structures that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Define MetricsSnapshot frozen dataclass with 9 fields (window_start, window_end, sample_count, p50_latency_ms, p95_latency_ms, p99_latency_ms, error_rate, token_usage, cost_usd) in langagent/cross_cutting/metrics_collector.py
- [x] T005 [P] Define LatencySample dataclass with 4 fields (operation, latency_ms, timestamp, event_id) in langagent/cross_cutting/metrics_collector.py
- [x] T006 [P] Define TokenUsageSample dataclass with 5 fields (model_name, prompt_tokens, completion_tokens, timestamp, event_id) in langagent/cross_cutting/metrics_collector.py
- [x] T007 [P] Define ErrorSample dataclass with 3 fields (operation, timestamp, event_id) in langagent/cross_cutting/metrics_collector.py
- [x] T008 Initialize module-level state: _lock (threading.Lock), _latency_samples (list), _token_samples (list), _error_samples (list), _event_id_window (set) in langagent/cross_cutting/metrics_collector.py
- [x] T009 Implement _redact_event_id() helper function for event deduplication (check event_id in _event_id_window, add with timestamp) in langagent/cross_cutting/metrics_collector.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 5 - Event Bus Integration (Priority: P1) 🎯 MVP Foundation

**Goal**: Enable automatic metrics collection by subscribing to event bus - this is the architectural foundation that all other stories depend on

**Independent Test**: Mock event bus, publish test events, verify metrics_collector internal state reflects those events

### Tests for User Story 5 (TDD - Write tests FIRST, ensure they FAIL)

- [x] T010 [P] [US5] Write test_subscribe_to_event_bus_tool_call in tests/cross_cutting/test_metrics_collector.py - verify tool_call event triggers record_latency()
- [x] T011 [P] [US5] Write test_subscribe_to_event_bus_model_response in tests/cross_cutting/test_metrics_collector.py - verify model_response event triggers record_token_usage()
- [x] T012 [P] [US5] Write test_subscribe_to_event_bus_eval_task_latency in tests/cross_cutting/test_metrics_collector.py - verify eval_task_started/done events calculate latency delta
- [x] T013 [P] [US5] Write test_event_deduplication_within_window in tests/cross_cutting/test_metrics_collector.py - verify duplicate event_id within 10 minutes is discarded
- [x] T014 [P] [US5] Write test_event_deduplication_window_expiry in tests/cross_cutting/test_metrics_collector.py - verify event_id older than 10 minutes can be reused
- [x] T015 [P] [US5] Write test_malformed_event_missing_latency in tests/cross_cutting/test_metrics_collector.py - verify event without latency_ms logs warning and skips
- [x] T016 [P] [US5] Write test_malformed_event_missing_event_id in tests/cross_cutting/test_metrics_collector.py - verify event without event_id logs warning and skips

### Implementation for User Story 5

- [x] T017 [US5] Implement initialize(event_bus: EventBusProtocol, pricing_table_path: str | None) function in langagent/cross_cutting/metrics_collector.py - subscribe to 4 event types (tool_call, model_response, eval_task_started, eval_task_done)
- [x] T018 [P] [US5] Implement _handle_tool_call_event(payload: dict) handler in langagent/cross_cutting/metrics_collector.py - extract operation, latency_ms, event_id, call record_latency()
- [x] T019 [P] [US5] Implement _handle_model_response_event(payload: dict) handler in langagent/cross_cutting/metrics_collector.py - extract model_name, tokens, event_id, call record_token_usage()
- [x] T020 [US5] Implement _handle_eval_task_events() handlers (started/done) in langagent/cross_cutting/metrics_collector.py - calculate latency delta between start and done timestamps
- [x] T021 [US5] Add event payload validation and malformed event handling (missing fields → log warning via cross_cutting_logger, skip event) in langagent/cross_cutting/metrics_collector.py
- [x] T022 [US5] Add event deduplication check to all event handlers (call _redact_event_id before processing) in langagent/cross_cutting/metrics_collector.py
- [x] T023 [US5] Implement 10-minute rolling window purge logic for _event_id_window (lazy cleanup: check and remove entries older than 10 minutes on every new event_id insertion in _redact_event_id() function) in langagent/cross_cutting/metrics_collector.py

**Checkpoint**: Event bus integration complete - automatic metrics collection is now functional

---

## Phase 4: User Story 1 - Automatic Metrics Collection (Priority: P1) 🎯 MVP Core

**Goal**: Provide record_latency(), record_token_usage(), record_error() APIs for automatic metrics collection during agent execution

**Independent Test**: Call record APIs, verify snapshot() returns correct aggregated metrics

### Tests for User Story 1 (TDD - Write tests FIRST, ensure they FAIL)

- [x] T024 [P] [US1] Write test_record_latency_increments_sample_count in tests/cross_cutting/test_metrics_collector.py - verify 100 calls → snapshot().sample_count == 100
- [x] T025 [P] [US1] Write test_record_token_usage_aggregates_by_model in tests/cross_cutting/test_metrics_collector.py - verify token_usage dict aggregates per model
- [x] T026 [P] [US1] Write test_record_error_calculates_error_rate in tests/cross_cutting/test_metrics_collector.py - verify 5 errors in 100 ops → error_rate == 0.05
- [x] T027 [P] [US1] Write test_record_operations_thread_safe in tests/cross_cutting/test_metrics_collector.py - verify 10 threads × 1000 calls = 10000 samples (no data loss)
- [x] T028 [P] [US1] Write test_empty_snapshot_returns_zero_sample_count in tests/cross_cutting/test_metrics_collector.py - verify no samples → sample_count == 0, error_rate == 0.0

### Implementation for User Story 1

- [x] T029 [P] [US1] Implement record_latency(operation: str, ms: float) function in langagent/cross_cutting/metrics_collector.py - append LatencySample to _latency_samples with thread lock
- [x] T030 [P] [US1] Implement record_token_usage(model_name: str, prompt: int, completion: int) function in langagent/cross_cutting/metrics_collector.py - append TokenUsageSample to _token_samples with thread lock
- [x] T031 [P] [US1] Implement record_error(operation: str) function in langagent/cross_cutting/metrics_collector.py - append ErrorSample to _error_samples with thread lock
- [x] T032 [US1] Implement basic snapshot(window_start: datetime, window_end: datetime) function in langagent/cross_cutting/metrics_collector.py - return MetricsSnapshot with sample_count, error_rate, token_usage aggregation
- [x] T033 [US1] Add window validation (window_end < window_start → raise ValueError) in snapshot() function in langagent/cross_cutting/metrics_collector.py
- [x] T034 [US1] Add thread lock acquisition in snapshot() function in langagent/cross_cutting/metrics_collector.py

**Checkpoint**: Core metrics collection APIs functional - can record latency, tokens, errors and generate basic snapshots

---

## Phase 5: User Story 4 - Percentile Latency Reporting (Priority: P1)

**Goal**: Calculate and report p50/p95/p99 latency metrics for performance analysis

**Independent Test**: Record 100 uniform latency samples, verify percentiles match expected values (p50 ≈ 60ms, p95 ≈ 105ms, p99 ≈ 109ms)

### Tests for User Story 4 (TDD - Write tests FIRST, ensure they FAIL)

- [x] T035 [P] [US4] Write test_snapshot_p50_latency in tests/cross_cutting/test_metrics_collector.py - verify p50 ≈ 60ms for uniform 10-110ms distribution
- [x] T036 [P] [US4] Write test_snapshot_p95_latency in tests/cross_cutting/test_metrics_collector.py - verify p95 ≈ 105ms for same distribution
- [x] T037 [P] [US4] Write test_snapshot_p99_latency in tests/cross_cutting/test_metrics_collector.py - verify p99 ≈ 110ms for same distribution
- [x] T038 [P] [US4] Write test_empty_snapshot_returns_none_percentiles in tests/cross_cutting/test_metrics_collector.py - verify no samples → p50/p95/p99 all return None
- [x] T039 [P] [US4] Write test_percentile_accuracy_within_one_percent in tests/cross_cutting/test_metrics_collector.py - verify percentile calculations match NumPy within 1% error for sample size > 100

### Implementation for User Story 4

- [x] T040 [US4] Implement _calculate_percentiles(latencies: list[float]) helper function in langagent/cross_cutting/metrics_collector.py - use statistics.quantiles() with method='exclusive' for NumPy compatibility
- [x] T041 [US4] Handle empty latencies case in _calculate_percentiles() in langagent/cross_cutting/metrics_collector.py - return (None, None, None) when list is empty
- [x] T042 [US4] Update snapshot() to call _calculate_percentiles() and populate p50_latency_ms, p95_latency_ms, p99_latency_ms fields in langagent/cross_cutting/metrics_collector.py
- [x] T043 [US4] Filter latency samples by timestamp window in snapshot() (only include samples where window_start <= timestamp < window_end) in langagent/cross_cutting/metrics_collector.py

**Checkpoint**: Percentile latency reporting functional - can analyze typical and worst-case performance

---

## Phase 6: User Story 2 - Time-Window Metrics Snapshots (Priority: P2)

**Goal**: Enable fine-grained performance analysis by requesting metrics for specific time windows

**Independent Test**: Record metrics over 60 seconds, request snapshots for [0:30] and [30:60], verify non-overlapping samples

### Tests for User Story 2 (TDD - Write tests FIRST, ensure they FAIL)

- [x] T044 [P] [US2] Write test_snapshot_window_filter in tests/cross_cutting/test_metrics_collector.py - verify samples outside [window_start, window_end] excluded
- [x] T045 [P] [US2] Write test_snapshot_non_overlapping_windows in tests/cross_cutting/test_metrics_collector.py - verify [0:30] and [30:60] windows contain distinct samples
- [x] T046 [P] [US2] Write test_snapshot_concurrent_calls_thread_safe in tests/cross_cutting/test_metrics_collector.py - verify concurrent snapshot() calls return consistent views

### Implementation for User Story 2

- [x] T047 [US2] Implement timestamp filtering for token samples in snapshot() (filter _token_samples by window) in langagent/cross_cutting/metrics_collector.py
- [x] T048 [US2] Implement timestamp filtering for error samples in snapshot() (filter _error_samples by window) in langagent/cross_cutting/metrics_collector.py
- [x] T049 [US2] Add timestamp boundary handling (inclusive window_start, exclusive window_end) in snapshot() filtering logic in langagent/cross_cutting/metrics_collector.py

**Checkpoint**: Time-window filtering complete - can analyze specific phases of agent execution

---

## Phase 7: User Story 3 - Cost Estimation from Token Usage (Priority: P2)

**Goal**: Automatically calculate cost_usd based on token usage and model pricing table

**Independent Test**: Provide mock pricing table, record token usage, verify cost_usd calculation matches expected formula

### Tests for User Story 3 (TDD - Write tests FIRST, ensure they FAIL)

- [x] T050 [P] [US3] Write test_snapshot_cost_usd in tests/cross_cutting/test_metrics_collector.py - verify cost calculation with mock pricing table (prompt_tokens × prompt_price + completion_tokens × completion_price) / 1000
- [x] T051 [P] [US3] Write test_pricing_table_from_json_file in tests/cross_cutting/test_metrics_collector.py - verify loading from JSON file at specified path
- [x] T052 [P] [US3] Write test_pricing_table_default_fallback in tests/cross_cutting/test_metrics_collector.py - verify built-in default prices when path not specified
- [x] T053 [P] [US3] Write test_pricing_table_unknown_model in tests/cross_cutting/test_metrics_collector.py - verify unknown model logs warning and contributes 0 to cost
- [x] T054 [P] [US3] Write test_pricing_table_env_var_override in tests/cross_cutting/test_metrics_collector.py - verify LANGAGENT_PRICING_TABLE_PATH environment variable overrides default

### Implementation for User Story 3

- [x] T055 [US3] Implement _load_pricing_table(path: str | None) function in langagent/cross_cutting/metrics_collector.py - load JSON, check env var LANGAGENT_PRICING_TABLE_PATH, fallback to built-in defaults
- [x] T056 [US3] Add built-in default pricing dict for gpt-4o, gpt-4o-mini, qwen3-8b in langagent/cross_cutting/metrics_collector.py
- [x] T057 [US3] Update initialize() to call _load_pricing_table() and store result in module-level _pricing_table variable in langagent/cross_cutting/metrics_collector.py
- [x] T058 [US3] Implement _calculate_cost(token_usage: dict[str, int]) function in langagent/cross_cutting/metrics_collector.py - multiply tokens by pricing, sum across models, handle unknown models (log warning, contribute 0)
- [x] T059 [US3] Update snapshot() to call _calculate_cost() and populate cost_usd field in langagent/cross_cutting/metrics_collector.py

**Checkpoint**: Cost estimation functional - can understand financial impact of agent runs

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements and missing pieces

- [x] T060 [P] Implement flush() function in langagent/cross_cutting/metrics_collector.py - clear _latency_samples, _token_samples, _error_samples, _event_id_window with thread lock
- [x] T061 [P] Write test_flush_clears_all_data in tests/cross_cutting/test_metrics_collector.py - verify flush() clears samples and deduplication window
- [x] T062 [P] Write test_flush_thread_safe in tests/cross_cutting/test_metrics_collector.py - verify concurrent flush() during event processing doesn't lose data
- [x] T063 [P] Add log emission in snapshot() function (emit "la.cross_cutting.metrics.emit" tag via cross_cutting_logger) in langagent/cross_cutting/metrics_collector.py
- [x] T064 [P] Verify MetricsSnapshot immutability (frozen=True) - write test_snapshot_returns_frozen_dataclass in tests/cross_cutting/test_metrics_collector.py
- [x] T065 [P] Add type hints for mypy --strict compliance (Optional[float] for percentiles) in langagent/cross_cutting/metrics_collector.py
- [x] T066 Run mypy --strict on langagent/cross_cutting/metrics_collector.py and fix any type errors
- [x] T067 Run pytest tests/cross_cutting/test_metrics_collector.py and verify all 18+ tests pass
- [x] T068 Verify performance goals: record_latency < 1ms, snapshot < 100ms for 10K samples (add performance benchmark tests if needed)
- [x] T068a [P] Write test_initialize_subscribes_within_100ms in tests/cross_cutting/test_metrics_collector.py - verify initialize() completes within 100ms (SC-001 performance benchmark)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US5 (Event Bus Integration) should complete first - it's the foundation for automatic collection
  - US1 (Automatic Metrics Collection) depends on US5 being functional
  - US4 (Percentile Latency) extends US1 - should complete after US1
  - US2 (Time-Window Snapshots) extends US1 - can run in parallel with US4
  - US3 (Cost Estimation) extends US1 - can run in parallel with US2 and US4
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 5 (P1)**: Foundation - MUST complete first
- **User Story 1 (P1)**: Depends on US5 - core metrics APIs
- **User Story 4 (P1)**: Depends on US1 - extends with percentiles
- **User Story 2 (P2)**: Depends on US1 - can run in parallel with US4 and US3
- **User Story 3 (P2)**: Depends on US1 - can run in parallel with US2 and US4

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- Helper functions before main functions
- Core implementation before edge cases
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T001, T002, T003)
- All Foundational dataclass definitions marked [P] can run in parallel (T005, T006, T007)
- All tests for a user story marked [P] can run in parallel
- Once US1 completes, US2/US3/US4 can start in parallel (if team capacity allows)
- All Polish tasks marked [P] can run in parallel

---

## Parallel Example: User Story 5 Tests

```bash
# Launch all tests for User Story 5 together:
Task: "Write test_subscribe_to_event_bus_tool_call in tests/cross_cutting/test_metrics_collector.py"
Task: "Write test_subscribe_to_event_bus_model_response in tests/cross_cutting/test_metrics_collector.py"
Task: "Write test_subscribe_to_event_bus_eval_task_latency in tests/cross_cutting/test_metrics_collector.py"
Task: "Write test_event_deduplication_within_window in tests/cross_cutting/test_metrics_collector.py"
Task: "Write test_event_deduplication_window_expiry in tests/cross_cutting/test_metrics_collector.py"
Task: "Write test_malformed_event_missing_latency in tests/cross_cutting/test_metrics_collector.py"
Task: "Write test_malformed_event_missing_event_id in tests/cross_cutting/test_metrics_collector.py"
```

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all tests for User Story 1 together:
Task: "Write test_record_latency_increments_sample_count in tests/cross_cutting/test_metrics_collector.py"
Task: "Write test_record_token_usage_aggregates_by_model in tests/cross_cutting/test_metrics_collector.py"
Task: "Write test_record_error_calculates_error_rate in tests/cross_cutting/test_metrics_collector.py"
Task: "Write test_record_operations_thread_safe in tests/cross_cutting/test_metrics_collector.py"
Task: "Write test_empty_snapshot_returns_zero_sample_count in tests/cross_cutting/test_metrics_collector.py"
```

---

## Implementation Strategy

### MVP First (User Stories 5 + 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 5 (Event Bus Integration - foundation)
4. Complete Phase 4: User Story 1 (Automatic Metrics Collection - core)
5. **STOP and VALIDATE**: Test US1 + US5 independently with mock event bus
6. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 5 → Event bus integration functional
3. Add User Story 1 → Core metrics collection functional (MVP!)
4. Add User Story 4 → Percentile latency reporting added
5. Add User Story 2 → Time-window filtering added
6. Add User Story 3 → Cost estimation added
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Complete US5 together (foundation for all)
3. Complete US1 together (core APIs)
4. Once US1 is done:
   - Developer A: User Story 4 (Percentile Latency)
   - Developer B: User Story 2 (Time-Window Snapshots)
   - Developer C: User Story 3 (Cost Estimation)
5. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files or different functions, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD Red-Green-Refactor)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Thread safety is critical - use _lock for all state mutations
- Event deduplication prevents double-counting retried operations
- Percentile calculations must match NumPy within 1% for credibility
- Cost estimation handles unknown models gracefully (log warning, contribute 0)
