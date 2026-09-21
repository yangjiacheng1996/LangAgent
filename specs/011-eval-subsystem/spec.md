# Feature Specification: Eval Subsystem (F11)

**Feature Branch**: `011-eval-subsystem`

**Created**: 2026-09-21

**Status**: Draft

**Constitutional Alignment**: This specification aligns with Constitution Article XV (Top-Level Design Primacy). Required artifacts from `harness/top_level_design/` have been reviewed:
- `workflow.md` — Agent Loop end-to-end business flow
- `architecture_modules.md` — Module dependencies, CLI↔module mapping
- `module_schemas.md` — Schema field constraints, naming conventions

**Input**: User description: "F11 — Eval 子系统（EvalTaskSpec + 5 种 Grader + EvalReport）"

## Clarifications

### Session 2026-09-21

- Q: 评估报告文件的存储位置是什么？ → A: 用户数据目录：`~/.local/share/langagent/reports/<agent-name>-<timestamp>.json`
- Q: `contains` 和 `regex` 评分器是否应该区分大小写？ → A: 默认区分大小写，允许通过 `case_sensitive: false` 配置为不区分
- Q: 当多个任务失败时，系统应该如何确定最终的退出码？ → A: 返回数值最大的退出码（78 > 70 > 65 > 0）

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Basic Evaluation Suite (Priority: P1)

A developer has created an agent and wants to verify it produces correct outputs for a set of test cases before deploying to production. They create YAML files describing test scenarios with expected outputs and run the evaluation command to get a pass/fail report.

**Why this priority**: Core value proposition - enables quality assurance for agents through automated testing. Without this, developers have no systematic way to validate agent behavior.

**Independent Test**: Can be fully tested by creating 3 YAML test cases with exact match grading, running the eval command, and verifying a JSON report is generated with pass/fail results for each case.

**Acceptance Scenarios**:

1. **Given** an agent directory with 3 eval YAML files in `evals/` folder, **When** user runs `langagent eval <agent-dir>`, **Then** system loads all 3 tasks, executes the agent for each input, grades outputs, and writes an EvalReport JSON file to disk
2. **Given** all 3 test cases pass, **When** evaluation completes, **Then** exit code is 0 and report shows 100% pass rate
3. **Given** 1 of 3 test cases fails, **When** evaluation completes, **Then** exit code is non-zero and report shows 66.7% pass rate with failure details

---

### User Story 2 - Semantic Output Validation (Priority: P2)

A developer needs to verify that agent responses are semantically correct even when exact wording varies. They configure test cases to use an LLM judge that evaluates whether actual outputs are semantically equivalent to expected outputs.

**Why this priority**: Enables realistic evaluation for natural language outputs where exact string matching is too brittle. Critical for conversational agents and creative tasks.

**Independent Test**: Can be tested by creating eval tasks with `grader: llm_judge`, running evaluation, and verifying the judge model is called to compare actual vs expected outputs semantically.

**Acceptance Scenarios**:

