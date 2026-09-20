# Feature Specification: ReAct Main Loop Runtime Dispatcher

**Feature Branch**: `008-react-main-loop`

**Created**: 2026-09-20

**Status**: Draft

**Constitutional Alignment**: Article XV (Top-Level Design Primacy), Article VI (Agent Loop and State), Article VIII (TDD Rigidity), Article IX (Quality Diagnostics)

**Input**: User description from F08 feature prompt - Implement runtime layer stage 5 `main_loop`: Drive LangGraph `CompiledStateGraph` to run the ReAct main loop (reasoning → tools → observation) until task completion, user interruption, or termination condition is triggered.

---

## Clarifications

### Session 2026-09-20

- Q: 工具执行错误后的恢复策略是什么？ → A: 仅记录错误到 scratchpad["errors"]，依靠 max_turns 自然终止；不做额外的错误计数或提前终止
- Q: loop 接近 max_turns 时的警告阈值是多少？ → A: 最后 10% 轮次开始警告（turn >= max_turns * 0.9，默认 30 轮时为第 27 轮起）
- Q: graph.stream() 模式的支持优先级是什么？ → A: F08 必须同时实现 invoke() 和 stream() 两种模式，所有测试用例覆盖两者
- Q: state.scratchpad["errors"] 的数据结构是什么？ → A: 结构化列表，含时间戳、工具名、错误消息、轮次：`[{"turn": 3, "tool": "echo", "error": "timeout", "timestamp": "2026-09-20T10:30:45Z"}, ...]`
- Q: dispatch() 在中断时的返回行为是什么？ → A: dispatch() 抛出 HitlInterruptedError 异常，异常对象携带当前 state 作为属性（如 `error.state`）

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Single-Turn Agent Execution (Priority: P1)

**As a** LangAgent user,  
**I want** the agent to execute a single ReAct turn (model call → tool execution → observation),  
**So that** I can see the agent make progress on my task through one complete reasoning cycle.

**Why this priority**: This is the atomic unit of the ReAct loop. Without single-turn execution working correctly, the entire agent runtime fails. This is the foundation for all subsequent functionality.

**Independent Test**: Can be fully tested by invoking `dispatch(graph, state)` once with a fake model that returns one tool call, verifying that the state contains the expected AIMessage and ToolMessage, and delivers immediate value as a complete reasoning cycle.

**Acceptance Scenarios**:

1. **Given** a compiled LangGraph with a fake model and a simple echo tool, **When** dispatch() is called with an initial state containing a HumanMessage("echo hello"), **Then** the returned state contains an AIMessage with tool_calls and a ToolMessage with the echo result
2. **Given** a compiled graph with a model that returns no tool calls, **When** dispatch() is called, **Then** the returned state contains a final AIMessage and the loop terminates
3. **Given** a compiled graph, **When** dispatch() is called and publishes events via the event bus, **Then** tool_call, tool_result, and model_response events are emitted with correct payloads
4. **Given** a single dispatch() call, **When** the turn completes, **Then** MetricsSnapshot is updated with turn count +1 and latency is recorded

---

### User Story 2 - Multi-Turn Loop Convergence (Priority: P1)

**As a** LangAgent user,  
**I want** the agent to run multiple ReAct turns until the task is complete,  
**So that** complex tasks requiring multiple reasoning steps and tool uses can be solved automatically.

**Why this priority**: This is the core value proposition of the ReAct agent - autonomous multi-step problem solving. Without loop convergence, the agent cannot handle real-world tasks.

**Independent Test**: Can be tested by calling `run_until_done(graph, state)` with a fake model that makes 3 tool calls before returning a final answer, verifying convergence and state consistency.

**Acceptance Scenarios**:

1. **Given** a compiled graph with a model that makes 3 tool calls, **When** run_until_done() is called, **Then** the loop executes 3 turns and terminates with a final AIMessage containing no tool_calls
2. **Given** a model that converges after 2 turns, **When** run_until_done() completes, **Then** state.messages contains exactly 2 AIMessages and 2 sets of ToolMessages in correct order
3. **Given** a multi-turn loop, **When** each turn completes, **Then** lifecycle.run.turn and runtime.main_loop.turn.start/end logs are emitted for each turn
4. **Given** a completed loop, **When** run_until_done() returns, **Then** the final state can be passed to exit_cleanup stage without error

