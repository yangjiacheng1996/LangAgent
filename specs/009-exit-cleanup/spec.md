# Feature Specification: Exit Cleanup & Doctor Self-Check

**Feature Branch**: `009-exit-cleanup`

**Created**: 2026-09-20

**Status**: Draft

**Input**: User description: "F09 — 退出清理（exit_cleanup 阶段 + doctor 自检）"

**Constitutional Alignment**: This specification aligns with Article XV (Top-Level Design Primacy) of the LangAgent Constitution. Required design artifacts have been reviewed:
- `harness/top_level_design/workflow.md#stage-exit_cleanup` — Stage 6 inputs, outputs, failure modes, exit codes
- `harness/top_level_design/architecture_modules.md#mod-runtime-exit-handler` — Module responsibilities, APIs, dependency matrix
- `harness/top_level_design/module_schemas.md` — DoctorReport, EvalReport, RuntimeConfigSnapshot, MetricsSnapshot, Span, AuditEntry schemas

**Key Constitutional Alignments**:
- **Article III** (LangSmith Isolation): Exit cleanup does not read LANGSMITH_* environment variables
- **Article IX** (Quality Diagnostics): Writes DoctorReport, EvalReport, MetricsSnapshot, Span, AuditEntry to disk
- **Article X** (Security & Privacy): Audit recorder flush happens in exit_cleanup stage; AuditEntry redacted before storage
- **Article XII** (Configuration Observability): RuntimeConfigSnapshot does not contain BaseChatModel instances

## Clarifications

### Session 2026-09-20

- Q: 当 write_reports() 写入报告文件时，如果目标文件已经存在（例如同一个 timestamp 的重复运行），系统应该如何处理？ → A: 直接覆盖已存在的文件（原子写入）
- Q: 当 check_instructions() 检查 instructions.md 的"最小可执行段落"时，具体的启发式规则应该是什么？ → A: 字符数 > 10 且包含 "you"（英文）或 "你"/"应该"（中文）关键词
- Q: 当 drain_spans() 或 drain_events() 返回空列表（没有数据）时，write_reports() 应该如何处理 JSONL 文件？ → A: 如果没有 span/event 数据，则不创建对应的 JSONL 文件
- Q: 当 check_skills() 发现某个 skill 的 SKILL.md frontmatter 格式错误或字段缺失时，应该返回什么状态？ → A: 返回 status="warn" 并在 detail 中列出有问题的 skill 名称（允许部分失败）
- Q: 当 metrics_collector.snapshot() 在步骤 5 失败后，步骤 8 write_reports() 使用"空 MetricsSnapshot"时，具体应该写入什么内容到报告文件？ → A: 写入一个带零值字段的 MetricsSnapshot（例如 token_usage=0, latency=0, cost=0）

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Graceful Cleanup After Normal Agent Run (Priority: P1)

As a developer running a LangAgent agent, when my agent completes its task (either successfully or with errors), the system should automatically clean up all resources, flush pending logs and metrics, close database connections, and write final reports to disk so that I can review execution traces and diagnose issues without resource leaks.

**Why this priority**: This is the core cleanup path that every `langagent run` execution must follow. Without this, resources leak and diagnostic data is lost.

**Independent Test**: Can be fully tested by running `langagent run [agent-dir]`, verifying that checkpointer connections are closed, metrics snapshot is written to `~/.local/share/langagent/reports/`, and span/event/audit data is appended to `~/.local/share/langagent/logs/<run-id>.jsonl`.

**Acceptance Scenarios**:

1. **Given** an agent has completed main_loop execution with final state and accumulated metrics, **When** exit_cleanup runs, **Then** checkpointer connection is closed, metrics are flushed, audit entries are written to disk, and exit code 0 is returned
2. **Given** multiple resources need cleanup (event bus, metrics, audit, checkpointer), **When** one resource flush fails (e.g., disk full), **Then** cleanup continues with remaining resources and returns appropriate exit code (4 for I/O failure)
3. **Given** an agent run accumulated spans and events during execution, **When** exit_cleanup runs, **Then** all spans are drained to `logs/<run-id>.jsonl` in JSONL format with 7 required fields (trace_id, span_id, parent_span_id, name, start, end, attributes)

