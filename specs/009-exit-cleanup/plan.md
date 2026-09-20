# Implementation Plan: Exit Cleanup & Doctor Self-Check

**Branch**: `009-exit-cleanup` | **Date**: 2026-09-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-exit-cleanup/spec.md`

**Note**: This plan implements F09 (runtime_exit_handler module), the exit_cleanup stage (stage 6 of 6), and doctor self-check functionality.

## Summary

Implement the exit_cleanup stage of the LangAgent runtime, which performs resource cleanup, writes diagnostic reports (DoctorReport, EvalReport, MetricsSnapshot), flushes logs/metrics/audit data, and returns appropriate exit codes. This feature also implements the 4-item doctor self-check functionality (model connectivity, checkpointer, skills, instructions validation) that helps users diagnose configuration issues before running agents.

**Technical Approach**:
- Implement 11-step cleanup sequence with continue-on-failure strategy
- Use exit code priority arbitration (worst_of function with 13-level priority table)
- Write reports atomically to `~/.local/share/langagent/` following XDG Base Directory Specification
- Apply stage capability guards to prevent model re-instantiation/config re-parsing during cleanup
- Support init-only cleanup mode (skips resource-intensive steps for fast init command completion)

## Technical Context

**Language/Version**: Python 3.11+ (per pyproject.toml requires-python field)

**Primary Dependencies**: 
- LangChain (BaseChatModel, BaseCheckpointSaver interfaces)
- LangGraph (checkpointer closing, state management)
- Pydantic (DoctorReport, EvalReport, RuntimeConfigSnapshot models)

**Storage**: 
- File system: `~/.local/share/langagent/reports/` (JSON reports)
- File system: `~/.local/share/langagent/logs/` (JSONL span/event traces)
- File system: `~/.local/share/langagent/audit.jsonl` (audit entries, managed by F04)

**Testing**: pytest with TDD workflow (Red → Green → Refactor per Constitution Article VIII)

**Target Platform**: Linux server (primary), macOS (development), packaged as single-file binary (PyInstaller per Constitution Article XI)

**Project Type**: CLI application (langagent run/eval/doctor/init subcommands)

**Performance Goals**: 
- Init-only cleanup completes in < 100ms (SC-008)
- Event bus flush timeout = 5s (best-effort, non-blocking)
- Cleanup continue-on-failure success rate ≥ 90% (SC-002)

**Constraints**: 
- Must not read LANGSMITH_* environment variables (Article III)
- Must not re-instantiate model/checkpointer during cleanup (stage capability boundary)
- Cleanup ordering is strict and immutable (11 steps sequential)
- Reports must be JSON-serializable (RuntimeConfigSnapshot excludes BaseChatModel instances)

**Scale/Scope**: 
- 27 functional requirements (FR-001 to FR-025)
- 8 edge cases with explicit handling strategies
- 4 doctor check functions
- 5 user scenarios (P1: run cleanup + doctor; P2: eval reporting + continue-on-failure; P3: init-only)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article I: Project Identity & Boundaries
✅ **PASS** - F09 is part of runtime layer, not exposed as SDK. No public API surface for third-party import. Only internal module consumed by F10 (cli_runner).

### Article III: LangSmith Isolation
✅ **PASS** - FR-023 explicitly prohibits reading LANGSMITH_* environment variables. audit_recorder.flush() does not attempt LangSmith upload. All reports write to local file system only.

### Article VIII: TDD Methodology
✅ **PASS** - Spec includes 22+ test cases in §四 (test_cleanup_emits_ok, test_cleanup_writes_metrics_snapshot, test_cleanup_continues_after_step_failure, test_worst_of_function, test_doctor_check_model_endpoint_reachable, etc.). Red → Green → Refactor workflow enforced.

### Article IX: Quality Diagnostics Matrix
✅ **PASS** - F09 writes 5 diagnostic outputs:
- **Tracing**: Span JSONL (7 fields per Constitution Article XII §3)
- **Monitoring**: MetricsSnapshot (token usage, latency, cost)
- **Evaluation**: EvalReport (pass_rate, p50/p95 latency, aggregated metrics)
- **Testing**: DoctorReport (4 checks: model, checkpointer, skills, instructions)
- **Guardrails**: AuditEntry flush (redacted, written to audit.jsonl)

### Article X: Security & Privacy
✅ **PASS** - RuntimeConfigSnapshot.from_runtime_config() excludes secrets (cli_args, env_vars, dotenv_values, builtin_defaults per FR-015). AuditEntry redaction handled by F04 before flush. No PII in reports.

### Article XII: Configuration Observability
✅ **PASS** - RuntimeConfigSnapshot schema (8 fields) excludes BaseChatModel instances per FR-015. JSON-serializable. DoctorReport embeds RuntimeConfigSnapshot instead of full RuntimeConfig.

### Article XV: Top-Level Design Primacy
✅ **PASS** - Spec references 3 top-level artifacts:
- `workflow.md#stage-exit_cleanup` (stage 6 inputs/outputs/failure modes)
- `architecture_modules.md#mod-runtime-exit-handler` (module API, dependency matrix)
- `module_schemas.md` (DoctorReport, EvalReport, RuntimeConfigSnapshot, MetricsSnapshot schemas)

