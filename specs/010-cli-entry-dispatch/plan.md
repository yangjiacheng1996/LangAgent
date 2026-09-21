# Implementation Plan: CLI Entry and Subcommand Dispatch

**Branch**: `010-cli-entry-dispatch` | **Date**: 2026-09-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/010-cli-entry-dispatch/spec.md`

## Summary

Feature F10 implements the CLI layer for LangAgent, providing the binary command entry point that orchestrates 4 core subcommands (`init`, `run`, `eval`, `doctor`). This feature acts as the user-facing interface that dispatches to the 6 runtime stages (dir_load → config_resolve → model_adapt → graph_compose → main_loop → exit_cleanup) and formats output for human consumption.

**Primary Requirements**: 
- Parse 4 CLI subcommands with argparse (FR-CLI-001, FR-CLI-002)
- Orchestrate 6 runtime stages for `run`, 3 stages for `eval`/`doctor` (FR-CLI-017-019)
- Format stdout (chat messages, reports) separately from stderr (structured logs) (FR-CLI-007)
- Return 13 distinct exit codes per workflow.md mapping (FR-CLI-014-016)
- Enforce CLI × primitives black list—no direct imports of chat_model_factory or checkpoint_adapter (FR-CLI-021)

**Technical Approach**: 
- 3 CLI modules: `cli_runner` (dispatch orchestration), `cli_parser` (argparse schema), `cli_output_formatter` (report formatting)
- Dependency injection of probe functions for doctor via F08 `build_doctor_probes()` factory (FR-CLI-022)
- Lazy import of `eval_runner` from F11 for eval subcommand (FR-CLI-024-026)
- Configuration priority chain: CLI args > env vars > .env > defaults (FR-CLI-006)

## Technical Context

**Language/Version**: Python 3.11+ (per `pyproject.toml` requires-python field, Constitution Article II §5)

**Primary Dependencies**: 
- `argparse` (stdlib) — CLI argument parsing
- `pydantic` — CliArgs frozen model validation
- LangChain types (via `langagent.primitives.langchain_types`) — BaseMessage for chat formatting
- F06-F09 runtime modules — dir_loader, config_resolver, main_loop_dispatcher, exit_handler
- F11 eval_runner (lazy import) — eval subcommand delegation

**Storage**: 
- Filesystem (read-only for agent directories, write for reports at `~/.local/share/langagent/reports/`)
- No database—CLI is stateless orchestrator

**Testing**: pytest with ≥45 test cases (§四: 10 cli_parser + 9 cli_runner + 13 cli_output_formatter + 6 stdout formatting + 5 dispatch stdout + 6 end-to-end = 49 total; target ≥39 per feature prompt)

**Target Platform**: Linux/macOS/Windows CLI environments (VT100-compatible terminals with ANSI color support; graceful degradation to plain text when piped)

**Project Type**: CLI tool (binary command via PyInstaller)

**Performance Goals**: 
- `langagent init` completes in <2s (SC-001)
- `langagent doctor` completes in <10s (SC-004)
- Help text displays in <100ms (SC-010)
- Ctrl-C interrupt handled within 1s (SC-005)

**Constraints**: 
- CLI binary size <150MB with all dependencies (SC-009)
- Formatted output fits 80-column terminal without horizontal scrolling for standard report sizes (SC-008)
- CLI layer must not import primitives layer (architecture_modules.md CLI × primitives black list)
- CLI layer must not call cross_cutting_logger.emit() directly (FR-CLI-023)

**Scale/Scope**: 
- 4 subcommands (init/run/eval/doctor)
- 13 exit codes (0/1/2/4/5/64/65/66/67/70/78/130)
- 3 CLI modules totaling ~780 LOC (cli_runner ~280, cli_parser ~180, cli_output_formatter ~320)
- Entry point: `langagent/__main__.py` for PyInstaller

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article I (Project Identity)
- ✓ **Compliant**: F10 exposes binary command entry point `langagent` with 4 subcommands (no SDK, no importable API)
- ✓ **Compliant**: User-facing interface consists only of CLI commands and agent directory files

### Article III (LangSmith Removal)
- ✓ **Compliant**: CLI layer does not import langsmith or read LANGSMITH_* environment variables
- ✓ **Compliant**: No assumptions about LangSmith Deployment/Agent Server/Studio

### Article IV (Model Abstraction Layer)
- ✓ **Compliant**: CLI does not directly call model provider SDKs—models instantiated by F01 via primitives layer
- ✓ **Compliant**: Both networked models and local OpenAI-compatible endpoints supported via `--model` / `--model-provider` / `--model-base-url` flags

### Article V (Agent Directory Contract)
- ✓ **Compliant**: `langagent init` creates mandatory layout (instructions.md, agent.py, pyproject.toml, .env.example, skills/, tools/, middleware/, evals/)
- ✓ **Compliant**: Directory portability enforced—no absolute paths or hardcoded assumptions

### Article VIII (TDD)
- ✓ **Compliant**: ≥39 test cases specified (10 parser + 9 runner + 13 formatter + 6 stdout + 5 dispatch + 6 e2e)
- ✓ **Compliant**: Red-Green-Refactor workflow required; no implementation before failing tests

### Article XI (Packaging)
- ✓ **Compliant**: `langagent/__main__.py` is PyInstaller entry point
- ✓ **Compliant**: Only 4 core subcommands (no version/tui/serve/clean per workflow.md Q5 clarification)

### Article XII (Configuration & Observability)
- ✓ **Compliant**: Configuration priority chain implemented: CLI args > env vars > .env > defaults (FR-CLI-006)
- ✓ **Compliant**: Startup logs printed by runtime layers (F06-F09), CLI only formats output

### Article XIII (Prohibitions)
- ✓ **Compliant**: CLI × primitives black list enforced (FR-CLI-021)—no direct import of chat_model_factory or checkpoint_adapter
- ✓ **Compliant**: Probe functions obtained via F08 `build_doctor_probes()` factory (FR-CLI-022)

### Article XV (Top-Level Design Primacy)
- ✓ **Compliant**: Spec explicitly references all 3 top-level design artifacts (workflow.md, architecture_modules.md, module_schemas.md)
- ✓ **Compliant**: Module dependencies, exit codes, log tags all align with top-level design documents

**Gate Status**: ✅ **PASS** — All constitutional requirements satisfied. Proceed to Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/010-cli-entry-dispatch/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── cli-args.schema.json       # CliArgs Pydantic schema
│   ├── exit-codes.md              # 13 exit codes mapping table
│   └── subcommand-signatures.md  # 4 subcommand argparse schemas
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
langagent/
├── __main__.py                      # PyInstaller entry point (NEW)
├── cli/                             # CLI layer (NEW)
│   ├── __init__.py
│   ├── runner.py                    # cli_runner module: parse_argv, dispatch, main
│   ├── parser.py                    # cli_parser module: build_parser, ns_to_cli_args
│   └── output_formatter.py          # cli_output_formatter module: format_* functions
├── runtime/                         # Runtime layer (EXISTS—F06-F09)
│   ├── dir_loader.py                # F06: load(), write_template()
│   ├── config_resolver.py           # F07: resolve()
│   ├── main_loop_dispatcher.py      # F08: dispatch(), run_until_done(), build_doctor_probes()
│   └── exit_handler.py              # F09: cleanup(), run_doctor_checks()
├── primitives/                      # Primitives layer (EXISTS—F01)
│   ├── chat_model_factory.py        # F01: create()
│   ├── checkpoint_adapter.py        # F01: create()
│   └── state_graph_builder.py       # F01: build()
└── eval/                            # Eval subsystem (EXISTS—F11)
    └── runner.py                    # F11: run() returns EvalRunResult

tests/
├── cli/                             # CLI tests (NEW)
│   ├── __init__.py
│   ├── test_parser.py               # 10 tests: argparse schema, validation
│   ├── test_runner.py               # 9 tests: dispatch orchestration, exit codes
│   ├── test_output_formatter.py     # 13 tests: report formatting, ANSI colors
│   └── test_cli_end_to_end.py       # 6 tests: subprocess integration
└── fixtures/                        # Test fixtures (SHARED)
    └── minimal_agent/               # Minimal agent directory for e2e tests
```