---

### User Story 2 - Doctor Self-Check Reporting (Priority: P1)

As a developer setting up a LangAgent environment, when I run `langagent doctor`, the system should check model endpoint connectivity, checkpointer functionality, skill validity, and instructions completeness, then write a comprehensive DoctorReport to disk showing which checks passed, warned, or failed so that I can diagnose configuration issues before running my agent.

**Why this priority**: Doctor is the primary diagnostic tool. Without proper reporting, users cannot identify setup issues.

**Independent Test**: Can be fully tested by running `langagent doctor` with various configuration states (valid model, invalid endpoint, missing skills), verifying that DoctorReport is written to `~/.local/share/langagent/reports/doctor-<timestamp>.json` with correct check results.

**Acceptance Scenarios**:

1. **Given** a valid model endpoint configuration, **When** doctor check_model runs with injected probe function, **Then** DoctorCheckResult shows status="ok" with connectivity details
2. **Given** an unreachable model endpoint, **When** doctor check_model runs, **Then** DoctorCheckResult shows status="error" with timeout/unreachable details
3. **Given** some skills have malformed SKILL.md frontmatter, **When** doctor check_skills runs, **Then** DoctorCheckResult shows status="warn" with detail listing problematic skill names
4. **Given** all 4 checks (model, checkpointer, skills, instructions) complete, **When** doctor report is generated, **Then** DoctorReport contains overall status ("ok"/"warn"/"error"), all check results, and RuntimeConfigSnapshot (without BaseChatModel or secrets)
5. **Given** doctor checks complete, **When** exit_cleanup writes the report, **Then** report is persisted to `reports/doctor-<timestamp>.json` in valid JSON format

---

### User Story 3 - Eval Report Aggregation and Persistence (Priority: P2)

As a developer running evaluation tasks, when `langagent eval` completes all tasks, the system should aggregate pass rate, latency metrics (P50, P95), token usage, and cost estimates into an EvalReport and write it to disk so that I can track agent quality over time and compare evaluation runs.

**Why this priority**: Eval reporting is essential for quality tracking, but depends on successful eval task execution (F11).

**Independent Test**: Can be fully tested by mocking eval_runner to return an EvalRunResult with eval_report, then calling exit_cleanup with eval_report parameter, verifying that the report is written to `reports/<agent-dir>-<timestamp>.json`.

**Acceptance Scenarios**:

1. **Given** eval runner completed 10 tasks with 7 passing, **When** exit_cleanup receives eval_report with pass_rate=0.7, **Then** report is written to disk with correct pass_rate and task_results
2. **Given** eval runner accumulated token usage from multiple model calls, **When** exit_report is written, **Then** token_usage dictionary aggregates by model and cost_usd is calculated
3. **Given** eval_report and doctor_report are both provided to cleanup, **When** cleanup routes reports, **Then** eval_report takes precedence (run-in-eval scenario) and is written

---

### User Story 4 - Continue-on-Failure Cleanup (Priority: P2)

As a system operator, when any cleanup step fails (metrics flush timeout, audit write error, checkpointer close exception), the system should log the failure, continue with remaining cleanup steps, and return the most severe exit code so that I get maximum diagnostic data even during partial failures.

**Why this priority**: Resilient cleanup prevents cascading failures and resource leaks.

**Independent Test**: Can be fully tested by mocking individual cleanup steps to throw exceptions, verifying that subsequent steps still execute and worst_of() correctly prioritizes exit codes.

**Acceptance Scenarios**:

