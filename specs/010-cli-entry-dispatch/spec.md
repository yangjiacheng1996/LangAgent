# Feature Specification: CLI Entry and Subcommand Dispatch

**Feature Branch**: `010-cli-entry-dispatch`

**Created**: 2026-09-20

**Status**: Draft

**Input**: User description: "F10 — CLI 入口与子命令分发（init / run / eval / doctor）"

**Constitutional Alignment**: This specification aligns with Constitution Article XV (Top-Level Design Primacy) by referencing the three mandatory artifacts in `harness/top_level_design/`:
- `workflow.md` — Defines the 4 core CLI subcommands, their inputs/outputs, failure modes, exit codes, and log tags
- `architecture_modules.md` — Defines the 3 CLI layer modules (`cli_runner`, `cli_parser`, `cli_output_formatter`) and their dependency constraints
- `module_schemas.md` — Defines `CliArgs`, `DoctorReport`, `EvalReport`, and other schemas consumed by CLI modules

This feature aligns with:
- **Article I** (Project Identity): F10 is the binary command entry point exposing `langagent init/run/eval/doctor`
- **Article III** (LangSmith Removal): CLI must not import langsmith or read LANGSMITH_* environment variables
- **Article XI** (Packaging): F10's `langagent/__main__.py` is the PyInstaller entry point
- **Article XIII** (Prohibitions): CLI × primitives black list enforced—F10 must not directly import `chat_model_factory` or `checkpoint_adapter`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Initialize New Agent (Priority: P1)

A developer wants to quickly bootstrap a new LangAgent project with the correct directory structure and template files, following the Agent Directory Contract (Constitution Article V).

**Why this priority**: This is the first command any user will run. Without a working init command, users cannot create agents at all. This is the gateway to all other functionality.

**Independent Test**: Can be fully tested by running `langagent init myagent` and verifying the created directory structure matches the mandatory layout (instructions.md, skills/, tools/, middleware/, evals/, agent.py, pyproject.toml) without needing any other LangAgent functionality.

**Acceptance Scenarios**:

1. **Given** user is in an empty directory, **When** user runs `langagent init myagent`, **Then** a directory `myagent/` is created with all mandatory files (instructions.md, agent.py, pyproject.toml, .env.example) and subdirectories (skills/, tools/, middleware/, evals/)
2. **Given** user runs `langagent init myagent`, **When** the command completes successfully, **Then** terminal displays a creation summary showing all created files and suggests next steps
3. **Given** a directory named `myagent` already exists in cwd, **When** user runs `langagent init myagent`, **Then** command fails with exit code 67 and error message "Directory 'myagent' already exists"
4. **Given** user runs `langagent init 123invalid`, **When** the name violates naming constraints (must start with letter), **Then** command fails with exit code 2 and error message explaining valid naming format

---

### User Story 2 - Run Agent with Configuration Override (Priority: P1)

A developer wants to test their agent against different model providers (local vLLM vs OpenAI vs Anthropic) without editing the .env file, using CLI flags to override configuration.

**Why this priority**: Running agents is the core use case. The ability to override configuration via CLI enables rapid testing across different models and checkpointers without file editing. This directly supports Constitution Article IV (Model Abstraction Layer) requirement that both networked models and local OpenAI-compatible endpoints must be equally supported.

**Independent Test**: Can be fully tested by creating a minimal agent directory, running `langagent run myagent --model gpt-4o --model-provider openai --max-turns 3`, and verifying the model is called with correct parameters and the agent completes within 3 turns.

**Acceptance Scenarios**:

1. **Given** an agent directory exists with `.env` specifying `MODEL_NAME=qwen-3.8-27b`, **When** user runs `langagent run myagent --model gpt-4o --model-provider openai`, **Then** the agent uses gpt-4o instead of qwen-3.8-27b (CLI args override .env)
2. **Given** user runs `langagent run myagent --max-turns 5`, **When** the agent loop executes, **Then** the loop terminates after at most 5 turns regardless of completion state
3. **Given** user runs `langagent run myagent`, **When** the agent executes and model responds, **Then** stdout displays conversation messages in format `[assistant] <content>` and stderr displays structured logs with `la.*` tags
4. **Given** user runs `langagent run /nonexistent/path`, **When** the path doesn't exist, **Then** command fails with exit code 66 (EX_NOINPUT) and error message "Agent directory not found: /nonexistent/path"

---

### User Story 3 - Evaluate Agent Quality (Priority: P2)

A developer has created eval tasks in the `evals/` directory and wants to run them to measure agent performance (pass rate, latency, token usage) before deploying changes.

