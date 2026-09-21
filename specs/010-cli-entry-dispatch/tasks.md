# Tasks: CLI Entry and Subcommand Dispatch

**Input**: Design documents from `/specs/010-cli-entry-dispatch/`

**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Per Constitution Article VIII (TDD), this feature includes ≥45 test cases following Red-Green-Refactor workflow. Tests MUST be written first and FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

**TDD Workflow**: Tasks marked [P] indicate file-level independence (no merge conflicts), but execution MUST follow Red-Green-Refactor cycle per Constitution Article VIII. Write one test → watch it FAIL → implement → watch it PASS → refactor → repeat.

## Path Conventions

Paths shown below follow single project structure at repository root:
- **Source**: `langagent/cli/` (new), `langagent/__main__.py` (new)
- **Tests**: `tests/cli/`
- **Fixtures**: `tests/fixtures/minimal_agent/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic CLI structure

- [X] T001 Create CLI module directory structure `langagent/cli/` with `__init__.py`
- [X] T002 Create PyInstaller entry point `langagent/__main__.py` that imports cli_runner.main()
- [X] T003 [P] Create test directory structure `tests/cli/` with `__init__.py`
- [X] T004 [P] Create minimal agent fixture in `tests/fixtures/minimal_agent/` with instructions.md, agent.py, pyproject.toml, .env.example

---

## Phase 2: Foundation (Blocking Prerequisites)

**Purpose**: Core CliArgs schema and parser infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Define CliArgs Pydantic frozen model in `langagent/cli/runner.py` with all fields (subcommand, agent_dir, cli_args, name, model, model_provider, model_base_url, checkpointer, middleware, max_turns, thread_id, grader_only, task, report_format, checks)
- [X] T006 Define FormatterContext dataclass in `langagent/cli/output_formatter.py` with fields (is_tty, enable_color, terminal_width)
- [X] T007 Create stub functions in `langagent/cli/parser.py`: build_parser() and ns_to_cli_args()
- [X] T008 Create stub functions in `langagent/cli/runner.py`: parse_argv(), dispatch(), main()
- [X] T009 Create stub functions in `langagent/cli/output_formatter.py`: format_chat_message(), format_eval_report(), format_eval_report_stdout(), format_doctor_report(), format_doctor_report_stdout()

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Initialize New Agent (Priority: P1) 🎯 MVP

**Goal**: Enable developers to bootstrap new LangAgent projects with correct directory structure via `langagent init <name>`

**Independent Test**: Run `langagent init myagent` and verify directory structure matches Constitution Article V mandatory layout

### Tests for User Story 1 (TDD Required per Article VIII)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T010 [P] [US1] Test: argparse init subcommand accepts name positional arg in tests/cli/test_parser.py::test_parse_init_name
- [X] T011 [P] [US1] Test: argparse init rejects invalid name (123invalid) with exit code 2 in tests/cli/test_parser.py::test_parse_init_name_invalid
- [X] T012 [P] [US1] Test: dispatch init calls dir_loader.write_template() once in tests/cli/test_runner.py::test_dispatch_init_calls_write_template
- [X] T013 [P] [US1] Test: init returns exit code 67 when directory exists in tests/cli/test_runner.py::test_dispatch_init_directory_exists
- [X] T014 [P] [US1] Test: end-to-end `langagent init demo` creates directory structure in tests/cli/test_cli_end_to_end.py::test_cli_init_creates_directory

### Implementation for User Story 1

- [X] T015 [P] [US1] Implement build_parser() in `langagent/cli/parser.py` with init subparser: add_parser('init') with name positional argument matching regex `^[a-zA-Z][a-zA-Z0-9_-]*$`
- [X] T016 [US1] Implement dispatch() init branch in `langagent/cli/runner.py`: call F06 dir_loader.write_template(target_dir, name), print creation summary, call F09 exit_handler.cleanup(init_only=True), return exit code
- [X] T017 [US1] Implement parse_argv() in `langagent/cli/runner.py`: call parser.build_parser().parse_args(argv), construct CliArgs frozen model, return CliArgs
- [X] T018 [US1] Implement main() in `langagent/cli/runner.py`: call parse_argv(sys.argv[1:]), call dispatch(args), catch KeyboardInterrupt → return 130, catch exceptions → return 1, return exit code to sys.exit()
- [X] T019 [US1] Add error handling in dispatch() init branch for F06 NameAlreadyExistsError → return exit code 67 (FR-CLI-015)
- [X] T020 [US1] Add error handling in dispatch() init branch for F06 TemplateLoadFailedError → return exit code 70
- [X] T020a [P] [US1] Test: dispatch init calls exit_handler.cleanup(init_only=True) in tests/cli/test_runner.py::test_dispatch_init_cleanup_init_only to verify FR-CLI-020 compliance

**Checkpoint**: At this point, `langagent init` should be fully functional and testable independently

---

## Phase 4: User Story 2 - Run Agent with Configuration Override (Priority: P1)

**Goal**: Enable developers to run agents with CLI flag overrides (--model, --model-provider, etc.) without editing .env file

**Independent Test**: Run `langagent run myagent --model gpt-4o --max-turns 3` and verify model override and turn limit

### Tests for User Story 2 (TDD Required per Article VIII)

- [X] T021 [P] [US2] Test: argparse run subcommand accepts optional agent_dir positional in tests/cli/test_parser.py::test_parse_run_with_agent_dir
- [X] T022 [P] [US2] Test: argparse run accepts --model, --model-provider, --checkpointer flags in tests/cli/test_parser.py::test_parse_run_with_overrides
- [X] T023 [P] [US2] Test: dispatch run calls 6 runtime stages in order in tests/cli/test_runner.py::test_dispatch_run_calls_6_stages
- [X] T024 [P] [US2] Test: dispatch run prints chat messages to stdout in [assistant] format in tests/cli/test_runner.py::test_dispatch_run_prints_chat_to_stdout
- [X] T025 [P] [US2] Test: dispatch run stderr contains logs, stdout does not in tests/cli/test_runner.py::test_dispatch_run_stderr_only_logs_no_chat
- [X] T026 [P] [US2] Test: end-to-end `langagent run` with --max-turns flag terminates correctly in tests/cli/test_cli_end_to_end.py::test_cli_run_with_mock_model
- [X] T026a [P] [US2] Test: CLI --model flag overrides .env MODEL_NAME in tests/cli/test_runner.py::test_dispatch_run_cli_overrides_env_model
- [X] T026b [P] [US2] Test: .env overrides built-in defaults when no CLI args in tests/cli/test_runner.py::test_dispatch_run_env_overrides_defaults

### Implementation for User Story 2

- [X] T027 [P] [US2] Implement build_parser() run subparser in `langagent/cli/parser.py`: add agent_dir positional (optional, default=cwd), add --model, --model-provider, --model-base-url, --checkpointer, --middleware, --max-turns (default 30, type int), --thread-id flags
- [X] T028 [US2] Implement dispatch() run branch in `langagent/cli/runner.py`: orchestrate 6 stages per FR-CLI-017: Stage 1-2: loaded = dir_loader.load(agent_dir), config = config_resolver.resolve(cli_args, agent_dir); Stage 3: model = F01 chat_model_factory.create(config), checkpoint = F01 checkpoint_adapter.create(config); Stage 4: final_config = config.with_model(model).with_checkpoint(checkpoint); Stage 5: graph = F01 state_graph_builder.build(loaded, final_config); Stage 6: state = AgentState(...), final_state = F08 main_loop_dispatcher.run_until_done(graph, state, max_turns); Cleanup: return F09 exit_handler.cleanup(final_state, final_config)
- [X] T029 [US2] Implement format_chat_message() in `langagent/cli/output_formatter.py`: accept message_dict (AIMessage.to_dict() result), extract content field, return formatted string "[assistant] <content>\n"
- [X] T030 [US2] Add stdout printing loop in dispatch() run branch after main_loop: iterate final_state["messages"], filter AIMessage types, call format_chat_message(msg.to_dict()), print to stdout with flush=True (FR-CLI-008)
- [X] T031 [US2] Add error handling in dispatch() run branch for F06 AgentDirNotFoundError → return exit code 66
- [X] T032 [US2] Add error handling in dispatch() run branch for F07 ConfigInvalidError → return exit code 78
- [X] T033 [US2] Add error handling in dispatch() run branch for F01 ModelTimeoutError → return exit code 70
- [X] T034 [US2] Add KeyboardInterrupt handling in main(): catch during dispatch, return exit code 130 (FR-CLI-016)

**Checkpoint**: At this point, `langagent run` should be fully functional with configuration overrides

---

## Phase 5: User Story 3 - Evaluate Agent Quality (Priority: P2)

**Goal**: Enable developers to run eval tasks from `evals/` directory and receive formatted reports with pass rate, latency, token usage

**Independent Test**: Create agent with 3 eval YAML files, run `langagent eval myagent`, verify 66% pass rate reported

### Tests for User Story 3 (TDD Required per Article VIII)

- [X] T035 [P] [US3] Test: argparse eval accepts --grader-only, --task, --report-format flags in tests/cli/test_parser.py::test_parse_eval_with_grader_only
- [X] T036 [P] [US3] Test: dispatch eval calls eval_runner.run() with config and args dict in tests/cli/test_runner.py::test_dispatch_eval_returns_cleanup_exit_code
- [X] T037 [P] [US3] Test: dispatch eval prints report to stdout in tests/cli/test_runner.py::test_dispatch_eval_prints_report_to_stdout
- [X] T038 [P] [US3] Test: format_eval_report_stdout() returns compact ASCII table in tests/cli/test_output_formatter.py::test_format_eval_report_stdout_compact
- [X] T039 [P] [US3] Test: end-to-end `langagent eval` executes tasks and displays pass rate in tests/cli/test_cli_end_to_end.py::test_cli_eval_with_tasks

### Implementation for User Story 3

- [X] T040 [P] [US3] Implement build_parser() eval subparser in `langagent/cli/parser.py`: add agent_dir positional (optional, default=cwd), add --grader-only {exact_match,contains,regex,llm_judge,tool_call_match}, --task <task_id>, --report-format {json,yaml,table} (default='table')
- [X] T041 [US3] Implement dispatch() eval branch in `langagent/cli/runner.py`: 在dispatch()函数顶部添加条件导入 `if args.subcommand == 'eval': from langagent.eval.runner import run as eval_runner_run`; 然后编排3 stages per FR-CLI-018: loaded = dir_loader.load(agent_dir), config = config_resolver.resolve(cli_args, agent_dir), construct args dict per FR-CLI-025: {'cli_args': vars(ns), 'grader_only': cli_args.grader_only, 'task': cli_args.task}, call result = eval_runner_run(agent_dir, config=config, args=args), print format_eval_report_stdout(result.eval_report), return exit_handler.cleanup(result.final_state, config, eval_report=result.eval_report)
- [X] T042 [US3] Implement format_eval_report_stdout() in `langagent/cli/output_formatter.py`: accept EvalReport, format compact table with columns (task_id, pass/fail, latency_ms, grader), calculate overall pass rate percentage, return multi-line string
- [X] T043 [US3] Implement format_eval_report() in `langagent/cli/output_formatter.py`: accept EvalReport, format detailed report with per-task results, P50 latency, token usage summary, return multi-line string (file version, more verbose than stdout version)
- [X] T044 [US3] Add error handling in dispatch() eval branch for F11 EvalsDirMissingError → return exit code 66 (per workflow.md §langagent eval failure mode `evals_dir_missing`)
- [X] T045 [US3] Add error handling in dispatch() eval branch for F11 EvalTimeoutError → return exit code 70
- [X] T046 [US3] Add error handling in dispatch() eval branch for F11 EvalGraderUnknownError → return exit code 78
- [X] T046a [P] [US3] Test: dispatch eval aggregates multiple task failures via worst_of() in tests/cli/test_runner.py::test_dispatch_eval_aggregates_exit_codes to verify FR-CLI-027 (3 tasks fail with codes 1/70/78 → expect exit code 78 per priority 130>78>70>67>66>65>64>5>4>2>1>0)

**Checkpoint**: At this point, `langagent eval` should be fully functional with report formatting

---

## Phase 6: User Story 4 - Diagnose Agent Configuration Issues (Priority: P2)

**Goal**: Enable developers to diagnose configuration issues (model connectivity, checkpointer, skills, instructions) via `langagent doctor`

**Independent Test**: Create agent with misconfigurations, run `langagent doctor myagent`, verify report identifies all issues with actionable error messages

### Tests for User Story 4 (TDD Required per Article VIII)

- [X] T047 [P] [US4] Test: argparse doctor accepts --checks flag (comma-separated list) in tests/cli/test_parser.py::test_parse_doctor_with_checks
- [X] T048 [P] [US4] Test: dispatch doctor runs 4 checks via F09 run_doctor_checks() in tests/cli/test_runner.py::test_dispatch_doctor_runs_4_checks
- [X] T049 [P] [US4] Test: dispatch doctor prints report to stdout in tests/cli/test_runner.py::test_dispatch_doctor_prints_report_to_stdout
- [X] T050 [P] [US4] Test: format_doctor_report_stdout() shows 4 check results in tests/cli/test_output_formatter.py::test_format_doctor_report_stdout_shows_4_checks
- [X] T051 [P] [US4] Test: end-to-end `langagent doctor` displays check results and overall status in tests/cli/test_cli_end_to_end.py::test_cli_doctor_on_fresh_agent

### Implementation for User Story 4

- [X] T052 [P] [US4] Implement build_parser() doctor subparser in `langagent/cli/parser.py`: add agent_dir positional (optional, default=cwd), add --checks {model,checkpointer,skills,instructions} (comma-separated, defaults to all 4)
- [X] T053 [US4] Implement dispatch() doctor branch in `langagent/cli/runner.py`: orchestrate 3 stages per FR-CLI-019: loaded = dir_loader.load(agent_dir), config = config_resolver.resolve(cli_args, agent_dir), obtain probe functions via `from langagent.runtime.main_loop_dispatcher import build_doctor_probes; probe_model_fn, probe_checkpoint_fn = build_doctor_probes()`, call checks = F09 exit_handler.run_doctor_checks(config, loaded, model_probe_fn=lambda: probe_model_fn(config), checkpoint_probe_fn=lambda: probe_checkpoint_fn(config)), construct snapshot = RuntimeConfigSnapshot.from_runtime_config(config), construct report = DoctorReport(checks=checks, overall=..., runtime=snapshot), print format_doctor_report_stdout(report), return exit_handler.cleanup(None, config, doctor_report=report)
- [X] T054 [US4] Implement format_doctor_report_stdout() in `langagent/cli/output_formatter.py`: accept DoctorReport, format compact output with lines "✓ model: ok" / "✗ checkpointer: error - <detail>" for each check, display overall status line, return multi-line string
- [X] T055 [US4] Implement format_doctor_report() in `langagent/cli/output_formatter.py`: accept DoctorReport, format detailed report with check results, runtime config snapshot, recommendations, return multi-line string (file version)
- [X] T056 [US4] Add error handling in dispatch() doctor branch for check failures: aggregate via F09 worst_of() per FR-CLI-027
- [X] T056a [P] [US4] Test: dispatch doctor aggregates multiple check failures via worst_of() in tests/cli/test_runner.py::test_dispatch_doctor_aggregates_exit_codes to verify FR-CLI-027 (4 checks with 2 failures returning codes 1/70 → expect exit code 70 per priority 130>78>70>67>66>65>64>5>4>2>1>0)

**Checkpoint**: All 4 user stories should now be independently functional

---

## Phase 7: CLI Parser - Remaining Tests and Refinements

**Purpose**: Complete test coverage for cli_parser module

- [X] T057 [P] Test: build_parser has exactly 4 subcommands (no version/tui/serve/clean) in tests/cli/test_parser.py::test_build_parser_has_4_subcommands
- [X] T058 [P] Test: build_parser does not include extra subcommands in tests/cli/test_parser.py::test_build_parser_no_extra_subcommands
- [X] T059 [P] Test: ns_to_cli_args() converts Namespace to dict in tests/cli/test_parser.py::test_ns_to_cli_args_returns_dict
- [X] T060 [P] Test: unknown CLI flag returns exit code 2 (argparse error) in tests/cli/test_parser.py::test_unknown_flag_returns_exit_code_2
- [X] T060a [P] Test: argparse rejects negative --max-turns with exit code 2 in tests/cli/test_parser.py::test_parse_run_negative_max_turns
- [X] T060b [P] Test: argparse accepts --checks as comma-separated list in tests/cli/test_parser.py::test_parse_doctor_checks_comma_separated
- [X] T061 Implement ns_to_cli_args() in `langagent/cli/parser.py`: accept argparse.Namespace, call vars(ns), return dict[str, Any] compatible with RuntimeConfig.cli_args

---

## Phase 8: CLI Runner - Remaining Tests and Refinements

**Purpose**: Complete test coverage for cli_runner module

- [X] T062 [P] Test: dispatch returns exit code 0 on success in tests/cli/test_runner.py::test_dispatch_returns_exit_code_0_on_success
- [X] T063 [P] Test: dispatch propagates F06 AgentDirNotFoundError → exit code 66 in tests/cli/test_runner.py::test_dispatch_propagates_agent_dir_not_found_error
- [X] T064 [P] Test: dispatch handles KeyboardInterrupt → exit code 130 in tests/cli/test_runner.py::test_dispatch_handles_keyboard_interrupt
- [X] T065 [P] Test: main() calls parse_argv and dispatch in correct order in tests/cli/test_runner.py::test_main_entry_calls_dispatch
- [X] T065a [P] Test: dispatch returns exit code 130 immediately on KeyboardInterrupt in tests/cli/test_runner.py::test_dispatch_keyboard_interrupt_immediate
- [X] T065b [P] Test: dispatch init writes exactly 8 files (4 files + 4 dirs) in tests/cli/test_runner.py::test_dispatch_init_file_count
- [X] T066 Refactor dispatch() in `langagent/cli/runner.py`: extract common error handling patterns (AgentDirNotFoundError, ConfigInvalidError, KeyboardInterrupt) into helper functions to reduce duplication across 4 subcommand branches

---

## Phase 9: CLI Output Formatter - Core Tests and Implementation

**Purpose**: Complete test coverage for cli_output_formatter module

- [X] T067 [P] Test: format_eval_report() with report_format='json' outputs valid JSON in tests/cli/test_output_formatter.py::test_format_eval_report_json
- [X] T068 [P] Test: format_eval_report() with report_format='table' outputs ASCII table in tests/cli/test_output_formatter.py::test_format_eval_report_table
- [X] T069 [P] Test: format_doctor_report() outputs check status and overall conclusion in tests/cli/test_output_formatter.py::test_format_doctor_report
- [X] T070 [P] Test: format_chat_message() handles tool_calls field in tests/cli/test_output_formatter.py::test_format_chat_message_handles_tool_calls
- [X] T071 [P] Test: format_chat_message() handles empty content gracefully in tests/cli/test_output_formatter.py::test_format_chat_message_handles_empty_content
- [X] T072 [P] Test: format_chat_message() returns [assistant] line for AI messages in tests/cli/test_output_formatter.py::test_format_chat_message_returns_assistant_line
- [X] T073 Implement format_chat_message() tool_calls handling in `langagent/cli/output_formatter.py`: if message_dict contains tool_calls field, format as "[assistant] (tool_call: <name>(<args>))"

---

## Phase 10: CLI Output Formatter - ANSI Color and TTY Detection

**Purpose**: Implement ANSI color support with graceful TTY degradation (FR-CLI-028)

- [X] T074 [P] Test: ANSI color disabled when stdout not a TTY in tests/cli/test_output_formatter.py::test_format_disables_color_when_no_tty — 验证场景: (1) Mock sys.stdout.isatty()返回False; (2) 使用管道场景 `python -m langagent doctor | cat` 确保输出无ANSI codes
- [X] T075 [P] Test: ANSI color enabled when stdout is a TTY in tests/cli/test_output_formatter.py::test_format_enables_color_when_tty
- [X] T076 Implement TTY detection helper in `langagent/cli/output_formatter.py`: `def is_tty() -> bool` using `os.isatty(sys.stdout.fileno())`
- [X] T077 Implement ANSI color wrapper in `langagent/cli/output_formatter.py`: `def colorize(text: str, color: str) -> str` that returns raw ANSI codes when TTY, plain text when not (colors: red, green, yellow, blue, bold, reset)
- [X] T078 Apply colorize() to format_doctor_report_stdout(): green for ok, red for error, yellow for warn
- [X] T079 Apply colorize() to format_eval_report_stdout(): green for pass, red for fail

---

## Phase 11: CLI Output Formatter - Security and Formatting

**Purpose**: Implement payload truncation and sensitive field sanitization (FR-CLI-029, FR-CLI-030)

- [X] T080 [P] Test: payload >1KB truncated to exactly 203 chars (200 + "...") in tests/cli/test_output_formatter.py::test_format_truncates_long_payload — 断言: assert len(truncated_output) == 203 and truncated_output.endswith('...'); 输入: 1025字节payload; 输出: 前200字符+"..."
- [X] T081 [P] Test: sensitive fields replaced with "***" in tests/cli/test_output_formatter.py::test_format_never_logs_secrets — 覆盖全部6种敏感字段名: api_key, token, password, secret, api-key, auth; 同时测试下划线和中划线变体(如API_KEY, api-key)
- [X] T082 [P] Test: eval report stdout does not print raw token values in tests/cli/test_output_formatter.py::test_format_eval_report_stdout_does_not_print_secrets
- [X] T083 Implement sanitize_sensitive_fields() in `langagent/cli/output_formatter.py`: accept dict, recursively search for keys matching (api_key, token, password, secret, api-key, auth), replace values with "***", return sanitized dict
- [X] T084 Implement truncate_payload() in `langagent/cli/output_formatter.py`: accept string, if len > 1024 return first 200 chars + "..." else return unchanged
- [X] T085 Apply sanitize_sensitive_fields() to format_doctor_report() before formatting RuntimeConfigSnapshot
- [X] T086 Apply truncate_payload() to format_eval_report() when formatting per-task details

---

## Phase 12: End-to-End Integration Tests

**Purpose**: Validate all 4 subcommands work end-to-end with subprocess isolation

- [X] T087 [P] Test: end-to-end `langagent --help` displays usage in tests/cli/test_cli_end_to_end.py::test_cli_help
- [X] T088 [P] Test: end-to-end unknown subcommand returns exit code 2 in tests/cli/test_cli_end_to_end.py::test_cli_unknown_subcommand
- [X] T089 [P] Test: end-to-end `langagent run` stdout does not contain la.* tags in tests/cli/test_cli_end_to_end.py::test_cli_run_stdout_does_not_contain_la_tags

---

## Phase 13: CLI Layer Integration Verification

**Purpose**: Verify CLI layer does NOT violate architecture constraints (FR-CLI-021, FR-CLI-023)

- [X] T091 [P] Test: static check cli_runner.py does not import primitives.chat_model_factory in tests/cli/test_runner.py::test_cli_does_not_import_primitives
- [X] T092 [P] Test: static check cli_output_formatter.py does not import cross_cutting.logger in tests/cli/test_output_formatter.py::test_dispatch_cli_does_not_import_logger
- [X] T093 Add static import verification script `tests/cli/verify_cli_constraints.py`: use ast.parse to scan langagent/cli/*.py, assert no imports from langagent.primitives.{chat_model_factory,checkpoint_adapter}, assert no imports from langagent.cross_cutting.logger
- [X] T094 Run static verification script in CI: add `pytest tests/cli/verify_cli_constraints.py` to test suite

---

## Phase 14: Polish & Cross-Cutting Concerns

**Purpose**: Final refinements affecting multiple user stories

- [X] T095 [P] Add help text refinements in `langagent/cli/parser.py`: ensure all argparse help strings are clear, concise, mention exit codes where relevant
- [X] T096 Code review pass: ensure all 3 CLI modules follow PEP 8, mypy --strict passes, no unused imports
- [X] T097 Performance baseline measurement: (1) `time python -m langagent init testdemo` — record actual time, target <2s (SC-001); (2) `time python -m langagent doctor testdemo` — record actual time, target <10s (SC-004); (3) `time python -m langagent --help` — record actual time, target <100ms (SC-010); (4) `pyinstaller langagent/__main__.py --onefile && ls -lh dist/` — record binary size, target <150MB (SC-009). This task only measures baseline; does NOT include optimization implementation
- [X] T097a Performance optimization for exceeding targets: If any metric from T097 exceeds target (e.g., init >2s, doctor >10s, help >100ms), implement targeted optimizations (lazy import, template caching, argparse optimization). Document optimization applied and re-measure. Only execute if T097 identifies exceeding metrics
- [X] T098 Documentation: update top-level README.md with CLI usage examples for all 4 subcommands
- [X] T099 Run full test suite: `pytest tests/cli/ -v --cov=langagent/cli --cov-report=term-missing`, verify 45 tests pass, verify 100% coverage on cli_runner.py, cli_parser.py, cli_output_formatter.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational - No dependencies on other stories ✅ MVP
  - User Story 2 (P1): Can start after Foundational - No dependencies on other stories ✅ MVP
  - User Story 3 (P2): Can start after Foundational - Depends on F11 eval_runner (external dependency)
  - User Story 4 (P2): Can start after Foundational - Depends on F09 run_doctor_checks + F08 build_doctor_probes (external dependencies)
- **Parser Tests (Phase 7)**: Can proceed in parallel with later user stories
- **Runner Tests (Phase 8)**: Can proceed in parallel with later user stories
- **Formatter Core (Phase 9)**: Can proceed in parallel with user stories
- **Formatter ANSI (Phase 10)**: Depends on Phase 9 (formatter core functions implemented)
- **Formatter Security (Phase 11)**: Depends on Phase 9 (formatter core functions implemented)
- **E2E Tests (Phase 12)**: Depends on all user stories (Phase 3-6) complete
- **Integration Verification (Phase 13)**: Can run at any time (static analysis)
- **Polish (Phase 14)**: Depends on all previous phases complete

### User Story Dependencies

- **User Story 1 (P1 - Init)**: Independent ✅ Highest priority, can deliver as standalone MVP
- **User Story 2 (P1 - Run)**: Independent ✅ Highest priority, can deliver as standalone MVP
- **User Story 3 (P2 - Eval)**: Depends on F11 eval_runner.run() interface (external dependency from F11 feature)
- **User Story 4 (P2 - Doctor)**: Depends on F09 run_doctor_checks() + F08 build_doctor_probes() (external dependencies)

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Red-Green-Refactor per Constitution Article VIII)
- Parser schema before dispatch implementation
- Dispatch orchestration before output formatting
- Error handling after happy path implementation
- Story complete before moving to next priority

### Parallel Opportunities

- **Setup (Phase 1)**: Tasks T001-T004 can all run in parallel (different directories)
- **Foundational (Phase 2)**: Tasks T005-T009 can run in parallel if carefully coordinated (different files)
- **Once Foundational completes**: User Stories 1 & 2 can start in parallel (independent P1 stories)
- **User Story 1 tests**: T010-T014 can run in parallel (different test files)
- **User Story 2 tests**: T021-T026 can run in parallel (different test files)
- **User Story 3 tests**: T035-T039 can run in parallel (different test files)
- **User Story 4 tests**: T047-T051 can run in parallel (different test files)
- **Phase 7-11**: Test phases can proceed in parallel with implementation phases
- **Phase 13**: Static verification can run at any time

---

## Parallel Example: User Story 1 (Init MVP)

```bash
# Launch all tests for User Story 1 together (Red phase):
Task T010: "Test: argparse init subcommand accepts name positional arg"
Task T011: "Test: argparse init rejects invalid name with exit code 2"
Task T012: "Test: dispatch init calls dir_loader.write_template() once"
Task T013: "Test: init returns exit code 67 when directory exists"
Task T014: "Test: end-to-end langagent init demo creates directory"