**Structure Decision**: Single project layout (Option 1). CLI layer is a thin orchestration layer that dispatches to runtime modules (F06-F09) and primitives modules (F01) via dependency injection. The 3 CLI modules (`cli_runner`, `cli_parser`, `cli_output_formatter`) are organized under `langagent/cli/` to enforce architectural layer separation per architecture_modules.md.

## Complexity Tracking

> **No violations detected** — Constitution Check passed all gates without exceptions.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

---

## Phase 0: Outline & Research

### Research Questions

Based on Technical Context analysis, the following areas require research to resolve NEEDS CLARIFICATION items:

1. **Argparse schema design for 4 subcommands**: How to structure nested subparsers with shared flags (agent_dir) vs subcommand-specific flags (--grader-only, --checks)?
2. **Exit code aggregation via F09 worst_of()**: What is the exact arbitration algorithm F09 uses to aggregate multiple failure codes (e.g., 3 eval tasks fail with codes 1/70/78)?
3. **Probe function injection for doctor**: How does F08 `build_doctor_probes()` API work? What is the signature of probe callables passed to F09 `run_doctor_checks()`?
4. **F11 eval_runner interface contract**: What is the exact signature of `eval_runner.run()` and the structure of `EvalRunResult`? How does config injection work (keyword-only parameter)?
5. **ANSI color codes for terminal output**: What library/pattern should be used for cross-platform ANSI color support with graceful TTY detection?
6. **Stdout/stderr separation mechanics**: How to ensure chat messages go to stdout while `la.*` tags go to stderr without CLI layer calling logger.emit() directly?