**Why this priority**: Evaluation is critical for maintaining agent quality but comes after basic run functionality. Developers need confidence their agents work correctly before caring about quality metrics. This supports Constitution Article IX (Quality Diagnostics) evaluation capability.

**Independent Test**: Can be fully tested by creating an agent with 3 eval YAML files (2 expected to pass, 1 expected to fail), running `langagent eval myagent`, and verifying the report shows 66% pass rate with detailed per-task results.

**Acceptance Scenarios**:

1. **Given** agent directory contains 5 eval tasks in `evals/*.yaml`, **When** user runs `langagent eval myagent`, **Then** all 5 tasks execute sequentially and terminal displays pass/fail status, P50 latency, and token usage summary
2. **Given** user runs `langagent eval myagent --task user_greeting`, **When** `--task` filter is specified, **Then** only the task with task_id=user_greeting executes (other 4 tasks are skipped)
3. **Given** user runs `langagent eval myagent --grader-only llm_judge`, **When** eval tasks use different graders (exact_match, contains, llm_judge), **Then** only tasks using llm_judge grader execute
4. **Given** agent directory has no `evals/` directory, **When** user runs `langagent eval myagent`, **Then** command fails with exit code 66 and error message "evals/ directory not found"
5. **Given** all eval tasks pass, **When** `langagent eval` completes, **Then** exit code is 0 and report is written to `~/.local/share/langagent/reports/<agent>-<timestamp>.json`

---

### User Story 4 - Diagnose Agent Configuration Issues (Priority: P2)

A developer encounters errors when running their agent and wants to diagnose whether the problem is model connectivity, checkpointer configuration, missing skills, or invalid instructions.

**Why this priority**: Doctor functionality is a troubleshooting tool that becomes valuable after users have attempted to run agents and encountered problems. It's preventive maintenance rather than core functionality. This supports Constitution Article IX (Quality Diagnostics) monitoring capability.

**Independent Test**: Can be fully tested by creating an agent with intentional misconfigurations (invalid MODEL_BASE_URL, missing skills/ directory, malformed instructions.md), running `langagent doctor myagent`, and verifying the report identifies all 3 issues with actionable error messages.

**Acceptance Scenarios**:

1. **Given** agent directory has all required files and valid configuration, **When** user runs `langagent doctor myagent`, **Then** terminal displays 4 check results (model: ok, checkpointer: ok, skills: ok, instructions: ok) with overall status "ok" and exit code 0
2. **Given** `.env` specifies unreachable MODEL_BASE_URL, **When** `langagent doctor` runs model probe, **Then** check result shows "model: error - Cannot connect to http://invalid:8000" with exit code 1
3. **Given** user runs `langagent doctor myagent --checks model,checkpointer`, **When** `--checks` filter is specified, **Then** only model and checkpointer checks execute (skills and instructions checks are skipped)
4. **Given** agent directory is missing `instructions.md`, **When** `langagent doctor` runs layout validation, **Then** check result shows "instructions: error - instructions.md not found" with exit code 1
5. **Given** doctor finds warnings but no errors (e.g., large instructions.md file), **When** all critical checks pass, **Then** exit code is 0 but report includes warnings section

---

### Edge Cases