### Post-Design Re-Check

**Status**: ✅ All gates pass after Phase 1 design completion

**Article I**: No new SDK surface introduced. RuntimeExitHandler, DoctorCheckResult, ExitCode remain internal.

**Article III**: data-model.md confirms RuntimeConfigSnapshot excludes LangSmith-related fields. No LANGSMITH_* env var access in any schema.

**Article VIII**: quickstart.md provides 5 runnable TDD validation scenarios. research.md documents all technical decisions with rationale.

**Article IX**: data-model.md defines schemas for all 5 diagnostic outputs (Span, MetricsSnapshot, EvalReport, DoctorReport, AuditEntry).

**Article X**: RuntimeConfigSnapshot.from_runtime_config() factory method explicitly excludes cli_args, env_vars, dotenv_values, builtin_defaults per data-model.md §4.

**Article XII**: DoctorReport embeds RuntimeConfigSnapshot (not RuntimeConfig). Verified JSON-serializable in quickstart.md Scenario 1.

**Article XV**: All 3 top-level artifacts remain referenced. data-model.md schemas align with module_schemas.md definitions.

**Conclusion**: No constitutional violations introduced during Phase 1 design. Ready for Phase 2 (/speckit.tasks).

## Project Structure

### Documentation (this feature)

```text
specs/009-exit-cleanup/
├── plan.md              # This file
├── research.md          # Phase 0: Exit code arbitration, JSONL atomicity, idempotent checkpointer close
├── data-model.md        # Phase 1: DoctorCheckResult, ExitCode priority table, cleanup step state machine
├── quickstart.md        # Phase 1: Run doctor, trigger cleanup with mocked failures, verify continue-on-failure
├── contracts/           # Phase 1: (N/A - internal runtime module, no external contract surface)
└── tasks.md             # Phase 2: (created by /speckit.tasks, not by this command)
```

### Source Code (repository root)

```text
langagent/
├── runtime/
│   ├── exit_handler.py          # RuntimeExitHandler class, cleanup() entry point, close_checkpointer(), write_reports()
│   ├── exit_code.py             # EXIT_CODE_PRIORITY list, worst_of(codes) arbitration function
│   └── doctor_check.py          # DoctorCheckResult model, run_doctor_checks(), check_model/checkpointer/skills/instructions
├── cross_cutting/
│   ├── logger.py                # (F02) drain_spans() API consumed by F09
│   ├── metrics_collector.py     # (F02) flush(), snapshot() APIs consumed by F09
│   ├── audit_recorder.py        # (F04) flush() API consumed by F09
│   └── stage_guard.py           # (F06) @cross_cutting_stage_guard_decorator applied to cleanup()
├── protocol/
│   └── event_bus.py             # (F03) flush(timeout=5), drain_events() APIs consumed by F09
└── primitives/
    └── checkpoint_adapter.py    # (F01) close(checkpointer) API consumed by F09

tests/
├── runtime/
│   ├── test_exit_handler.py     # ≥22 test cases (cleanup main flow, failure paths, init-only mode)
│   ├── test_exit_code.py        # ≥5 test cases (worst_of unit tests, priority resolution)
│   └── test_doctor_checks.py    # ≥11 test cases (4 check functions, probe injection, skipped status)
└── fixtures/
    └── run_id_generator.py      # Test helper for generating unique run IDs
```

**Structure Decision**: Single-project Python package structure. F09 is runtime layer module, depends on F01-F04, F06, F08, F10. No frontend/backend split. CLI entry points handled by F10 (cli_runner).

## Complexity Tracking

> No constitutional violations require justification. All gates pass.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | N/A | N/A |

---

## Phase 0: Research

### Research Tasks

1. **Exit Code Priority Arbitration**
   - **Question**: How to implement worst_of() function that correctly prioritizes 13 exit codes (130 > 70 > 67 > 78 > 66 > 65 > 64 > 5 > 4 > 3 > 2 > 1 > 0) when multiple failures occur?
   - **Context**: FR-010 requires priority table lookup. Multiple failures must return highest-priority code. Edge case: empty list should return 0.