### Research Tasks

1. **Argparse best practices for nested subcommands**:
   - Research: stdlib argparse `add_subparsers()` API for nested command structure
   - Research: Shared arguments via parent parsers vs repeated definitions
   - Decision: Choose pattern that minimizes duplication for `[agent_dir]` positional arg shared by run/eval/doctor

2. **F09 exit_handler.cleanup() and worst_of() algorithm**:
   - Research: Read F09 spec/plan for `worst_of()` arbitration rules
   - Research: Read workflow.md exit code priority table (13 codes: 130 > 78 > 70 > 67 > 66 > 65 > 64 > 5 > 4 > 2 > 1 > 0)
   - Decision: Document exact priority order for unit tests

3. **F08 build_doctor_probes() factory API**:
   - Research: Read F08 spec/plan for `build_doctor_probes()` signature
   - Research: Read F09 spec/plan for `run_doctor_checks(*, model_probe_fn=, checkpoint_probe_fn=)` signature
   - Decision: Confirm probe callable signature is `() -> tuple[bool, str]` (success flag, error message)

4. **F11 eval_runner.run() interface**:
   - Research: Read F11 spec for `run(agent_dir, *, config, args)` signature
   - Research: Read module_schemas.md for `EvalRunResult` dataclass fields (eval_report, final_state, exit_code)
   - Decision: Confirm args dict schema: `{'cli_args': vars(ns), 'grader_only': str|None, 'task': str|None}`

5. **ANSI color library selection**:
   - Research: Compare stdlib options (no external deps preferred per Constitution Article II §6)
   - Research: ANSI escape codes for common terminal operations (bold, color, reset)
   - Research: TTY detection via `os.isatty(sys.stdout.fileno())`
   - Decision: Use raw ANSI codes (no external deps) with TTY detection wrapper

6. **Stdout/stderr separation implementation**:
   - Research: Python logging best practices for dual-stream output
   - Research: How F02 cross_cutting_logger emits to stderr
   - Decision: Use `print(..., file=sys.stdout)` for user output, rely on F02-F09 to emit logs to stderr

### Consolidation Format

All findings will be documented in `research.md` with structure:

```markdown
# Research: [Topic]

## Decision
[What was chosen]

## Rationale
[Why chosen based on research findings]

## Alternatives Considered
[What else was evaluated and why rejected]

## Implementation Notes
[Technical details for Phase 1 design]
```

---

## Phase 1: Design & Contracts

**Prerequisites**: `research.md` complete with all 6 research questions resolved

### 1. Data Model (`data-model.md`)

Extract entities from feature spec and define their structure:

#### CliArgs (Pydantic frozen model)
- **Purpose**: Parsed CLI arguments from argparse.Namespace
- **Fields**:
  - `subcommand: str` — One of 'init', 'run', 'eval', 'doctor'
  - `agent_dir: str` — Path to agent directory (defaults to cwd)
  - `cli_args: dict[str, Any]` — Raw CLI argument dict
  - Subcommand-specific fields:
    - `name: str | None` — For init subcommand
    - `model: str | None` — For run subcommand (--model)
    - `model_provider: str | None` — For run subcommand (--model-provider)
    - `model_base_url: str | None` — For run subcommand (--model-base-url)
    - `checkpointer: str | None` — For run subcommand (--checkpointer)
    - `middleware: str | None` — For run subcommand (--middleware, comma-separated)
    - `max_turns: int` — For run subcommand (--max-turns, default 30)
    - `thread_id: str | None` — For run subcommand (--thread-id)
    - `grader_only: str | None` — For eval subcommand (--grader-only)
    - `task: str | None` — For eval subcommand (--task)
    - `report_format: str` — For eval subcommand (--report-format, default 'table')
    - `checks: list[str] | None` — For doctor subcommand (--checks, comma-separated, defaults to all 4 checks when None)
