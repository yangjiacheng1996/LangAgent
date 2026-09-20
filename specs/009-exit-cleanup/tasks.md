# Tasks: Exit Cleanup & Doctor Self-Check

**Input**: Design documents from `/specs/009-exit-cleanup/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Tests**: Tests are included per specification requirement (spec §四 lists 38+ test cases). TDD workflow enforced per Constitution Article VIII.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in task descriptions

---

## Phase 1: Setup & Infrastructure

**Goal**: Initialize project structure and shared utilities needed by all user stories.

### Tasks

- [X] T001 Create langagent/runtime/exit_handler.py with RuntimeExitHandler class skeleton
- [X] T001a Implement generate_run_id() utility in langagent/runtime/run_id.py (UUID-based or timestamp-based unique ID generation for JSONL file naming per FR-006/FR-007)
- [X] T002 Create langagent/runtime/exit_code.py with EXIT_CODE_PRIORITY dict (13 codes)
- [X] T003 Create langagent/runtime/doctor_check.py with DoctorCheckResult Pydantic model
- [X] T004 Create tests/runtime/test_exit_handler.py with test harness setup
- [X] T005 Create tests/runtime/test_exit_code.py with test harness setup
- [X] T006 Create tests/runtime/test_doctor_checks.py with test harness setup
- [X] T007 Create tests/fixtures/run_id_generator.py test helper
- [X] T008 Ensure ~/.local/share/langagent/reports/ directory creation in setup
- [X] T009 Ensure ~/.local/share/langagent/logs/ directory creation in setup

**Checkpoint**: Project structure ready, test harnesses in place

---

## Phase 2: Foundational Components (Blocking Prerequisites)

**Goal**: Implement core utilities that all user stories depend on.

### Tasks

- [X] T010 [P] Implement worst_of(codes: list[int]) -> int in langagent/runtime/exit_code.py
- [X] T011 [P] Write test_worst_of_function in tests/runtime/test_exit_code.py (empty list, priority ordering, unknown codes)
- [X] T012 [P] Write test_exit_code_priority_worst_wins in tests/runtime/test_exit_code.py (exit code 4 > 1)
- [X] T013 [P] Write test_exit_code_priority_with_user_interrupt in tests/runtime/test_exit_code.py (exit code 130 > all)
- [X] T014 [P] Write test_exit_code_priority_130_overrides_all in tests/runtime/test_exit_code.py (130 + 70 + 4 → 130)
- [X] T015 Implement RuntimeConfigSnapshot Pydantic model in langagent/runtime/config_snapshot.py with from_runtime_config() factory
- [X] T016 Write test_runtime_config_snapshot_excludes_model in tests/runtime/test_runtime_config_snapshot.py
- [X] T017 Write test_runtime_config_snapshot_excludes_secrets in tests/runtime/test_runtime_config_snapshot.py
- [X] T018 Implement DoctorCheckResult.model_validate_json() test in tests/runtime/test_doctor_checks.py

**Checkpoint**: worst_of() arbitration working, RuntimeConfigSnapshot serialization verified

**Independent Test**: `pytest tests/runtime/test_exit_code.py tests/runtime/test_runtime_config_snapshot.py -v`

---

## Phase 3: User Story 1 - Graceful Cleanup After Normal Agent Run (P1)

**Story Goal**: Implement 11-step cleanup sequence with continue-on-failure strategy. Core cleanup path for every langagent run execution.

**Why Independent**: Tests cleanup flow end-to-end with mocked dependencies (F01-F04, F06). Does not require real model/checkpointer instances.

### Tasks

#### Tests First (TDD Red Phase)

- [X] T019 [P] [US1] Write test_cleanup_emits_la_runtime_exit_cleanup_ok in tests/runtime/test_exit_handler.py
- [X] T020 [P] [US1] Write test_cleanup_returns_exit_code_0_on_success in tests/runtime/test_exit_handler.py
- [X] T021 [P] [US1] Write test_cleanup_closes_checkpointer in tests/runtime/test_exit_handler.py (MemorySaver/SqliteSaver/PostgresSaver)
- [X] T022 [P] [US1] Write test_cleanup_writes_metrics_snapshot in tests/runtime/test_exit_handler.py
- [X] T023 [P] [US1] Write test_cleanup_writes_span_jsonl in tests/runtime/test_exit_handler.py (3 spans → 3 JSONL lines)
- [X] T024 [P] [US1] Write test_cleanup_writes_event_jsonl in tests/runtime/test_exit_handler.py (5 events → 5 JSONL lines)
- [X] T025 [P] [US1] Write test_cleanup_continues_after_step_failure in tests/runtime/test_exit_handler.py (audit flush fails → other steps continue)
- [X] T026 [P] [US1] Write test_cleanup_event_bus_flush_timeout in tests/runtime/test_exit_handler.py (timeout=5s non-failure)

#### Implementation (TDD Green Phase)

- [ ] T027 [US1] Implement cleanup() signature with 7 parameters (2 positional + 5 keyword-only) in langagent/runtime/exit_handler.py
- [ ] T028 [US1] Implement step 1: event_bus.flush(timeout=5) in cleanup(); timeout does not record exit code (non-failure per FR-024)
- [ ] T029 [US1] Implement step 2: metrics_collector.flush() in cleanup()
- [ ] T030 [US1] Implement step 3: audit_recorder.flush() in cleanup()
- [ ] T031 [US1] Implement step 4: checkpoint_adapter.close(checkpoint) in cleanup()
- [ ] T032 [US1] Implement step 5: metrics_snapshot = metrics_collector.snapshot() in cleanup()
- [ ] T033 [US1] Implement step 6: spans = logger.drain_spans() in cleanup()
- [ ] T034 [US1] Implement step 7: events = event_bus.drain_events() in cleanup()
- [ ] T035 [US1] Implement step 8: write_reports() with atomic file write in langagent/runtime/exit_handler.py
- [ ] T036 [US1] Implement step 9: emit la.runtime.exit_cleanup.ok / fail logs in cleanup()
- [ ] T037 [US1] Implement step 11: return worst_of(failed_exit_codes + [0]) in cleanup()
- [ ] T038 [US1] Implement close_checkpointer() with idempotent connection check in langagent/runtime/exit_handler.py
- [ ] T039 [US1] Implement write_reports() JSONL atomic append with fcntl.flock in langagent/runtime/exit_handler.py
- [ ] T040 [US1] Implement continue-on-failure with failed_steps and failed_exit_codes tracking in cleanup()

#### Failure Path Tests

- [ ] T041 [P] [US1] Write test_cleanup_report_write_failed in tests/runtime/test_exit_handler.py (disk full → exit code 4)
- [ ] T042 [P] [US1] Write test_cleanup_checkpointer_close_failed in tests/runtime/test_exit_handler.py (PostgresSaver exception → exit code 1)
- [ ] T043 [P] [US1] Write test_cleanup_audit_flush_failed in tests/runtime/test_exit_handler.py (AuditFlushError → continue → exit code 4)
- [ ] T044 [P] [US1] Write test_cleanup_emits_la_runtime_exit_cleanup_fail in tests/runtime/test_exit_handler.py

#### Edge Cases

- [ ] T045 [P] [US1] Write test_cleanup_routes_by_report_type in tests/runtime/test_exit_handler.py (eval_report > doctor_report priority)
- [ ] T046 [P] [US1] Write test_cleanup_default_run_no_report in tests/runtime/test_exit_handler.py (run without report writes metrics_snapshot only)
- [ ] T047 [P] [US1] Implement zero-valued MetricsSnapshot fallback when snapshot() fails in cleanup() (FR-005 edge case)
- [ ] T048 [P] [US1] Implement "do not create JSONL file if drain returns empty list" in write_reports() (FR-006/007 edge case)

**Checkpoint**: Cleanup flow works end-to-end, all 11 steps execute with continue-on-failure, edge cases handled

**Independent Test**: `pytest tests/runtime/test_exit_handler.py::TestUS1 -v`

---

## Phase 4: User Story 2 - Doctor Self-Check Reporting (P1)

**Story Goal**: Implement 4 doctor check functions (model, checkpointer, skills, instructions) and report generation.

**Why Independent**: Tests doctor checks with mocked probe functions. Does not require US1 cleanup flow (only depends on write_reports from US1).

### Tasks

#### Tests First (TDD Red Phase)

- [ ] T119 [P] [US2] Write test_doctor_check_model_endpoint_reachable in tests/runtime/test_doctor_checks.py
- [ ] T120 [P] [US2] Write test_doctor_check_model_endpoint_unreachable in tests/runtime/test_doctor_checks.py
- [ ] T121 [P] [US2] Write test_doctor_check_model_without_probe_fn_returns_skipped in tests/runtime/test_doctor_checks.py
- [ ] T122 [P] [US2] Write test_doctor_check_checkpointer_sqlite_ok in tests/runtime/test_doctor_checks.py
- [ ] T123 [P] [US2] Write test_doctor_check_checkpointer_failed in tests/runtime/test_doctor_checks.py
- [ ] T124 [P] [US2] Write test_doctor_check_skills_all_valid in tests/runtime/test_doctor_checks.py
- [ ] T125 [P] [US2] Write test_doctor_check_skills_malformed in tests/runtime/test_doctor_checks.py (status="warn" for any number of malformed skills; status="error" only when all fail)
- [ ] T126 [P] [US2] Write test_doctor_check_instructions_too_short in tests/runtime/test_doctor_checks.py (len<=10 → status="warn")
- [ ] T127 [P] [US2] Write test_doctor_check_instructions_missing_keywords in tests/runtime/test_doctor_checks.py (len>10 but no "you"/"你"/"应该" → status="warn")
- [ ] T128 [P] [US2] Write test_doctor_check_instructions_valid in tests/runtime/test_doctor_checks.py ((len>10 AND contains keyword) → status="ok")
- [ ] T129 [P] [US2] Write test_run_doctor_checks_aggregates_overall in tests/runtime/test_doctor_checks.py (4 ok → overall="ok"; 1 error → overall="error")
- [ ] T130 [P] [US2] Write test_run_doctor_checks_calls_probe_functions_exactly_once in tests/runtime/test_doctor_checks.py

#### Implementation (TDD Green Phase)

- [ ] T131 [US2] Implement check_model(config, loaded, *, model_probe_fn) -> DoctorCheckResult in langagent/runtime/doctor_check.py
- [ ] T132 [US2] Implement check_checkpointer(config, *, checkpoint_probe_fn) -> DoctorCheckResult in langagent/runtime/doctor_check.py
- [ ] T133 [US2] Implement check_skills(loaded) -> DoctorCheckResult in langagent/runtime/doctor_check.py with skill frontmatter validation (warn on any malformed, error only when all fail or dir missing)
- [ ] T134 [US2] Implement check_instructions(loaded) -> DoctorCheckResult in langagent/runtime/doctor_check.py with heuristic: (len>10 AND (contains "you" OR "你" OR "应该"))
- [ ] T135 [US2] Implement run_doctor_checks(config, loaded, *, model_probe_fn, checkpoint_probe_fn) -> list[DoctorCheckResult] in langagent/runtime/doctor_check.py
- [ ] T136 [US2] Implement overall status aggregation (any error → "error"; else any warn → "warn"; else "ok") in run_doctor_checks()
- [ ] T137 [US2] Implement DoctorReport Pydantic model in langagent/schemas/doctor_report.py with RuntimeConfigSnapshot embedding
- [ ] T138 [US2] Integrate run_doctor_checks() with cleanup() for doctor_report parameter routing in langagent/runtime/exit_handler.py

#### Report Tests

- [ ] T139 [P] [US2] Write test_cleanup_writes_doctor_report in tests/runtime/test_exit_handler.py (doctor_report → reports/doctor-<timestamp>.json)
- [ ] T140 [P] [US2] Write test_doctor_report_json_serializable in tests/runtime/test_doctor_checks.py
- [ ] T141 [P] [US2] Write test_doctor_report_includes_runtime_snapshot in tests/runtime/test_doctor_checks.py (RuntimeConfigSnapshot not RuntimeConfig)
- [ ] T142 [P] [US2] Write test_exit_handler_does_not_import_primitives in tests/runtime/test_doctor_checks.py (static AST check)

**Checkpoint**: Doctor checks work with probe injection, DoctorReport written to disk

**Independent Test**: `pytest tests/runtime/test_doctor_checks.py -v`

---

## Phase 5: User Story 3 - Eval Report Aggregation and Persistence (P2)

**Story Goal**: Support eval_report parameter routing and EvalReport file writing.

**Why Independent**: Tests eval_report routing without running actual eval tasks (F11). Uses mocked EvalReport instances.

### Tasks

#### Tests First (TDD Red Phase)

- [ ] T143 [P] [US3] Write test_cleanup_writes_eval_report in tests/runtime/test_exit_handler.py (eval_report → reports/<agent-dir>-<timestamp>.json)
- [ ] T144 [P] [US3] Write test_eval_report_json_serializable in tests/runtime/test_eval_report.py
- [ ] T145 [P] [US3] Write test_eval_report_pass_rate in tests/runtime/test_eval_report.py (10 tasks, 7 pass → pass_rate=0.7)
- [ ] T146 [P] [US3] Write test_eval_report_p50_latency in tests/runtime/test_eval_report.py (latency distribution → p50)
- [ ] T147 [P] [US3] Write test_eval_report_token_usage_aggregation in tests/runtime/test_eval_report.py (token by model)

#### Implementation (TDD Green Phase)

- [ ] T148 [US3] Implement EvalReport Pydantic model in langagent/schemas/eval_report.py with 9 fields
- [ ] T149 [US3] Implement eval_report routing in write_reports() (eval_report takes precedence over doctor_report) in langagent/runtime/exit_handler.py
- [ ] T150 [US3] Implement EvalReport file path generation (<agent-dir>-<timestamp>.json) in write_reports()
- [ ] T151 [US3] Implement EvalReport atomic file write with overwrite in write_reports()

**Checkpoint**: EvalReport parameter routing works, report written to correct path

**Independent Test**: `pytest tests/runtime/test_exit_handler.py::TestUS3 tests/runtime/test_eval_report.py -v`

---

## Phase 6: User Story 4 - Continue-on-Failure Cleanup (P2)

**Story Goal**: Verify continue-on-failure strategy handles multiple simultaneous failures and returns correct exit code.

**Why Independent**: Tests worst_of() priority arbitration with multiple failure scenarios. Builds on US1 cleanup flow.

### Tasks

#### Tests First (TDD Red Phase)

- [ ] T152 [P] [US4] Write test_exit_code_priority_hitl_cancel in tests/runtime/test_exit_code.py (HITL cancel + report write fail → 130)
- [ ] T153 [P] [US4] Write test_cleanup_continues_after_multiple_failures in tests/runtime/test_exit_handler.py (audit fail + checkpoint fail + report fail → continue → exit code 4)

#### Implementation (TDD Green Phase)

- [ ] T154 [US4] Enhance cleanup() to track multiple failed_exit_codes in langagent/runtime/exit_handler.py
- [ ] T155 [US4] Implement per-step exception mapping to exit codes (AuditFlushError → 4, CheckpointerCloseError → 1, etc.) in cleanup()
- [ ] T156 [US4] Verify all 11 steps execute even with 3+ simultaneous failures in cleanup()

**Checkpoint**: Continue-on-failure works with 90%+ success rate for remaining steps

**Independent Test**: `pytest tests/runtime/test_exit_handler.py::TestUS4 -v`

---

## Phase 7: User Story 5 - Init-Only Cleanup Mode (P3)

**Story Goal**: Implement init_only=True fast path that skips steps 1-8 and completes in <100ms.

**Why Independent**: Tests minimal cleanup path independently. Does not require full cleanup implementation.

### Tasks

#### Tests First (TDD Red Phase)

- [ ] T157 [P] [US5] Write test_cleanup_init_only_mode_emits_init_end_log in tests/runtime/test_exit_handler.py (init_only=True → la.lifecycle.init.end)
- [ ] T158 [P] [US5] Write test_cleanup_init_only_skips_steps_1_to_8 in tests/runtime/test_exit_handler.py (verify no flush/close/snapshot calls)
- [ ] T159 [P] [US5] Write test_cleanup_init_only_performance in tests/runtime/test_exit_handler.py (duration < 100ms)

#### Implementation (TDD Green Phase)

- [ ] T160 [US5] Implement init_only parameter in cleanup() signature (keyword-only, default False) in langagent/runtime/exit_handler.py
- [ ] T161 [US5] Implement step 1-8 skip logic when init_only=True in cleanup()
- [ ] T162 [US5] Implement step 10: emit la.lifecycle.init.end log (only when init_only=True) in cleanup()
- [ ] T163 [US5] Optimize init_only path for <100ms target (lazy module imports if needed) in cleanup()

**Checkpoint**: Init-only cleanup completes in <100ms with correct logs

**Independent Test**: `pytest tests/runtime/test_exit_handler.py::TestUS5 -v`

---

## Phase 8: Polish & Cross-Cutting Concerns

**Goal**: Stage capability guards, edge case handling, final validation.

### Tasks

- [ ] T164 [P] Apply @cross_cutting_stage_guard_decorator('exit_cleanup') to cleanup() in langagent/runtime/exit_handler.py
- [ ] T165 [P] Write test_cleanup_does_not_invoke_model in tests/runtime/test_exit_handler.py (stage capability violation)
- [ ] T166 [P] Write test_cleanup_does_not_reload_dir in tests/runtime/test_exit_handler.py (stage capability violation)
- [ ] T167 [P] Write test_cleanup_does_not_re_resolve_config in tests/runtime/test_exit_handler.py (stage capability violation)
- [ ] T168 [P] Write test_cleanup_allows_reading_state_and_config in tests/runtime/test_exit_handler.py (positive test: verify cleanup can read state/config without triggering StageCapabilityViolationError)
- [ ] T169 [P] Write test_cleanup_emits_start_log in tests/runtime/test_exit_handler.py (verify la.runtime.exit_cleanup.start log at stage entry per FR-018)
- [ ] T170 [P] Write test_span_jsonl_format in tests/runtime/test_exit_handler.py (7 fields: trace_id, span_id, parent_span_id, name, start, end, attributes)
- [ ] T171 [P] Write test_audit_jsonl_append_only in tests/runtime/test_exit_handler.py (3 writes → 3 lines, no truncate)
- [ ] T172 [P] Write test_drain_spans_failure_preserves_buffer in tests/runtime/test_exit_handler.py (verify buffer intact after drain failure per FR-025)
- [ ] T173 [P] Write test_drain_events_failure_preserves_buffer in tests/runtime/test_exit_handler.py (verify buffer intact after drain failure per FR-025)
- [ ] T174 [P] Write test_exit_handler_does_not_read_langsmith_env_vars in tests/runtime/test_exit_handler.py (static AST check: no LANGSMITH_* access per FR-023)
- [ ] T175 Run mypy --strict on langagent/runtime/exit_handler.py, exit_code.py, doctor_check.py
- [ ] T176 Run full test suite: pytest tests/runtime/ -v --cov=langagent.runtime --cov-report=html
- [ ] T177 Verify test coverage ≥ 90% for langagent/runtime/exit_handler.py

**Checkpoint**: All tests pass, stage guards active, mypy clean, coverage ≥ 90%

**Independent Test**: `pytest tests/runtime/ -v`

---

## Dependencies Between User Stories

```
Setup (Phase 1)
    ↓