2. **JSONL Atomic Write Patterns**
   - **Question**: How to atomically append spans/events to JSONL files to prevent corruption during concurrent writes or process crashes?
   - **Context**: FR-006, FR-007 require JSONL format (one record per line). Spans and events may be written concurrently by different cleanup steps. File must remain grep-able.

3. **Idempotent Checkpointer Closing**
   - **Question**: How to make close_checkpointer() idempotent across MemorySaver, SqliteSaver, PostgresSaver implementations?
   - **Context**: Edge case: checkpointer may already be closed when cleanup runs. FR-004 requires graceful handling without exceptions.

4. **Continue-on-Failure State Tracking**
   - **Question**: What data structures track failed_steps and failed_exit_codes during cleanup to ensure all 11 steps attempt execution even after failures?
   - **Context**: FR-003 requires continue-on-failure. Each step failure must record exit code, but not halt execution. Final worst_of() call aggregates all codes.

5. **RuntimeConfigSnapshot Serialization**
   - **Question**: How to safely exclude BaseChatModel instances and secrets (cli_args, env_vars) from RuntimeConfigSnapshot without breaking Pydantic JSON serialization?
   - **Context**: FR-015, SC-007 require JSON-serializable snapshot. DoctorReport embeds RuntimeConfigSnapshot. Cannot serialize BaseChatModel (contains unpicklable GRPC connections).

### Research Outputs

See [research.md](./research.md) for consolidated findings, decisions, and rationale.

---

## Phase 1: Design & Contracts

### 1. Data Model

See [data-model.md](./data-model.md) for:
- **DoctorCheckResult**: Pydantic model with check_name, status (Literal["ok", "warn", "error", "skipped"]), detail fields
- **ExitCode Priority Table**: Enum or dict mapping exit codes to priority ranks (1 = highest = 130, 13 = lowest = 0)
- **CleanupStepState**: Track execution status of 11 cleanup steps (pending, running, succeeded, failed, skipped, timed_out)
- **RuntimeConfigSnapshot**: 8-field frozen Pydantic model (schema_version, model_provider, model_name, model_base_url, checkpointer, middleware_ids, skill_dirs, log_level, guardrail_allow_internal_endpoints)

### 2. Interface Contracts

**N/A** - F09 is internal runtime module. No external API surface. Contracts are internal Python function signatures:
- `cleanup(state, config, *, doctor_report, eval_report, metrics_snapshot, init_only) -> int`
- `run_doctor_checks(config, loaded, *, model_probe_fn, checkpoint_probe_fn) -> list[DoctorCheckResult]`
- `worst_of(codes: list[int]) -> int`

### 3. Quickstart Validation

See [quickstart.md](./quickstart.md) for:
- **Scenario 1**: Run `langagent doctor` with invalid model endpoint → verify DoctorReport contains status="error" for check_model
- **Scenario 2**: Mock audit_recorder.flush() to raise AuditFlushError → verify cleanup continues and returns exit code 4
- **Scenario 3**: Call cleanup(init_only=True) → verify steps 1-8 skipped, lifecycle.init.end log emitted, completes in < 100ms
- **Scenario 4**: Provide both eval_report and doctor_report to cleanup() → verify eval_report written (routing priority)
- **Scenario 5**: Mock metrics_collector.snapshot() to return None → verify zero-valued MetricsSnapshot written, exit code 70

---

## Dependencies

### Upstream (F09 depends on)
- **F01** (primitives_checkpoint_adapter): close(checkpointer) API, CheckpointerCloseError exception
- **F02** (cross_cutting_logger): drain_spans() API, SpanDrainError exception
- **F02** (cross_cutting_metrics_collector): flush(), snapshot() APIs
- **F03** (protocol_event_bus): flush(timeout=5), drain_events() APIs, EventDrainError exception
- **F04** (cross_cutting_audit_recorder): flush() API, AuditFlushError exception
- **F06** (cross_cutting_stage_guard): @cross_cutting_stage_guard_decorator, StageCapabilityViolationError
- **F08** (runtime_main_loop_dispatcher): build_doctor_probes() factory returning (model_probe_fn, checkpoint_probe_fn) tuple

### Downstream (F09 consumed by)
- **F10** (cli_runner): Calls cleanup() at end of run/eval/doctor/init subcommands; injects doctor probe functions via run_doctor_checks()
- **F11** (eval_runner): Passes eval_report to cleanup() after eval tasks complete

### Critical Path
F09 is on critical path for **all 4 CLI subcommands** (run, eval, doctor, init). Blocks F10 integration and F12 (binary packaging).

---

## Risk Analysis

### High Risk
1. **Continue-on-failure complexity**: Mocking 11 steps with different failure modes (exceptions, timeouts, None returns) requires extensive test coverage. Mitigation: TDD with ≥22 test cases per spec §四.
2. **Exit code priority bugs**: worst_of() must handle all 13 codes + empty list + duplicate codes correctly. Mitigation: Exhaustive unit tests in test_exit_code.py with priority table verification.