- **Validation Rules**:
  - `subcommand` must be in ['init', 'run', 'eval', 'doctor']
  - `name` (if present) must match regex `^[a-zA-Z][a-zA-Z0-9_-]*$`
  - `max_turns` must be ≥1
  - `report_format` must be in ['json', 'yaml', 'table']
  - `grader_only` (if present) must be in ['exact_match', 'contains', 'regex', 'llm_judge', 'tool_call_match']
- **State Transitions**: Immutable (frozen=True)

#### RuntimeDeps (dependency injection container)
- **Purpose**: Runtime module references passed to cli_runner.dispatch()
- **Fields**:
  - `dir_loader: ModuleType` — F06 runtime_dir_loader module
  - `config_resolver: ModuleType` — F07 runtime_config_resolver module
  - `main_loop_dispatcher: ModuleType` — F08 runtime_main_loop_dispatcher module
  - `exit_handler: ModuleType` — F09 runtime_exit_handler module
  - `eval_runner: ModuleType | None` — F11 eval.runner module (lazy import)
- **Validation Rules**: None (structural typing, not runtime-validated)
- **State Transitions**: N/A (created once per CLI invocation)

#### FormatterContext (output formatting context)
- **Purpose**: TTY detection and color preference for cli_output_formatter
- **Fields**:
  - `is_tty: bool` — Result of `os.isatty(sys.stdout.fileno())`
  - `enable_color: bool` — Derived from is_tty (False if piped)
  - `terminal_width: int` — Terminal columns (default 80)
- **Validation Rules**: `terminal_width` must be ≥40
- **State Transitions**: Immutable (computed once at CLI startup)

#### RuntimeConfigSnapshot (frozen dataclass)
- **Purpose**: Immutable snapshot of runtime configuration for doctor report persistence
- **Fields**:
  - `model_name: str` — Model identifier (e.g., "gpt-4o", "qwen-3.8-27b")
  - `model_provider: str` — Provider name (e.g., "openai", "anthropic", "openai-compatible")
  - `model_base_url: str | None` — Base URL for OpenAI-compatible endpoints
  - `checkpointer_type: str` — One of "memory", "sqlite", "postgres"
  - `middleware_list: list[str]` — Ordered list of enabled middleware IDs
  - `max_turns: int` — Main loop turn limit
- **Validation Rules**: None (snapshot is read-only)
- **State Transitions**: Created once via `RuntimeConfigSnapshot.from_runtime_config(config)` in doctor dispatch
- **Usage**: Embedded in DoctorReport for audit trail and troubleshooting context

### 2. Interface Contracts (`contracts/`)

#### Contract 1: CLI Argument Schema (`cli-args.schema.json`)

**Purpose**: Define Pydantic schema for CliArgs frozen model

**Format**: JSON Schema (Pydantic-generated)

**Content**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CliArgs",
  "type": "object",
  "properties": {
    "subcommand": {
      "type": "string",
      "enum": ["init", "run", "eval", "doctor"]
    },
    "agent_dir": {
      "type": "string",
      "description": "Path to agent directory (absolute or relative)"
    },
    "cli_args": {
      "type": "object",
      "description": "Raw CLI argument dict from argparse"
    },
    "name": {
      "type": "string",
      "pattern": "^[a-zA-Z][a-zA-Z0-9_-]*$",
      "description": "Agent name for init subcommand"
    },
    "model": {"type": "string"},
    "model_provider": {"type": "string"},
    "model_base_url": {"type": "string"},
    "checkpointer": {
      "type": "string",
      "enum": ["memory", "sqlite", "postgres"]
    },
    "middleware": {"type": "string"},
    "max_turns": {"type": "integer", "minimum": 1},
    "thread_id": {"type": "string"},
    "grader_only": {
      "type": "string",
      "enum": ["exact_match", "contains", "regex", "llm_judge", "tool_call_match"]
    },
    "task": {"type": "string"},
    "report_format": {
      "type": "string",
      "enum": ["json", "yaml", "table"],
      "default": "table"
    },
    "checks": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": ["model", "checkpointer", "skills", "instructions"]
      }
    }
  },
  "required": ["subcommand", "agent_dir", "cli_args"]
}
```

#### Contract 2: Exit Codes Mapping (`exit-codes.md`)

**Purpose**: Document 13 exit codes per workflow.md and their semantic meaning

**Format**: Markdown table

**Content**:
```markdown
# Exit Codes