Foundational (Phase 2: worst_of, RuntimeConfigSnapshot)
    ↓
    ├─→ US1 (Graceful Cleanup) ────────────────┐
    │       ↓                                   │
    ├─→ US2 (Doctor Checks) ← depends on write_reports from US1
    │       ↓                                   │
    ├─→ US3 (Eval Report) ← depends on write_reports from US1
    │       ↓                                   │
    ├─→ US4 (Continue-on-Failure) ← depends on cleanup() from US1
    │       ↓                                   │
    └─→ US5 (Init-Only) ← depends on cleanup() from US1
            ↓
Polish (Phase 8: stage guards, edge cases)
```

**Critical Path**: Setup → Foundational → US1 → US2 (parallel with US3, US4, US5) → Polish

**Parallelization Opportunities**:
- Phase 1 tasks T001-T009 can run in parallel (different files)
- Phase 2 tasks T010-T018 can run in parallel (worst_of, RuntimeConfigSnapshot, tests)
- Within each US phase, [P] test tasks can run in parallel
- US2, US3, US4, US5 can run in parallel after US1 completes (different features, minimal shared code)

---

## Implementation Strategy

### MVP (Minimum Viable Product)

**Scope**: Setup + Foundational + User Story 1 only

**Delivers**:
- Graceful cleanup after langagent run
- 11-step cleanup sequence working
- Continue-on-failure strategy validated
- MetricsSnapshot / Span / Event writing

**Test**: `pytest tests/runtime/test_exit_handler.py::TestUS1 -v`

**Timeline**: ~40 tasks (T001-T046)

### Incremental Delivery

1. **MVP** (Setup + Foundational + US1) → Foundation ready
2. **Add US2** (Doctor checks) → Test independently → Deploy
3. **Add US3** (Eval reporting) → Test independently → Deploy
4. **Add US4** (Continue-on-failure) → Test independently → Deploy
5. **Add US5** (Init-only) → Test independently → Deploy
6. **Polish** → Final validation

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T018)
2. Once US1 complete:
   - Developer A: US2 (Doctor checks)
   - Developer B: US3 (Eval reporting)
   - Developer C: US4 (Continue-on-failure)
   - Developer D: US5 (Init-only)
3. Stories integrate independently via write_reports() interface

### Testing Strategy

- **Red → Green → Refactor**: Write failing test before implementation (TDD per Article VIII)
- **Test isolation**: Each US test suite runs independently
- **Mock dependencies**: F01-F04, F06, F08 mocked in tests
- **Performance validation**: Init-only <100ms measured with time.perf_counter()
- **Coverage target**: ≥90% for all runtime/ modules

---

## Parallel Execution Examples

### Phase 1 (Setup) - All Parallel
```bash
# Run all T001-T009 concurrently (different files)
for task in {T001..T009}; do
  execute_task $task &