1. **Given** audit_recorder.flush() raises AuditFlushError (exit code 4), **When** cleanup continues, **Then** checkpointer.close(), metrics.snapshot(), and write_reports() all execute, and final exit code is 4
2. **Given** multiple failures occur (checkpointer close fails with exit code 1, report write fails with exit code 4), **When** cleanup completes, **Then** worst_of() returns exit code 4 (I/O failure has higher priority than generic failure)
3. **Given** event_bus.flush() times out after 5 seconds, **When** cleanup continues, **Then** timeout is logged but not counted as failure (exit code remains 0 if no other failures)
4. **Given** user presses Ctrl-C during any cleanup step, **When** cleanup completes, **Then** exit code 130 (SIGINT) is returned regardless of other failures (highest priority)

---

### User Story 5 - Init-Only Cleanup Mode (Priority: P3)

As a developer running `langagent init <name>`, when the command completes directory creation, the system should perform minimal cleanup (skip resource flushes, only emit lifecycle.init.end log) and return exit code 0 or 67 (name already exists) so that init remains fast and lightweight without unnecessary cleanup overhead.

**Why this priority**: Init is a lightweight setup command that doesn't accumulate runtime state. Full cleanup is unnecessary.

**Independent Test**: Can be fully tested by calling cleanup(state=None, config=None, init_only=True) and verifying that steps 1-8 are skipped, only lifecycle.init.end and exit_cleanup.ok logs are emitted, and exit code 0 is returned.

**Acceptance Scenarios**:

1. **Given** langagent init successfully created agent directory, **When** cleanup(init_only=True) is called, **Then** event_bus.flush, metrics.flush, audit.flush, checkpointer.close, snapshot, drain_spans, drain_events, write_reports are all skipped
2. **Given** init-only cleanup mode, **When** cleanup completes, **Then** la.lifecycle.init.end and la.runtime.exit_cleanup.ok logs are emitted and exit code 0 is returned

---

### Edge Cases