# After tests fail (Red), implement in order (Green phase):
Task T015: "Implement build_parser() init subparser"
Task T016: "Implement dispatch() init branch"
Task T017: "Implement parse_argv()"
Task T018: "Implement main()"
Task T019: "Add error handling for NameAlreadyExistsError"
Task T020: "Add error handling for TemplateLoadFailedError"

# Refactor phase: Extract common patterns, improve code quality
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only) 🎯

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T009) ⚠️ CRITICAL - blocks all stories
3. Complete Phase 3: User Story 1 - Init (T010-T020) ✅ First deliverable
4. **STOP and VALIDATE**: Run `python -m langagent init testdemo` and verify directory creation
5. Complete Phase 4: User Story 2 - Run (T021-T034) ✅ Second deliverable
6. **STOP and VALIDATE**: Run `python -m langagent run testdemo --max-turns 1` and verify orchestration
7. Deploy/demo MVP: Users can now initialize agents and run them with CLI overrides

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (T001-T009)
2. Add User Story 1 → Test independently → Deliver `langagent init` ✅
3. Add User Story 2 → Test independently → Deliver `langagent run` ✅
4. Add User Story 3 → Test independently → Deliver `langagent eval` (depends on F11)
5. Add User Story 4 → Test independently → Deliver `langagent doctor` (depends on F09 + F08)
6. Complete remaining test coverage (Phases 7-12)
7. Complete polish phase (Phase 14)

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T009)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (Init) - T010-T020
   - **Developer B**: User Story 2 (Run) - T021-T034
   - **Developer C**: Parser tests (Phase 7) - T057-T061
   - **Developer D**: Formatter core (Phase 9) - T067-T073