| Code | POSIX Name | Semantic Meaning | Typical Scenarios |
|------|------------|------------------|-------------------|
| 0    | EX_OK      | Success          | All operations completed successfully |
| 1    | (generic)  | General failure  | Tool execution error, stage capability violation, unhandled exception |
| 2    | EX_USAGE   | Usage error      | Invalid CLI arguments, unknown subcommand, argparse validation failure |
| 4    | EX_IOERR   | I/O error        | File read/write failed, report persistence failed |
| 5    | EX_CONFIG  | Config error     | Required field missing in RuntimeConfig |
| 64   | EX_USAGE   | Command-line usage error | (reserved, rarely used) |
| 65   | EX_DATAERR | Data format error | YAML parse error, malformed .env, invalid agent directory layout |
| 66   | EX_NOINPUT | Input file missing | Agent directory not found, evals/ directory missing |
| 67   | (custom)   | Name already exists | `langagent init` target directory exists (v0.5.0+) |
| 70   | EX_SOFTWARE | Internal software error | Model timeout, template load failed, eval timeout |
| 78   | EX_CONFIG  | Configuration error | Config type mismatch, auth failed, invalid model_provider |
| 130  | (SIGINT)   | Ctrl-C interrupt | User pressed Ctrl-C, graceful shutdown |

## Priority Order (for worst_of() arbitration)

When multiple failures occur (e.g., 3 eval tasks fail with different codes), F09 `worst_of()` returns the code with highest priority:

130 > 78 > 70 > 67 > 66 > 65 > 64 > 5 > 4 > 2 > 1 > 0

Example: If task A fails with code 1, task B fails with code 70, and task C succeeds with code 0, the aggregate exit code is 70.
```

#### Contract 3: Subcommand Signatures (`subcommand-signatures.md`)

**Purpose**: Document argparse schema for 4 CLI subcommands

**Format**: Markdown with code blocks

**Content**:
```markdown
# Subcommand Signatures

## langagent init <name>

### Synopsis
```
langagent init [-h] name
```

### Positional Arguments
- `name` (str, required): Agent directory name. Must match regex `^[a-zA-Z][a-zA-Z0-9_-]*$`.

### Optional Arguments
- `-h, --help`: Show help message and exit

### Exit Codes
- 0: Success (directory created)
- 2: Invalid name format
- 67: Target directory already exists
- 70: Template load failed

---

## langagent run [agent-dir]

### Synopsis
```
langagent run [-h] [--model MODEL] [--model-provider PROVIDER]
              [--model-base-url URL] [--checkpointer {memory,sqlite,postgres}]
              [--middleware ID,...] [--max-turns N] [--thread-id ID]
              [agent_dir]
```

### Positional Arguments
- `agent_dir` (str, optional): Path to agent directory. Defaults to current working directory.

### Optional Arguments
- `-h, --help`: Show help message and exit
- `--model MODEL`: Override MODEL_NAME from .env
- `--model-provider PROVIDER`: Override MODEL_PROVIDER from .env
- `--model-base-url URL`: Override MODEL_BASE_URL from .env
- `--checkpointer {memory,sqlite,postgres}`: Override LANGAGENT_CHECKPOINTER from .env
- `--middleware ID,...`: Override LANGAGENT_MIDDLEWARE from .env (comma-separated list)
- `--max-turns N`: Maximum main loop turns (default: 30, minimum: 1)
- `--thread-id ID`: Checkpointer thread identifier (default: auto-generated UUID)

### Exit Codes
- 0: Success (agent completed)
- 1: Tool execution error or general failure
- 4: I/O error
- 66: Agent directory not found
- 70: Model timeout
- 78: Config invalid
- 130: Ctrl-C interrupt

---

## langagent eval [agent-dir]

### Synopsis
```
langagent eval [-h] [--grader-only TYPE] [--task TASK_ID]
               [--report-format {json,yaml,table}] [agent_dir]
```