- What happens when both eval_report and doctor_report are provided to cleanup()? (Routing priority: eval_report wins in run-in-eval scenarios)
- How does cleanup handle missing MetricsSnapshot (if metrics_collector.snapshot() fails)? (Write zero-valued MetricsSnapshot with all required fields set to 0, record exit code 70)
- What happens if spans or events cannot be drained due to buffer persistence failure? (Record exit code 4, buffer remains intact for retry, continue cleanup)
- How does cleanup prevent stage capability violations (e.g., model re-instantiation during exit_cleanup)? (Apply @cross_cutting_stage_guard_decorator with monkeypatch blacklist)
- What if checkpointer is already closed when cleanup runs? (close_checkpointer should be idempotent and handle already-closed state gracefully)
- How does cleanup handle concurrent flush operations? (Steps are sequential, not concurrent, to maintain strict cleanup ordering)
- What if report file already exists when writing? (Atomically overwrite the existing file)
- What if drain_spans() or drain_events() returns empty list? (Do not create JSONL file; file absence indicates no trace data)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement cleanup(state, config, *, doctor_report, eval_report, metrics_snapshot, init_only) with 7 parameters (2 positional + 5 keyword-only)
- **FR-002**: System MUST execute cleanup in strict 11-step sequence: (1) event_bus.flush(timeout=5), (2) metrics.flush(), (3) audit.flush(), (4) checkpointer.close(), (5) metrics.snapshot(), (6) drain_spans(), (7) drain_events(), (8) write_reports(), (9) emit la.runtime.exit_cleanup.ok/fail, (10) emit la.lifecycle.init.end (only if init_only=True), (11) return worst_of(exit_codes)
- **FR-003**: System MUST continue cleanup after any single step failure (continue-on-failure strategy)
- **FR-004**: System MUST close checkpointer connections (MemorySaver, SqliteSaver, PostgresSaver) in step 4
- **FR-005**: System MUST write MetricsSnapshot to `~/.local/share/langagent/reports/<run-id>.json`; if metrics_collector.snapshot() fails, write zero-valued MetricsSnapshot with all numeric fields set to 0
- **FR-006**: System MUST write Span data to `~/.local/share/langagent/logs/<run-id>.jsonl` in JSONL format (one span per line); if no spans exist, do not create the file
- **FR-007**: System MUST write Event data to `~/.local/share/langagent/logs/<run-id>.jsonl` in JSONL format (one event per line); if no events exist, do not create the file
- **FR-008**: System MUST write DoctorReport to `~/.local/share/langagent/reports/doctor-<timestamp>.json` when doctor_report parameter is provided; if file exists, atomically overwrite it
- **FR-009**: System MUST write EvalReport to `~/.local/share/langagent/reports/<agent-dir>-<timestamp>.json` when eval_report parameter is provided; if file exists, atomically overwrite it
- **FR-010**: System MUST implement worst_of(codes: list[int]) -> int function that returns highest priority exit code according to priority table (130 > 70 > 67 > 78 > 66 > 65 > 64 > 5 > 4 > 3 > 2 > 1 > 0)
- **FR-011**: System MUST implement run_doctor_checks(config, loaded, *, model_probe_fn, checkpoint_probe_fn) with 4 check functions: check_model, check_checkpointer, check_skills, check_instructions
- **FR-011a**: System MUST implement check_instructions() with heuristic validation: (character count > 10) AND (contains "you" OR contains "你" OR contains "应该"). Returns status="ok" when both conditions met, status="warn" otherwise
- **FR-011b**: System MUST implement check_skills() to return status="warn" when any number of skills have malformed SKILL.md frontmatter or missing required fields (partial failure); returns status="error" only when all skills fail or skills/ directory does not exist; detail MUST list problematic skill names
- **FR-012**: System MUST inject model_probe_fn and checkpoint_probe_fn via keyword-only parameters (no direct primitives instantiation in exit_handler)
- **FR-013**: System MUST return DoctorCheckResult with status="skipped" when probe_fn is None
- **FR-014**: System MUST aggregate 4 DoctorCheckResults into overall status ("ok"/"warn"/"error")
- **FR-015**: System MUST construct RuntimeConfigSnapshot.from_runtime_config(config) excluding model, cli_args, env_vars, dotenv_values, builtin_defaults
- **FR-016**: System MUST write Span with exactly 7 fields: trace_id, span_id, parent_span_id, name, start, end, attributes
- **FR-017**: System MUST route report writes based on provided parameters: eval_report > doctor_report > metrics_snapshot_only
- **FR-018**: System MUST emit la.runtime.exit_cleanup.start at stage entry
- **FR-019**: System MUST emit la.runtime.exit_cleanup.ok on success or la.runtime.exit_cleanup.fail on any failure
- **FR-020**: System MUST emit la.lifecycle.init.end only when init_only=True
- **FR-021**: System MUST skip steps 1-8 when init_only=True (only execute steps 9-11: emit logs and return 0)
- **FR-022**: System MUST apply @cross_cutting_stage_guard_decorator('exit_cleanup') with monkeypatch blacklist to prevent stage capability violations
- **FR-023**: System MUST not read LANGSMITH_* environment variables during cleanup (Constitution Article III)
- **FR-024**: System MUST handle event_bus.flush(timeout=5) timeout as non-failure (log to la.cross_cutting.event_handler_error but continue with exit code 0); timeout does NOT contribute to failed_exit_codes list
- **FR-025**: System MUST keep drain buffer intact when drain_spans() or drain_events() fails (allow retry); failed drain records exit code 4 but buffer state remains unchanged for subsequent retry attempts

### Key Entities