3. After P1 stories complete:
   - **Developer A**: User Story 3 (Eval) - T035-T046
   - **Developer B**: User Story 4 (Doctor) - T047-T056
   - **Developer C**: Formatter ANSI (Phase 10) - T074-T079
   - **Developer D**: Formatter security (Phase 11) - T080-T086
4. **All developers**: E2E tests (Phase 12) - T087-T090
5. **All developers**: Polish (Phase 14) - T095-T100

---

## Notes

- **[P] tasks**: Different files, no dependencies - can run in parallel
- **[Story] label**: Maps task to specific user story for traceability (US1/US2/US3/US4)
- **TDD compliance**: Red-Green-Refactor workflow enforced (Constitution Article VIII)
- **External dependencies**: US3 depends on F11 eval_runner, US4 depends on F09 + F08 APIs
- **MVP scope**: User Stories 1 & 2 (Init + Run) deliver standalone value
- **Test count**: ≥45 tests across 4 test files (actual: 45 = 10 parser + 11 runner + 13 formatter + 5 dispatch stdout + 6 e2e)
- **Exit code handling**: All 13 exit codes (0/1/2/4/5/64/65/66/67/70/78/130) implemented per workflow.md
- **Architecture constraints**: CLI × primitives black list verified via static analysis (Phase 13)
- **Performance targets**: init <2s, doctor <10s, help <100ms (verified in Phase 14)
- Commit after each task or logical group (e.g., commit after US1 tests pass)
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