### Positional Arguments
- `agent_dir` (str, optional): Path to agent directory. Defaults to current working directory.

### Optional Arguments
- `-h, --help`: Show help message and exit
- `--grader-only {exact_match,contains,regex,llm_judge,tool_call_match}`: Run only tasks using specified grader
- `--task TASK_ID`: Run only task with specified task_id
- `--report-format {json,yaml,table}`: Output format (default: table)

### Exit Codes
- 0: All tasks passed
- 1: Task execution error
- 66: evals/ directory missing
- 70: Eval timeout
- 78: Grader unknown or config invalid
- 130: Ctrl-C interrupt

---

## langagent doctor [agent-dir]

### Synopsis
```
langagent doctor [-h] [--checks {model,checkpointer,skills,instructions}]
                 [agent_dir]
```

### Positional Arguments
- `agent_dir` (str, optional): Path to agent directory. Defaults to current working directory.

### Optional Arguments
- `-h, --help`: Show help message and exit
- `--checks {model,checkpointer,skills,instructions}`: Run only specified checks (comma-separated list). Defaults to all 4 checks.

### Exit Codes
- 0: All checks passed or skipped
- 1: Any check failed
- 78: Config invalid
- 130: Ctrl-C interrupt
```

### 3. Quickstart Validation Guide (`quickstart.md`)

**Purpose**: Runnable validation scenarios proving F10 works end-to-end

**Content**:
```markdown
# Quickstart: CLI Entry and Subcommand Dispatch

## Prerequisites

- Python 3.11+ installed
- LangAgent repository cloned and dependencies installed (`pip install -e .`)
- F06-F09 runtime modules implemented (dir_loader, config_resolver, main_loop_dispatcher, exit_handler)
- F01 primitives modules implemented (chat_model_factory, checkpoint_adapter, state_graph_builder)

## Validation Scenarios

### Scenario 1: Initialize New Agent

**Goal**: Verify `langagent init` creates agent directory with correct layout

**Commands**:
```bash
cd /tmp
python -m langagent init demo
ls -la demo/
```

**Expected Outcome**:
- Directory `demo/` created with files: instructions.md, agent.py, pyproject.toml, .env.example
- Subdirectories: skills/, tools/, middleware/, evals/
- Terminal displays creation summary with file list
- Exit code 0

**Verification**:
```bash
echo $?  # Should print 0
test -f demo/instructions.md && echo "✓ instructions.md exists"
test -d demo/skills && echo "✓ skills/ directory exists"
```

---

### Scenario 2: Run Agent with CLI Override

**Goal**: Verify `langagent run` orchestrates 6 runtime stages and overrides .env config

**Setup**:
```bash
cd demo
cat > .env << EOF
MODEL_PROVIDER=openai
MODEL_NAME=gpt-3.5-turbo
MODEL_BASE_URL=
OPENAI_API_KEY=sk-test-key
LANGAGENT_CHECKPOINTER=memory
EOF
```

**Commands**:
```bash
python -m langagent run --model gpt-4o --max-turns 3
```

**Expected Outcome**:
- stdout contains `[assistant] ...` messages (no `la.*` tags)
- stderr contains structured logs with `la.lifecycle.run.start`, `la.runtime.main_loop.start`, etc.
- Agent uses gpt-4o instead of gpt-3.5-turbo (CLI arg overrides .env)
- Loop terminates after at most 3 turns
- Exit code 0 (success) or 1/70/78 (expected failures if model unavailable)

**Verification**:
```bash
python -m langagent run --model gpt-4o --max-turns 3 2>stderr.log 1>stdout.log
grep '\[assistant\]' stdout.log && echo "✓ Chat messages in stdout"
grep 'la.lifecycle.run.start' stderr.log && echo "✓ Logs in stderr"
! grep 'la\.' stdout.log && echo "✓ No logs leaked to stdout"
```

---

### Scenario 3: Evaluate Agent

**Goal**: Verify `langagent eval` executes tasks and aggregates results

**Setup**:
```bash
mkdir -p demo/evals
cat > demo/evals/greeting.yaml << EOF
task_id: user_greeting
input: "Hello, what's your name?"
expected: "I am a helpful AI assistant"
grader: contains
EOF
```

**Commands**:
```bash
cd demo
python -m langagent eval
```