### Medium Risk
1. **Checkpointer idempotence**: SqliteSaver/PostgresSaver may not have idempotent close() methods. Mitigation: Research Phase 0 task 3, wrap close() in try-except, check connection state before closing.
2. **JSONL corruption**: Concurrent writes or partial writes during crash may corrupt JSONL files. Mitigation: Research Phase 0 task 2, use atomic write-then-rename pattern.

### Low Risk
1. **Init-only performance**: 100ms target may be tight if event_bus/metrics/audit imports are slow. Mitigation: Profile import time, lazy-load heavy modules.

---

## Testing Strategy

### Unit Tests (≥38 total per spec)
- **test_exit_handler.py** (≥22): cleanup main flow, failure paths, init-only mode, report routing, stage guard violations
- **test_exit_code.py** (≥5): worst_of() with all priority combinations, empty list, duplicate codes
- **test_doctor_checks.py** (≥11): 4 check functions, probe injection, skipped status when probe_fn=None, overall status aggregation

### Test Fixtures and Helpers
- **tests/fixtures/run_id_generator.py**: Helper utility for generating unique run IDs in tests (ensures consistent test data isolation and report file naming)

### Integration Tests
- End-to-end cleanup after real `langagent run` execution (verify checkpointer closed, files written)
- Doctor checks with real model endpoint (probe connectivity)
- Continue-on-failure with real disk-full scenario (verify remaining steps execute)

### Acceptance Criteria Validation
- SC-001: Resource leak detection (lsof checks no open file handles after cleanup)
- SC-002: Continue-on-failure rate ≥ 90% (inject failures in 10% of cleanup runs, verify 90% still succeed)
- SC-008: Init-only < 100ms (time.perf_counter profiling)

---

## Implementation Notes

### Cleanup Step Sequencing
```python
# Strict ordering (FR-002)
1. event_bus.flush(timeout=5)      # Best-effort, timeout not failure
2. metrics_collector.flush()        # Persist accumulated metrics
3. audit_recorder.flush()           # Write audit entries before closing DB
4. checkpoint_adapter.close()       # Close DB connections
5. metrics_snapshot = metrics_collector.snapshot()  # Take final snapshot
6. spans = logger.drain_spans()     # Drain buffered spans
7. events = event_bus.drain_events()  # Drain buffered events
8. write_reports(state, config, doctor_report, eval_report, metrics_snapshot, spans, events)
9. emit la.runtime.exit_cleanup.ok / fail
10. emit la.lifecycle.init.end (only if init_only=True)
11. return worst_of(failed_exit_codes + [0])
```

### Doctor Check Injection Pattern
```python
# F10 dispatch calls F08 build_doctor_probes() to get probe functions
model_probe_fn, checkpoint_probe_fn = build_doctor_probes(config)

# F10 then injects probes into F09 run_doctor_checks()
check_results = run_doctor_checks(
    config, loaded,
    model_probe_fn=model_probe_fn,
    checkpoint_probe_fn=checkpoint_probe_fn
)
```

### Exit Code Priority Lookup
```python
EXIT_CODE_PRIORITY = {
    130: 1,   # SIGINT (highest)
    70: 2,    # EX_SOFTWARE
    67: 3,    # name_already_exists
    78: 4,    # EX_CONFIG
    66: 5,    # EX_NOINPUT
    65: 6,    # EX_DATAERR
    64: 7,    # EX_USAGE
    5: 8,     # config_error
    4: 9,     # I/O
    3: 10,    # data_error
    2: 11,    # usage_error
    1: 12,    # generic_failure
    0: 13     # success (lowest)
}

def worst_of(codes: list[int]) -> int:
    if not codes:
        return 0
    return min(codes, key=lambda c: EXIT_CODE_PRIORITY.get(c, 999))
```

---

## Deliverables Checklist

- [ ] Phase 0: research.md (exit code arbitration, JSONL atomicity, idempotent close, continue-on-failure tracking, snapshot serialization)
- [ ] Phase 1: data-model.md (DoctorCheckResult, ExitCode, CleanupStepState, RuntimeConfigSnapshot schemas)
- [ ] Phase 1: quickstart.md (5 validation scenarios)
- [ ] Phase 1: Constitution Check re-evaluation (post-design gate)
- [ ] (Phase 2 tasks.md generated by /speckit.tasks command, not by this plan)

---

## Next Steps

1. Execute Phase 0 research (5 tasks above)
2. Generate data-model.md, quickstart.md (Phase 1)
3. Re-check Constitution gates post-design
4. Await /speckit.tasks command for Phase 2 task breakdown