- **Concurrent execution**: What happens when user runs multiple `langagent run` commands simultaneously on the same agent directory with checkpointer=sqlite? System must handle file locking gracefully or fail with clear error message.
- **Ctrl-C interrupt**: What happens when user presses Ctrl-C during `langagent run` or `langagent eval`? System must return exit code 130, close checkpointer cleanly, flush audit logs, and not corrupt state.
- **Invalid CLI arguments**: What happens when user provides contradictory flags like `--model gpt-4o --model openai-legacy-model`? System must detect conflict during argparse validation and fail with exit code 2 before any runtime stages execute.
- **Agent directory with spaces**: What happens when agent directory path contains spaces like `/home/user/my agents/demo`? System must handle paths correctly with proper quoting.
- **Empty evals directory**: What happens when `evals/` directory exists but contains no YAML files? System must report "0 tasks found" and exit with code 0 (not an error condition).
- **Partial eval failure**: What happens when 3 out of 10 eval tasks fail? System must report individual task failures, aggregate results, and return worst-case exit code from failed tasks per F09 worst_of() arbitration rules.
- **Doctor check without model**: What happens when `.env` has no MODEL_BASE_URL and doctor runs model probe? System must skip model check with status "skipped" (not "error") and continue with remaining checks, overall exit code remains 0 if other checks pass.
- **Template corruption**: What happens when internal template files (embedded in binary or in ~/.local/share/langagent/templates/) are corrupted? System must detect corruption during `langagent init` and fail with exit code 70 (EX_SOFTWARE) with actionable error message.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-CLI-001**: System MUST expose exactly 4 CLI subcommands: `init`, `run`, `eval`, `doctor` (no `version`, `tui`, `serve`, `clean` - Constitution Article XI §2)
- **FR-CLI-002**: System MUST parse `langagent init <name>` where `<name>` matches regex `^[a-zA-Z][a-zA-Z0-9_-]*$` and reject invalid names with exit code 2
- **FR-CLI-003**: System MUST create agent directory structure matching Constitution Article V mandatory layout: instructions.md, agent.py, pyproject.toml, .env.example, skills/, tools/, middleware/, evals/
- **FR-CLI-004**: System MUST support optional `[agent-dir]` positional argument for run/eval/doctor subcommands, defaulting to current working directory when omitted
- **FR-CLI-005**: System MUST accept CLI flag overrides for model configuration: `--model`, `--model-provider`, `--model-base-url`, `--checkpointer`, `--middleware`, `--max-turns`, `--thread-id`
- **FR-CLI-006**: System MUST implement configuration priority chain: CLI args > environment variables > agent directory .env > built-in defaults (Constitution Article XII §1)
- **FR-CLI-007**: System MUST separate stdout (user-facing conversation) from stderr (structured logs with `la.*` tags) per workflow.md run command semantics
- **FR-CLI-008**: System MUST format chat messages to stdout as `[assistant] <content>` during `langagent run` execution
- **FR-CLI-009**: System MUST format EvalReport to stdout with pass rate, P50 latency, token usage after `langagent eval` execution
- **FR-CLI-010**: System MUST format DoctorReport to stdout showing 4 check results (model/checkpointer/skills/instructions) with overall status
- **FR-CLI-011**: System MUST support eval filtering flags: `--grader-only {exact_match,contains,regex,llm_judge,tool_call_match}` and `--task <task_id>`
- **FR-CLI-012**: System MUST support doctor filtering flag: `--checks {model,checkpointer,skills,instructions}` (comma-separated, defaults to all 4)
- **FR-CLI-013**: System MUST support eval output format flag: `--report-format {json,yaml,table}` (defaults to table)
- **FR-CLI-014**: System MUST return exit code 0 for success, non-zero for failures per workflow.md exit code table (13 distinct codes: 0/1/2/4/5/64/65/66/67/70/78/130)
- **FR-CLI-015**: System MUST return exit code 67 when `langagent init <name>` target directory already exists (not 66 which is EX_NOINPUT)
- **FR-CLI-016**: System MUST return exit code 130 when user presses Ctrl-C (SIGINT) during run/eval/doctor execution
- **FR-CLI-017**: System MUST orchestrate 6 runtime stages for `langagent run`: dir_load → config_resolve → model_adapt → graph_compose → main_loop → exit_cleanup
- **FR-CLI-018**: System MUST orchestrate 3 runtime stages for `langagent eval`: dir_load → config_resolve → [eval_runner.run] → exit_cleanup
- **FR-CLI-019**: System MUST orchestrate 3 runtime stages for `langagent doctor`: dir_load → config_resolve → [run_doctor_checks] → exit_cleanup
- **FR-CLI-020**: System MUST call exit_handler.cleanup() with `init_only=True` for `langagent init` subcommand per workflow.md init lifecycle
- **FR-CLI-021**: System MUST NOT directly import `langagent.primitives.chat_model_factory` or `langagent.primitives.checkpoint_adapter` from CLI layer (Constitution Article XIII + architecture_modules.md CLI × primitives black list)
- **FR-CLI-022**: System MUST obtain model/checkpoint probe functions via `runtime_main_loop_dispatcher.build_doctor_probes()` factory for doctor orchestration
- **FR-CLI-023**: System MUST NOT directly call `cross_cutting_logger.emit()` from CLI layer—all `la.*` tags emitted by runtime/protocol/cross_cutting layers per architecture_modules.md constraints
- **FR-CLI-024**: System MUST accept `eval_runner.run()` return type `EvalRunResult(eval_report, final_state, exit_code)` and pass `eval_report` to `exit_handler.cleanup()`
- **FR-CLI-025**: System MUST construct args dict for eval_runner with schema `{'cli_args': vars(ns), 'grader_only': str|None, 'task': str|None}` to avoid F11 importing F10 CliArgs type
- **FR-CLI-026**: System MUST call `config_resolver.resolve()` once in eval dispatch and inject result via keyword-only `config` parameter to `eval_runner.run(agent_dir, *, config, args)`
- **FR-CLI-027**: System MUST aggregate exit codes via F09 `worst_of()` arbitration for eval/doctor subcommands when multiple tasks/checks fail
- **FR-CLI-028**: System MUST disable ANSI color codes in output when stdout is not a TTY (e.g., piped to file or CI environment)
- **FR-CLI-029**: System MUST truncate long payload fields (>1KB) to 200 characters + "..." in formatted output to prevent terminal flooding
- **FR-CLI-030**: System MUST sanitize sensitive fields (api_key, token, password) in formatted output—replace with "***" placeholder