1. **Given** an eval task with `grader: llm_judge` and expected output "Hello, Alice!", **When** agent produces "Hi there, Alice!", **Then** judge model evaluates semantic equivalence and returns pass/fail
2. **Given** judge model returns "YES" for semantic match, **When** grading completes, **Then** task is marked as passed
3. **Given** judge model uses independent model instance (not the agent's model), **When** evaluation runs, **Then** no judge bias from shared model state

---

### User Story 3 - Tool Call Verification (Priority: P2)

A developer wants to verify that their agent correctly selects and invokes specific tools with expected arguments. They create test cases that check whether the agent's tool calls match expected tool IDs and argument structures.

**Why this priority**: Essential for agents that rely on tool execution. Ensures agent makes correct tool choices and passes appropriate parameters.

**Independent Test**: Can be tested by creating an eval task with `grader: tool_call_match` and expected tool call specification, running evaluation, and verifying the grader checks both tool ID and arguments.

**Acceptance Scenarios**:

1. **Given** eval task expects `{"tool_id": "search", "args": {"query": "AI"}}`, **When** agent produces AIMessage with matching tool call, **Then** grader marks task as passed
2. **Given** eval task expects specific tool call, **When** agent calls different tool or wrong arguments, **Then** grader marks task as failed
3. **Given** eval YAML specifies `grader: tool_call_match` with non-dict expected value, **When** loading tasks, **Then** schema validation fails with clear error message

---

### User Story 4 - Flexible String Matching (Priority: P3)

A developer needs to verify that agent outputs contain specific keywords or match patterns without requiring exact matches. They configure test cases using substring matching or regex patterns.

**Why this priority**: Provides flexibility for output validation when exact matching is too strict but semantic evaluation is unnecessary. Useful for structured outputs and templated responses.

**Independent Test**: Can be tested by creating eval tasks with `grader: contains` or `grader: regex`, running evaluation, and verifying outputs are validated against substrings or patterns.

**Acceptance Scenarios**:

1. **Given** eval task with `grader: contains` and expected "order #12345", **When** agent output includes that substring anywhere, **Then** task passes
2. **Given** eval task with `grader: regex` and pattern `^\d{3}-\d{4}$`, **When** agent output matches format "123-4567", **Then** task passes
3. **Given** eval task with `grader: contains` and list of expected values, **When** agent output contains any one value, **Then** task passes
4. **Given** eval task with `case_sensitive: false`, **When** expected "HELLO" and actual "hello", **Then** task passes (case-insensitive match)

---

### User Story 5 - Performance Metrics Aggregation (Priority: P3)

A developer wants to understand not just pass rates but also latency, token usage, and cost across their evaluation suite. They run evaluations and review aggregated metrics in the report.

**Why this priority**: Enables performance optimization and cost tracking. Helps identify slow test cases and resource-intensive operations.

**Independent Test**: Can be tested by running evaluation with multiple tasks, then verifying EvalReport contains p50/p95 latency, token usage by model, and cost estimates.

**Acceptance Scenarios**:

1. **Given** 10 eval tasks with varying execution times, **When** evaluation completes, **Then** report includes p50 and p95 latency percentiles
2. **Given** tasks use 2 different models, **When** evaluation completes, **Then** report aggregates token usage separately per model
3. **Given** evaluation includes failed tasks, **When** report is generated, **Then** metrics include only completed tasks with separate error count

---

### User Story 6 - Selective Evaluation Execution (Priority: P3)

A developer wants to run only specific test cases or only tests using a particular grader type during development iterations to save time.

**Why this priority**: Speeds up iterative development by allowing focused testing. Avoids running full suite when debugging specific functionality.

**Independent Test**: Can be tested by running `langagent eval --task task_001` or `--grader-only llm_judge` and verifying only matching tasks execute.

**Acceptance Scenarios**:

1. **Given** 10 eval tasks exist, **When** user runs `langagent eval --task task_001`, **Then** only task_001 executes and report contains 1 result
2. **Given** mix of grader types, **When** user runs `--grader-only llm_judge`, **Then** only tasks with that grader execute
3. **Given** filter matches no tasks, **When** evaluation runs, **Then** exit code 0 with report showing 0 tasks executed

---

### Edge Cases

- What happens when `evals/` directory doesn't exist in agent directory?
  - System returns empty task list, generates report with 0 tasks, exits with code 0
- What happens when YAML file is malformed or contains invalid field values?
  - System throws specific error (EvalYamlParseError or ValidationError), logs filename and error details, exits with appropriate code (65 for data errors, 78 for config errors)
- What happens when a single task times out during execution?
  - System terminates that specific task, marks it as failed with timeout error, continues with remaining tasks
- What happens when a grader throws an unexpected exception?
  - System catches exception, marks task as failed, logs error details, continues evaluation without crashing
- What happens when agent produces no output (empty string)?
  - Graders handle empty strings according to their logic (exact_match/contains fail, others may pass if expected is also empty)
- What happens when expected value is a list and agent output matches multiple items?
  - Graders treat list as "any match" - if output matches any item in list, task passes
- What happens when LLM judge returns ambiguous response (neither YES nor NO)?
  - System throws LlmJudgeInvalidResponseError, marks task as failed, logs the invalid response
- What happens when multiple tasks fail with different exit codes (e.g., one timeout=70, one config error=78)?
  - System selects the numerically highest exit code (78 in this example) as the final exit code for the entire evaluation run

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST scan `<agent-dir>/evals/*.yaml` and load all valid YAML files as EvalTaskSpec instances
- **FR-002**: System MUST validate each YAML against EvalTaskSpec schema (8 fields: task_id, input, expected, grader, timeout_s, metadata, grader_extensibility, case_sensitive - with case_sensitive defaulting to true; MUST reject with ValidationError if grader=exact_match and case_sensitive field is present regardless of value)
- **FR-003**: System MUST support 5 grader types: `exact_match`, `contains`, `regex`, `llm_judge`, `tool_call_match`
- **FR-004**: System MUST execute each eval task by running the agent's main loop once with the task input
- **FR-005**: System MUST apply task-level timeout (default 60 seconds, configurable per task via `timeout_s` field)
- **FR-006**: System MUST grade each task output using the specified grader and record pass/fail result
- **FR-007**: System MUST aggregate results into EvalReport containing: report_id, generated_at, agent_dir, task_results, pass_rate, p50_latency_ms, p95_latency_ms, token_usage, cost_usd
- **FR-008**: System MUST write EvalReport to disk as JSON file to platform-specific user data directory (Linux/macOS: `~/.local/share/langagent/reports/`, Windows: `%LOCALAPPDATA%\langagent\reports\`) with filename pattern `<agent-name>-<timestamp>.json` (creates directory if not exists, uses platformdirs library for cross-platform resolution)
- **FR-009**: System MUST return exit code 0 if all tasks pass, non-zero if any task fails
- **FR-010**: System MUST continue evaluation if individual task fails - failures don't halt entire suite
- **FR-011**: System MUST emit lifecycle events at eval start, each task completion, and eval summary
- **FR-012**: System MUST publish protocol events (`eval_task_started`, `eval_task_done`) for metrics collection
- **FR-013**: System MUST use independent model instance for `llm_judge` grader to avoid judge bias
- **FR-014**: System MUST accept CLI filter arguments `--task <task_id>` and `--grader-only <grader_name>` to run subset of tests
- **FR-015**: System MUST validate `tool_call_match` grader has dict-type expected value at both schema load time and runtime
- **FR-016**: System MUST strip whitespace when comparing strings in `exact_match` grader (always case-sensitive; exact_match grader MUST NOT accept case_sensitive parameter - any YAML with grader=exact_match containing case_sensitive field will be rejected at schema validation time per FR-002)
- **FR-017**: System MUST treat expected value as list-of-alternatives when provided as YAML array (any match passes)
- **FR-018**: System MUST compile regex patterns once per task and handle compilation errors gracefully (case sensitivity controlled by case_sensitive parameter, default true)
- **FR-021**: System MUST apply case_sensitive parameter (default true, applicable only to `contains` and `regex` graders) to control case-insensitive matching
- **FR-019**: System MUST aggregate token usage separately per model when tasks use multiple models
- **FR-020**: System MUST calculate exit code as worst_of(all_task_exit_codes) by selecting the numerically highest exit code value using `max(all_task_exit_codes, default=0)` and include in EvalRunResult (returns 0 when all tasks pass)

### Key Entities

- **EvalTaskSpec**: Represents a single evaluation test case with fields: task_id (unique identifier), input (prompt to agent), expected (expected output in various formats), grader (validation method), timeout_s (execution limit), metadata (arbitrary tags), grader_extensibility (future extension registry), case_sensitive (boolean, default true, controls case sensitivity for contains/regex graders)
- **EvalReport**: Aggregated evaluation results (Pydantic model) with fields: report_id (UUID), generated_at (ISO timestamp), agent_dir (path to evaluated agent), task_results (list of individual outcomes), pass_rate (percentage), p50_latency_ms (median), p95_latency_ms (95th percentile), token_usage (per-model breakdown), cost_usd (estimated cost)
- **EvalRunResult**: Return value from eval runner containing: eval_report (aggregated results), final_state (last task's agent state), exit_code (worst failure code)
- **TaskResult**: Individual task outcome (Pydantic model) with fields: task_id (str), passed (bool), actual_output (str), expected_output (Any), grader_used (str), latency_ms (float), error_message (Optional[str]), exit_code (int)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can run evaluation suite on agent directory with single command and receive results in under 5 minutes for suites of 50 tasks
- **SC-002**: System correctly validates 100% of schema violations (missing required fields, invalid grader names, wrong expected types) and exits with appropriate error codes
- **SC-003**: Pass/fail accuracy matches manual verification for all 5 grader types across 100 sample test cases
- **SC-004**: System continues evaluation after individual task failures - 99% of tasks in suite still execute when 1 task crashes
- **SC-005**: LLM judge grader produces semantically accurate evaluations in 90%+ of cases (validated against human judgment on sample set)
- **SC-006**: Evaluation reports include complete performance metrics (latency percentiles, token usage, cost) with <5% measurement error
- **SC-007**: Timeout mechanism terminates long-running tasks within 2 seconds of timeout threshold
- **SC-008**: CLI filter options (--task, --grader-only) reduce execution time by 80%+ when running 10% of task suite

## Assumptions

- Users have already created agent directories following LangAgent structure (agent.py, instructions.md, etc.) before running evaluations
- Agent's main loop (LangGraph graph) is functional and can execute independently for each eval task
- Evaluation tasks are independent - no shared state between tasks, order doesn't matter
- LLM judge grader requires network access to model API (or local model server) - not purely offline
- Token usage tracking relies on model API responses providing token counts - may be incomplete for some providers
- Cost calculation uses standard pricing tables - actual costs may vary based on enterprise agreements
- YAML files in evals/ directory are under version control with agent code
- Evaluation runs in same environment as agent development - access to same models, tools, credentials
- Expected outputs in test cases are human-authored ground truth - no automatic generation of expectations
- Regex patterns in eval tasks use Python `re` module syntax
- Tool call matching uses LangChain's AIMessage.tool_calls structure
- Report files are written to `~/.local/share/langagent/reports/` directory with filenames following pattern `<agent-name>-<timestamp>.json`
- Phase 1 modules (task_loader, report_aggregator) can be developed without runtime dependencies on other features
- Phase 2 graders can be developed in parallel once schemas are finalized
- Phase 3 runner integration happens after F06/F07/F08/F09/F10 dependencies are stable