done
wait
```

### Phase 2 (Foundational) - All Parallel
```bash
# T010-T018 can all run concurrently
pytest tests/runtime/test_exit_code.py &           # T011-T014
pytest tests/runtime/test_runtime_config_snapshot.py &  # T016-T017
execute_task T010 &  # worst_of implementation
execute_task T015 &  # RuntimeConfigSnapshot implementation
wait
```

### Phase 3 (US1) - Tests Parallel, Implementation Sequential
```bash
# TDD Red Phase: All test tasks run in parallel
pytest tests/runtime/test_exit_handler.py::test_cleanup_emits_ok &  # T019
pytest tests/runtime/test_exit_handler.py::test_cleanup_returns_0 &  # T020
# ... (T021-T026 all parallel)
wait

# TDD Green Phase: Implementation tasks sequential (same file)
execute_task T027  # cleanup() signature
execute_task T028  # step 1
execute_task T029  # step 2
# ... (T030-T040 sequential)
```

### Phase 4-7 (US2-US5) - All User Stories Parallel
```bash
# After US1 complete, all user stories can proceed in parallel
execute_story US2 &  # T047-T071
execute_story US3 &  # T072-T080
execute_story US4 &  # T081-T085
execute_story US5 &  # T086-T092
wait
```

---

## Notes

- **[P] tasks** = different files, no dependencies, can run in parallel
- **[Story] label** maps task to specific user story for traceability
- Each user story is independently completable and testable
- **TDD workflow**: Verify tests fail before implementing (Red → Green → Refactor)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **Performance target**: Init-only cleanup <100ms (SC-008)
- **Coverage target**: ≥90% for runtime/exit_handler.py (T101)
- **Constitution alignment**: Article VIII (TDD), Article III (no LangSmith), Article X (secrets excluded)
- **Top-level design artifacts**: workflow.md, architecture_modules.md, module_schemas.md all referenced