---

### User Story 3 - Loop Termination on Max Turns (Priority: P2)

**As a** LangAgent operator,  
**I want** the loop to terminate with an error after max_turns iterations,  
**So that** infinite loops caused by misconfigured models or prompts don't consume resources indefinitely.

**Why this priority**: Essential safety mechanism to prevent resource exhaustion, but less critical than basic functionality. Most well-configured agents will converge before hitting this limit.

**Independent Test**: Can be tested by providing a fake model that always returns tool_calls (never converges) and verifying TokenLimitExceededError is raised after exactly 30 turns with exit code 70.

**Acceptance Scenarios**:

1. **Given** a fake model that always generates tool_calls, **When** run_until_done() reaches 30 turns, **Then** TokenLimitExceededError is raised with exit code 70
2. **Given** max_turns=10, **When** the loop exceeds 10 turns, **Then** the error message contains the turn count and suggests reviewing the model configuration
3. **Given** a loop that hits max_turns, **When** the exception is raised, **Then** the current state is preserved and can be inspected for debugging
4. **Given** a loop approaching max_turns (turn >= max_turns * 0.9), **When** turn 27 completes (for default max_turns=30), **Then** a warning log is emitted indicating the loop is near the limit

---

### User Story 4 - Human-in-the-Loop Interruption (Priority: P2)

**As a** LangAgent user,  
**I want** to interrupt the agent with Ctrl-C or when a tool requires approval,  
**So that** I can stop runaway executions or review sensitive operations before they execute.

**Why this priority**: Critical for user control and safety, but comes after basic loop functionality. Enables interactive workflows and prevents unwanted actions.

**Independent Test**: Can be tested by (a) mocking KeyboardInterrupt during dispatch and verifying HitlInterruptedError with exit code 130, and (b) using a tool with requires_approval=True and verifying LangGraph Interrupt is caught and control returns to caller.

**Acceptance Scenarios**:

1. **Given** a running loop, **When** KeyboardInterrupt is raised, **Then** HitlInterruptedError is raised with exit code 130, the exception carries the current state as an attribute (error.state), and state is preserved
2. **Given** a tool with requires_approval=True, **When** the model calls this tool, **Then** LangGraph Interrupt exception is raised, dispatch() catches it and raises HitlInterruptedError with current state attached
3. **Given** a guardrail interrupt, **When** F04 guardrail middleware blocks an action, **Then** F08 catches GraphInterrupt, raises HitlInterruptedError with state attached, and returns control to CLI (does not re-emit guardrail_block log - F04 already emitted it)
4. **Given** an interrupted loop in eval mode, **When** F11 catches the HitlInterruptedError, **Then** TaskResult.guardrail_blocked=True is recorded and the preserved state from error.state can be inspected without terminating the entire eval run

---

### User Story 5 - AgentState Field Reducer Correctness (Priority: P1)

**As a** LangAgent developer,  
**I want** the 5 AgentState fields to update correctly using their defined reducers,  
**So that** state consistency is maintained across turns and the agent's memory/context evolves as designed.

**Why this priority**: Fundamental correctness requirement. Incorrect state updates break the entire agent execution model and cause unpredictable behavior.

**Independent Test**: Can be tested by calling dispatch() multiple times with different state updates and asserting that messages append (add_messages), todos/scratchpad replace correctly (replace_with_merge), files merge by key (merge_dict), and context overwrites or merges (overwrite_or_merge).

**Acceptance Scenarios**:

1. **Given** two consecutive dispatch() calls, **When** each adds a message, **Then** state.messages length increases by 2 and history is preserved (add_messages reducer)
2. **Given** consecutive todo updates, **When** the second update provides a complete list, **Then** todos are merged correctly without blind overwrite (replace_with_merge reducer)
3. **Given** two file updates for the same file_path, **When** merging, **Then** the second update's keys overwrite the first's keys but don't delete absent keys (merge_dict reducer)
4. **Given** a context update with mode='overwrite', **When** merging, **Then** the entire context is replaced; given mode='merge_with_prior', keys are merged shallowly
5. **Given** scratchpad updates across turns, **When** merging, **Then** each update provides a complete scratchpad dictionary (replace_with_merge reducer, same as todos)