- **RuntimeExitHandler**: Main class implementing cleanup logic with cleanup(), close_checkpointer(), write_reports() methods
- **ExitCode**: Exit code priority table and worst_of() arbitration function
- **DoctorCheckResult**: Single check result with check_name, status ("ok"/"warn"/"error"/"skipped"), detail
- **RuntimeConfigSnapshot**: Serializable config subset (8 fields: schema_version, model_provider, model_name, model_base_url, checkpointer, middleware_ids, skill_dirs, log_level, guardrail_allow_internal_endpoints)
- **DoctorReport**: 6 fields (report_id, generated_at, checks, overall, agent_dir, runtime)
- **EvalReport**: 9 fields (report_id, generated_at, agent_dir, task_results, pass_rate, p50_latency_ms, p95_latency_ms, token_usage, cost_usd)
- **MetricsSnapshot**: Consumed from F02, written to reports/ directory
- **Span**: 7 fields (trace_id, span_id, parent_span_id, name, start, end, attributes), written to logs/ JSONL
- **Event**: Consumed from F03, written to logs/ JSONL
- **AuditEntry**: Consumed from F04, written to audit.jsonl

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every langagent run/eval/doctor/init execution completes cleanup without resource leaks (checkpointer connections closed, file handles released)
- **SC-002**: Cleanup continues after single-step failure with success rate of remaining steps ≥ 90% (continue-on-failure verified)
- **SC-003**: Exit code priority correctly resolves in 100% of multi-failure scenarios (130 always wins, then 70, then other codes by priority)
- **SC-004**: DoctorReport written to disk contains valid JSON and all 4 check results (model, checkpointer, skills, instructions); check_instructions validates using heuristic: character count > 10 AND contains keyword ("you" / "你" / "应该")
- **SC-005**: EvalReport written to disk contains valid JSON with pass_rate, latency metrics, and token usage
- **SC-006**: Span JSONL files are grep-able (one span per line, no pretty-printing) and contain exactly 7 fields per line
- **SC-007**: RuntimeConfigSnapshot excludes BaseChatModel instances and serializes to JSON without errors
- **SC-008**: Init-only cleanup mode completes in under 100ms (skips all resource-intensive steps)
- **SC-009**: Cleanup emits correct lifecycle logs (la.lifecycle.init.end only for init_only=True, la.runtime.exit_cleanup.ok/fail for all modes)
- **SC-010**: Stage capability violations (model re-instantiation, config re-parsing, dir reload) raise StageCapabilityViolationError with exit code 1

## Assumptions

- F02 (cross_cutting_logger) provides logger.drain_spans() API that returns list[Span] and raises SpanDrainError on buffer persistence failure
- F03 (protocol_event_bus) provides event_bus.drain_events() API that returns list[Event], event_bus.flush(timeout=5) API, and raises EventDrainError on drain failure
- F04 (cross_cutting_audit_recorder) provides audit_recorder.flush() API that raises AuditFlushError on failure
- F02 (cross_cutting_metrics_collector) provides metrics_collector.flush() and metrics_collector.snapshot() APIs
- F01 (primitives_checkpoint_adapter) provides close(checkpointer) API that raises CheckpointerCloseError on failure
- F08 (runtime_main_loop_dispatcher) provides build_doctor_probes() factory that returns (model_probe_fn, checkpoint_probe_fn) tuple for doctor checks
- F06 (cross_cutting_stage_guard) provides @cross_cutting_stage_guard_decorator that enforces stage capability boundaries via monkeypatch blacklist
- Doctor probe functions (model_probe_fn, checkpoint_probe_fn) are injected by F10 (cli_runner) via run_doctor_checks() keyword-only parameters
- Exit codes follow standard priority table: 130 (SIGINT) > 70 (EX_SOFTWARE) > 67 (name_already_exists) > 78 (EX_CONFIG) > 66 (EX_NOINPUT) > 65 (EX_DATAERR) > 64 (EX_USAGE) > 5 (config_error) > 4 (I/O) > 3 (data_error) > 2 (usage_error) > 1 (generic_failure) > 0 (success)
- Report write paths follow XDG Base Directory Specification: `~/.local/share/langagent/reports/` and `~/.local/share/langagent/logs/`
- JSONL format requires single-line JSON per record (no pretty-printing) to remain grep-able
- RuntimeConfigSnapshot schema_version is v0.2.0 (includes guardrail_allow_internal_endpoints field)
- LoadedAgent schema_version is v0.2.0 (5 fields without compiled_graph)
- Cleanup ordering is strict and must not be reordered (event_bus → metrics → audit → checkpointer → snapshot → drain → write → logs → return)
- Init-only cleanup mode (init_only=True) is triggered only by langagent init command via F10 dispatch