### Key Entities

- **CliArgs**: Frozen Pydantic model containing parsed CLI arguments—subcommand (str), agent_dir (str), cli_args (dict), plus subcommand-specific fields (grader_only: str|None, task: str|None, checks: list[str]|None, report_format: str, max_turns: int, thread_id: str|None)
- **RuntimeConfig**: Configuration object built from CLI args + env vars + .env file per priority chain—contains model settings, checkpointer type, middleware list, guardrail policy
- **LoadedAgent**: Frozen dataclass with 5 fields (instructions, skill_ids, tool_specs, middleware_specs, channel_specs) loaded from agent directory—does NOT contain compiled_graph per review.md v1.1.0 P0-2
- **CompiledStateGraph**: LangGraph compiled graph object held by F10 dispatch independently from LoadedAgent—produced by `state_graph_builder.build()` in run dispatch
- **EvalReport**: Report object containing task results, pass rate, latency metrics, token usage—produced by `eval_runner.run()` and consumed by `cli_output_formatter.format_eval_report_stdout()`
- **DoctorReport**: Report object containing 4 check results (model/checkpointer/skills/instructions), overall status (ok/warn/error), runtime config snapshot—produced by `exit_handler.run_doctor_checks()` and consumed by `cli_output_formatter.format_doctor_report_stdout()`

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create a new agent with `langagent init myagent` and receive a working directory structure in under 2 seconds
- **SC-002**: Users can run an agent with `langagent run` and see model responses in stdout immediately as they are generated (no buffering delay)
- **SC-003**: Users can evaluate 10 tasks with `langagent eval` and receive a formatted report in under 60 seconds (assuming 5s average task duration, measuring LangAgent local processing time only—excludes model API network latency which is uncontrollable)
- **SC-004**: Users can diagnose configuration issues with `langagent doctor` and receive actionable error messages for all 4 check types within 10 seconds
- **SC-005**: System handles Ctrl-C interrupt during any subcommand within 1 second and exits cleanly with code 130 without corrupting state
- **SC-006**: CLI parsing rejects invalid arguments (unknown flags, type mismatches) and returns exit code 2 with helpful error message before executing any runtime stage
- **SC-007**: stdout contains ONLY user-facing content (chat messages, reports) with zero `la.*` log tags—all logs appear exclusively on stderr
- **SC-008**: Formatted output (eval/doctor reports) renders correctly in 80-column terminal without horizontal scrolling for standard report sizes (defined as ≤20 eval tasks or ≤10 doctor check items)
- **SC-009**: CLI binary size remains under 150MB when packaged with PyInstaller including all dependencies (LangChain, LangGraph, pydantic, click)
- **SC-010**: Help text for all subcommands (`langagent --help`, `langagent run --help`, etc.) displays complete parameter documentation in under 100ms

## Assumptions

- **Agent directory portability**: Users can move agent directories between machines and expect them to work after updating .env file with local credentials (Constitution Article V portable directory constraint)
- **Python environment**: Users running from source have Python 3.11+ installed; users running packaged binary do not need Python installed (Constitution Article XI packaging requirement)
- **Model availability**: Local vLLM Qwen-3.8-27B is the default and baseline model; all functionality must work with this model first, then extend to networked models (Constitution Article IV §4)
- **Concurrent execution scope**: V1 does not support concurrent `langagent run` on same agent directory with shared checkpointer—will be addressed in v2 with proper locking
- **Terminal capabilities**: CLI output assumes VT100-compatible terminal with ANSI color support; gracefully degrades to plain text when piped or in CI (SC-006 verification)
- **Eval task execution**: Eval tasks execute sequentially in single process; parallel execution is out of scope for v1 (simplifies state management and error handling)
- **Doctor probe timeout**: Model probe timeout is 5 seconds; checkpointer probe timeout is 2 seconds—hardcoded in F09, not configurable via CLI in v1
- **Report persistence location**: Reports are written to `~/.local/share/langagent/reports/` on Linux/macOS and `%LOCALAPPDATA%\langagent\reports\` on Windows—not configurable in v1
- **CLI subcommand stability**: The 4 core subcommands (init/run/eval/doctor) are stable; no additional subcommands (version/tui/serve) will be added in v1 per Constitution Article XI §2 + workflow.md Q5 clarification