---

### User Story 6 - Event Bus and Structured Logging (Priority: P2)

**As a** LangAgent operator or monitoring system,  
**I want** the main_loop stage to emit events and structured logs for all key actions,  
**So that** I can observe agent behavior, measure performance, and debug issues through telemetry.

**Why this priority**: Essential for production observability but not required for basic agent execution. Can be validated after core loop functionality works.

**Independent Test**: Can be tested by mocking the event bus and logger, running run_until_done(), and asserting that all 13 expected log tags (5 lifecycle.run.* + 7 runtime.main_loop.* + 1 cross_cutting.guardrail.block if triggered) are emitted with correct payloads.

**Acceptance Scenarios**:

1. **Given** a complete run_until_done() execution, **When** the loop starts, **Then** both la.lifecycle.run.start and la.runtime.main_loop.start logs are emitted
2. **Given** 3 ReAct turns, **When** each turn executes, **Then** la.lifecycle.run.turn is emitted 3 times with turn numbers
3. **Given** a tool call, **When** the tool executes, **Then** both tool_call event (via protocol_event_bus) and la.lifecycle.run.tool_call log (via cross_cutting_logger) are emitted simultaneously (dual-channel)
4. **Given** a model response, **When** AIMessage is appended, **Then** model_response event contains usage_metadata for metrics collection
5. **Given** F04 guardrail blocks a tool, **When** the block occurs, **Then** F04 emits la.cross_cutting.guardrail.block (F08 does not re-emit, but counts it in the 13 observed tags)
6. **Given** the loop completes, **When** run_until_done() returns, **Then** la.runtime.main_loop.end log is emitted with final state summary
7. **Given** a loop approaching max_turns (turn >= max_turns * 0.9), **When** the threshold is crossed, **Then** la.runtime.main_loop.near_limit warning log is emitted (counted as part of the 12 F08-emitted tags)

---

### User Story 7 - Stage Capability Boundary Enforcement (Priority: P3)

**As a** LangAgent architect,  
**I want** main_loop stage to be prevented from re-loading directories, re-parsing config, or directly instantiating models,  
**So that** the 6-stage separation of concerns is maintained and unauthorized operations are blocked at runtime.

**Why this priority**: Architectural hygiene and defense-in-depth. Important for long-term maintainability but doesn't affect user-facing functionality if stages are implemented correctly.

**Independent Test**: Can be tested by attempting to call RuntimeDirLoader.load() or RuntimeConfigResolver.resolve() from within a @stage_guard_decorator('main_loop') decorated function and verifying StageCapabilityViolationError is raised with exit code 1.

**Acceptance Scenarios**:

1. **Given** main_loop stage is active, **When** code attempts to call RuntimeDirLoader.load(), **Then** StageCapabilityViolationError is raised (monkeypatch blacklist hit)
2. **Given** main_loop stage is active, **When** code attempts to read .env file via open(), **Then** StageCapabilityViolationError is raised (audit_event blacklist hit)
3. **Given** main_loop stage is active, **When** code attempts to call chat_model_factory.create(), **Then** StageCapabilityViolationError is raised (model instantiation forbidden)
4. **Given** a stage violation in main_loop, **When** the error is logged, **Then** la.cross_cutting.guardrail.block tag is used (not la.runtime.main_loop.fail)

---

### Edge Cases