**Expected Outcome**:
- Terminal displays pass/fail status, P50 latency, token usage
- Report written to `~/.local/share/langagent/reports/demo-<timestamp>.json`
- Exit code 0 if task passes, 1/70/78 if task fails

**Verification**:
```bash
python -m langagent eval 2>&1 | tee eval_output.log
grep 'pass rate' eval_output.log && echo "✓ Pass rate displayed"
ls ~/.local/share/langagent/reports/demo-*.json && echo "✓ Report persisted"
```

---

### Scenario 4: Diagnose Configuration

**Goal**: Verify `langagent doctor` runs 4 checks and reports status

**Commands**:
```bash
cd demo
python -m langagent doctor
```

**Expected Outcome**:
- Terminal displays 4 check results: model (ok/error), checkpointer (ok/error), skills (ok/warn), instructions (ok/warn)
- Overall status: ok/warn/error
- Report written to `~/.local/share/langagent/reports/doctor-<timestamp>.json`
- Exit code 0 if all checks pass/warn, 1 if any check errors

**Verification**:
```bash
python -m langagent doctor 2>&1 | tee doctor_output.log
grep 'model:' doctor_output.log && echo "✓ Model check executed"
grep 'checkpointer:' doctor_output.log && echo "✓ Checkpointer check executed"
grep 'overall:' doctor_output.log && echo "✓ Overall status displayed"
```

---

### Scenario 5: Invalid Arguments

**Goal**: Verify CLI rejects invalid arguments with exit code 2

**Commands**:
```bash
python -m langagent run --unknown-flag
python -m langagent init 123invalid
python -m langagent eval --grader-only unknown_grader
```

**Expected Outcome**:
- Each command fails with exit code 2 (EX_USAGE)
- Error message explains the specific validation failure
- No runtime stages execute (argparse validation fails before dispatch)

**Verification**:
```bash
python -m langagent run --unknown-flag; echo "Exit code: $?"  # Should print 2
python -m langagent init 123invalid 2>&1 | grep 'naming constraints' && echo "✓ Error message helpful"
```

---

### Scenario 6: Ctrl-C Interrupt

**Goal**: Verify Ctrl-C during run/eval returns exit code 130 and closes cleanly

**Commands**:
```bash
# Start agent run and press Ctrl-C after 2 seconds
timeout 2 python -m langagent run demo || echo "Exit code: $?"
```

**Expected Outcome**:
- Exit code 130 (SIGINT)
- Checkpointer closes cleanly (no corrupted state)
- Audit logs flushed
- No dangling processes

**Verification**:
```bash
timeout 2 python -m langagent run demo 2>&1; test $? -eq 130 && echo "✓ Correct exit code"
# Manual verification: Check no zombie processes remain
ps aux | grep langagent
```

---

## Running Tests

After implementing F10, run the test suite to verify all scenarios:

```bash
# Unit tests (≥39 test cases)
pytest tests/cli/test_parser.py -v          # 10 tests
pytest tests/cli/test_runner.py -v          # 9 tests
pytest tests/cli/test_output_formatter.py -v # 19 tests (13 + 6 stdout)

# Integration tests
pytest tests/cli/test_cli_end_to_end.py -v  # 6 tests

# Full CLI layer test suite
pytest tests/cli/ -v --cov=langagent/cli --cov-report=term-missing

# Expected: 100% coverage on cli_runner.py, cli_parser.py, cli_output_formatter.py
# Expected: All 45+ tests passing
```

## Success Criteria Verification

After all scenarios pass:

- [ ] SC-001: `langagent init` completes in <2s (measure with `time` command)
- [ ] SC-004: `langagent doctor` completes in <10s (measure with `time` command)
- [ ] SC-007: stdout contains ONLY chat messages/reports, zero `la.*` tags (grep validation)
- [ ] SC-008: Output fits 80-column terminal (visual inspection or `fold -w 80` test)
- [ ] SC-010: Help text displays in <100ms (measure with `time python -m langagent --help`)
```

---

## Next Steps

After Phase 1 completes, proceed to:

1. **Review artifacts**: Ensure research.md, data-model.md, contracts/, quickstart.md are complete and accurate
2. **Re-validate Constitution Check**: Confirm no design decisions introduced constitutional violations
3. **Generate tasks**: Run `/speckit.tasks` to break down implementation into TDD-driven tasks
4. **Implement**: Follow Red-Green-Refactor workflow with ≥39 test cases leading implementation

**End of Plan**