- **What happens when** a tool raises an unhandled exception during execution?
  - The exception is caught, recorded in state.scratchpad["errors"] as a structured entry: `{"turn": <turn_number>, "tool": <tool_name>, "error": <error_message>, "timestamp": <ISO8601_timestamp>}`, converted to a ToolMessage with error content, and the loop continues (doesn't immediately terminate)
  - metrics.error_rate is incremented
  - Loop relies on max_turns for natural termination; no additional error counting or early termination logic
  - Final exit code is 1 (tool_execution_error) if loop completes with recorded errors

- **What happens when** the model returns malformed tool_calls (invalid JSON args)?
  - LangGraph's tools_execute node catches the parsing error, creates an error ToolMessage, and passes it back to the model
  - The loop continues (model gets a chance to recover)
  - If the model repeatedly produces malformed calls, max_turns termination eventually triggers

- **What happens when** state.messages is empty (no initial HumanMessage)?
  - dispatch() accepts any valid AgentState; if messages is empty, the model receives no user input
  - This is a valid (though unusual) scenario - the model may generate output based solely on system prompt
  - Responsibility for providing initial messages lies with the caller (CLI or eval runner)

- **What happens when** multiple guardrail_block events occur in a single loop (multiple tools require approval)?
  - Each interrupt is handled individually by LangGraph's interrupt mechanism
  - F04 emits la.cross_cutting.guardrail.block once per interrupt
  - F08 catches the first GraphInterrupt, raises HitlInterruptedError with state attached (error.state), and returns control to caller
  - In langagent run mode, the first interrupt stops execution (exit code 130); in eval mode, F11 catches HitlInterruptedError and marks the task as guardrail_blocked=True

- **What happens when** the checkpointer fails to save state mid-loop?
  - LangGraph raises an exception during graph.invoke() or graph.stream()
  - F08 does not catch checkpointer errors (they propagate up)
  - F09 exit_cleanup handles checkpointer cleanup on failure
  - Exit code is typically 1 (general failure) or 4 (I/O error) depending on the underlying cause

- **What happens when** the loop runs for 29 turns and then converges on turn 30?
  - Turn 30 executes normally; if the model returns a final AIMessage (no tool_calls), the loop terminates successfully with exit code 0
  - The max_turns check happens *after* each turn completes, so turn 30 is allowed to finish
  - If turn 30 also produces tool_calls, *then* TokenLimitExceededError is raised

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `dispatch(graph: CompiledStateGraph, state: AgentState) -> AgentState` function that executes one ReAct turn (model call → tools execution → observation) and returns updated state; when LangGraph Interrupt/GraphInterrupt is caught, dispatch() MUST raise HitlInterruptedError with the current state attached as error.state attribute
- **FR-002**: System MUST provide a `run_until_done(graph: CompiledStateGraph, state: AgentState, max_turns: int = 30) -> AgentState` function that runs the ReAct loop until convergence, interruption, or max_turns is exceeded
- **FR-003**: System MUST publish `tool_call`, `tool_result`, and `model_response` events via protocol_event_bus (F03) during each dispatch() call
- **FR-004**: System MUST emit 12 structured log tags (5 la.lifecycle.run.* + 7 la.runtime.main_loop.*) via cross_cutting_logger (F02) during run_until_done() execution; F08 observes (but does not re-emit) 1 additional tag la.cross_cutting.guardrail.block from F04, totaling 13 tags in main_loop stage

  **12 Log Tags Complete List**:
  
  | # | Tag | Trigger Point | Layer |
  |---|-----|--------------|-------|
  | 1 | la.lifecycle.run.start | run_until_done() entry | lifecycle |
  | 2 | la.lifecycle.run.turn | Each turn start | lifecycle |
  | 3 | la.lifecycle.run.tool_call | Tool invocation | lifecycle |
  | 4 | la.lifecycle.run.tool_result | Tool return | lifecycle |
  | 5 | la.lifecycle.run.model_response | Model response | lifecycle |
  | 6 | la.runtime.main_loop.start | run_until_done() entry | runtime |
  | 7 | la.runtime.main_loop.turn.start | dispatch() entry | runtime |
  | 8 | la.runtime.main_loop.tool_call | Tool invocation | runtime |
  | 9 | la.runtime.main_loop.tool_result | Tool return | runtime |
  | 10 | la.runtime.main_loop.model_call | After model_call node | runtime |
  | 11 | la.runtime.main_loop.turn.end | dispatch() exit | runtime |
  | 12 | la.runtime.main_loop.near_limit | turn >= max_turns * 0.9 | runtime |
  | +1 | la.cross_cutting.guardrail.block | F04 guardrail trigger (observed) | observed |
- **FR-005**: System MUST observe (but not re-emit) the `la.cross_cutting.guardrail.block` tag when F04 guardrail middleware triggers an interrupt (counted in 13 total observed tags)
- **FR-006**: System MUST raise `TokenLimitExceededError` with exit code 70 when turn_count exceeds max_turns
- **FR-007**: System MUST raise `HitlInterruptedError` with exit code 130 when KeyboardInterrupt is caught during the loop
- **FR-008**: System MUST catch LangGraph `GraphInterrupt` / `Interrupt` exceptions (triggered by F04 guardrail or tool requires_approval=True) and raise HitlInterruptedError with current state attached as error.state attribute, returning control to caller without re-emitting guardrail_block logs
- **FR-009**: System MUST apply 5 field reducers to AgentState: `add_messages` (messages), `replace_with_merge` (todos, scratchpad), `merge_dict` (files), `overwrite_or_merge` (context)
- **FR-010**: System MUST import all LangChain/LangGraph types (BaseMessage, add_messages, interrupt) via `langagent.primitives.langchain_types` re-exports (not direct langchain/langgraph imports)
- **FR-011**: System MUST import all 3 reducer functions (replace_with_merge, merge_dict, overwrite_or_merge) from `langagent.primitives.state_reducers` (not defined in runtime layer)
- **FR-012**: System MUST apply `@cross_cutting_stage_guard_decorator('main_loop')` to enforce stage capability boundaries (monkeypatch blacklist + audit_event blacklist)
- **FR-013**: System MUST NOT re-load agent directory, re-parse config, or directly instantiate models during main_loop stage (violations raise StageCapabilityViolationError with exit code 1)
- **FR-014**: System MUST provide `build_doctor_probes() -> tuple[Callable, Callable]` factory function that constructs model and checkpointer probe functions for the doctor subcommand
- **FR-015**: System MUST increment MetricsSnapshot.turn_count after each dispatch() call
- **FR-016**: System MUST record tool execution errors in state.scratchpad["errors"] as structured entries (containing turn number, tool name, error message, ISO8601 timestamp) and continue the loop, relying on max_turns for natural termination without additional error counting logic; when max_turns is exceeded with recorded errors present, TokenLimitExceededError (exit code 70) takes precedence over tool_execution_error (exit code 1) as the loop termination mechanism
- **FR-017**: System MUST support both graph.invoke() and graph.stream() invocation modes; F08 deliverable includes complete implementation of both modes with all test cases covering invoke() and stream() behavior
- **FR-018**: System MUST preserve the current AgentState when any termination condition triggers (max_turns, interrupt, convergence) for inspection by exit_cleanup stage
- **FR-019**: System MUST emit dual-channel signals (Event via protocol_event_bus + structured log via cross_cutting_logger) independently for tool_call, tool_result, and model_response; failure in one channel MUST NOT block the other channel (best-effort delivery)
- **FR-020**: System MUST handle missing initial state fields gracefully; F08 dispatch() is responsible for checking optional fields (todos/files/context/scratchpad) before graph.invoke() and initializing them as empty list/dict if absent per TypedDict total=False semantics

### Key Entities

- **MainLoopDispatcher**: Runtime class that owns dispatch() and run_until_done() methods; coordinates graph invocation, event publishing, and state updates
- **AgentState**: 5-field TypedDict (messages, todos, files, context, scratchpad) with annotated reducers; the authoritative state container for LangGraph execution
- **CompiledStateGraph**: LangGraph compiled graph (input to dispatch); provided by F01 primitives_state_graph_builder.build(); F08 does not construct graphs
- **MetricsSnapshot**: Mutable metrics container updated after each turn (turn_count, latency, error_rate); owned by F02 cross_cutting_metrics_collector
- **Event**: Protocol layer event type (tool_call / tool_result / model_response / guardrail_block); published via F03 protocol_event_bus
- **StageCapabilityViolationError**: Exception raised when main_loop stage attempts forbidden operations (defined in F06 cross_cutting_stage_guard)
- **TokenLimitExceededError**: Exception raised when max_turns is exceeded (exit code 70)
- **HitlInterruptedError**: Exception raised when user interrupts with Ctrl-C or HITL mechanism triggers (exit code 130); carries the current AgentState as an attribute (error.state) for inspection and potential resumption

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A well-configured agent with a simple 3-turn task converges to a final answer within 5 seconds on local hardware (Qwen3.8-27B on vLLM)
- **SC-002**: The main loop handles 100 consecutive turns (artificial stress test with fake model) without memory leaks or performance degradation
- **SC-003**: All 13 log tags (12 emitted by F08 + 1 observed from F04) appear in the log output for a single run_until_done() execution with guardrail triggered
- **SC-004**: Tool execution errors are recorded as structured entries (with turn, tool, error, timestamp fields) but do not crash the loop - the loop relies on max_turns for natural termination without additional error counting logic
- **SC-005**: AgentState reducer tests pass for all 5 fields across 10+ consecutive dispatch() calls without state corruption
- **SC-006**: The dispatcher can be interrupted via KeyboardInterrupt at any point during a turn and raises HitlInterruptedError with exit code 130, carrying the preserved state in error.state attribute
- **SC-007**: Integration tests using real LangGraph (not mocked) with FakeListChatModel and real BaseTool subclasses pass without mocking graph behavior; tests cover both graph.invoke() and graph.stream() invocation modes
- **SC-008**: Stage capability violations (e.g., attempting to read .env during main_loop) are detected and raise StageCapabilityViolationError within 1ms of the forbidden operation
- **SC-009**: Event bus subscribers (metrics_collector, audit_recorder) receive all expected events during a multi-turn loop without dropped messages
- **SC-010**: The build_doctor_probes() factory returns working probe functions that successfully test model connectivity and checkpointer initialization when called by F10 doctor dispatch

---

## Assumptions

- The CompiledStateGraph passed to dispatch() is already compiled by F01 primitives_state_graph_builder.build() and contains all necessary nodes (model_call, tools_execute, should_continue) and edges
- The graph's nodes will use the BaseChatModel instance from RuntimeConfig.model (populated by F01 dispatch during model_adapt stage) - F08 does not instantiate or configure models
- The graph already has F04 guardrail middleware and any user-defined middleware injected during graph_compose stage (F01 responsibility) - F08 only drives the graph
- All LangChain/LangGraph types needed by F08 are available via primitives_langchain_types re-exports (no direct imports from langchain/langgraph packages)
- All 3 reducer functions are available from primitives_state_reducers (implemented by F01, not F08)
- The protocol_event_bus (F03) and cross_cutting_logger (F02) are initialized before main_loop stage begins
- The cross_cutting_stage_guard module (F06) provides the @stage_guard_decorator and stage blacklist table before F08 needs to apply it
- The max_turns default of 30 is sufficient for 95% of real-world tasks when using a capable model (e.g., GPT-4, Claude, or fine-tuned Qwen)
- KeyboardInterrupt will be the primary user interruption mechanism in CLI mode; LangGraph interrupt() handles tool-level HITL and guardrail blocks
- The eval runner (F11) will handle HitlInterruptedError differently from CLI runner (F10) - F11 catches the exception, extracts state from error.state, records guardrail_blocked=True, and continues eval loop; F10 propagates the exception and exits with code 130
- Tool execution errors are non-fatal by default - the loop records them as structured entries in scratchpad["errors"] with turn/tool/error/timestamp fields and relies on max_turns for natural termination (no additional error counting or early termination)
- Loop warns when approaching max_turns threshold: warning log emitted when turn >= max_turns * 0.9 (e.g., turn 27 for default max_turns=30)
- Checkpointer persistence is handled by LangGraph automatically during graph.invoke() - F08 does not manually call checkpointer.save() or checkpointer.load()
- State serialization/deserialization is handled by LangGraph's built-in checkpoint mechanism - F08 only works with in-memory AgentState TypedDict instances
- The 12 log tags emitted by F08 (5 lifecycle.run.* + 7 runtime.main_loop.*) are already registered in F02 cross_cutting_logger.ALLOWED_TAGS (≥46 total tags)
- The dual-channel emission pattern (Event + Log) is intentional and required - removing either channel would break downstream consumers (metrics, audit, CLI output)
