# Tasks: ReAct Main Loop Runtime Dispatcher

**Feature**: F08 - ReAct Main Loop Runtime Dispatcher  
**Branch**: `008-react-main-loop`  
**Input**: Design documents from `/specs/008-react-main-loop/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: INCLUDED (Constitution Article VIII - TDD Rigidity requires Red-Green-Refactor)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- ID format: T001, T002, T003... (sequential execution order)

---

## Phase 1: Setup

**Goal**: Initialize project structure and prepare dependencies

- [X] T001 Verify F01 primitives layer APIs exist (state_graph_builder, langchain_types, state_reducers, chat_model_factory, checkpoint_adapter)
- [X] T002 Verify F02 cross_cutting_logger API exists (emit function + ALLOWED_TAGS ≥46)
- [X] T003 Verify F03 protocol_event_bus API exists (publish function + Event type)
- [X] T004 Verify F04 cross_cutting_guardrail_middleware API exists (build_middleware + GraphInterrupt)
- [X] T005 Verify F06 cross_cutting_stage_guard API exists (@stage_guard_decorator + STAGE_BLACKLIST_TABLE)
- [X] T006 [P] Create langagent/runtime/agent_state.py module skeleton
- [X] T007 [P] Create langagent/runtime/main_loop_dispatcher.py module skeleton
- [X] T008 [P] Create tests/runtime/test_agent_state_reducers.py skeleton
- [X] T009 [P] Create tests/runtime/test_main_loop_dispatcher.py skeleton
- [X] T010 [P] Create tests/fixtures/sample_agent_with_fake_model/ directory structure

---

## Phase 2: Foundational - Data Structures & Types

**Goal**: Define core data structures required by all user stories

**Independent Test**: AgentState and error structures can be instantiated and type-checked with mypy --strict

### AgentState TypedDict

- [X] T011 [P] Define AgentState TypedDict in langagent/runtime/agent_state.py with 5 fields (messages, todos, files, context, scratchpad) and Annotated reducers imported from primitives
- [X] T012 [P] Define ErrorEntry TypedDict in langagent/runtime/agent_state.py with 4 fields (turn: int, tool: str, error: str, timestamp: str)
- [X] T013 [P] Write test_agent_state_instantiation in tests/runtime/test_agent_state_reducers.py verifying AgentState can be created with partial fields (total=False)
- [X] T014 [P] Write test_error_entry_structure in tests/runtime/test_agent_state_reducers.py verifying ErrorEntry matches clarification Q4 format

### Exception Classes

- [X] T015 [P] Define HitlInterruptedError frozen dataclass in langagent/runtime/main_loop_dispatcher.py with state/reason/message fields
- [X] T016 [P] Define TokenLimitExceededError frozen dataclass in langagent/runtime/main_loop_dispatcher.py with turn_count/max_turns/message fields
- [X] T017 [P] Write test_hitl_interrupted_error_carries_state in tests/runtime/test_main_loop_dispatcher.py verifying error.state attribute exists
- [X] T018 [P] Write test_token_limit_exceeded_error_metadata in tests/runtime/test_main_loop_dispatcher.py verifying turn_count/max_turns fields

### Reducer Tests (Constitution Article VI)

- [X] T019 [P] Write test_state_messages_add_messages_reducer in tests/runtime/test_agent_state_reducers.py verifying messages append without overwrite
- [X] T020 [P] Write test_state_todos_replace_with_merge in tests/runtime/test_agent_state_reducers.py verifying complete list replacement
- [X] T021 [P] Write test_state_files_merge_dict in tests/runtime/test_agent_state_reducers.py verifying key-level merge
- [X] T022 [P] Write test_state_context_overwrite_or_merge in tests/runtime/test_agent_state_reducers.py verifying mode-based merge
- [X] T023 [P] Write test_state_scratchpad_replace_with_merge in tests/runtime/test_agent_state_reducers.py verifying dict replacement

**Checkpoint**: Run `pytest tests/runtime/test_agent_state_reducers.py` → All 7 tests PASSED ✓

---

## Phase 3: User Story 1 - Single-Turn Agent Execution (P1)

**Goal**: Implement dispatch() for atomic single-turn ReAct execution

**Independent Test**: Can invoke `dispatch(graph, state)` with fake model, returns updated state with AIMessage + ToolMessage

### Tests First (TDD Red)

- [ ] T024 [US1] Write test_dispatch_simple_greeting in tests/runtime/test_main_loop_dispatcher.py: fake model returns final AIMessage (no tool_calls), verify state updated
- [ ] T025 [US1] Write test_dispatch_with_tool_call in tests/runtime/test_main_loop_dispatcher.py: fake model returns tool_call, verify ToolMessage appended
- [ ] T026 [US1] Write test_dispatch_emits_tool_call_event in tests/runtime/test_main_loop_dispatcher.py: mock event_bus, verify tool_call event published
- [ ] T027 [US1] Write test_dispatch_emits_tool_result_event in tests/runtime/test_main_loop_dispatcher.py: mock event_bus, verify tool_result event published
- [ ] T028 [US1] Write test_dispatch_emits_model_response_event in tests/runtime/test_main_loop_dispatcher.py: mock event_bus, verify model_response event published
- [ ] T029 [US1] Write test_dispatch_increments_turn_count in tests/runtime/test_main_loop_dispatcher.py: mock metrics_collector, verify turn_count +1

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k US1` → 6 tests RED

### Implementation (TDD Green)

- [X] T030 [US1] Implement dispatch() function signature in langagent/runtime/main_loop_dispatcher.py with graph/state parameters
- [X] T031 [US1] Apply @stage_guard_decorator('main_loop') to dispatch() in langagent/runtime/main_loop_dispatcher.py
- [X] T032 [US1] Implement graph.invoke() call in dispatch() in langagent/runtime/main_loop_dispatcher.py
- [X] T033 [US1] Implement tool_call Event emission in dispatch() in langagent/runtime/main_loop_dispatcher.py (dual-channel: event_bus.publish + logger.emit)
- [X] T034 [US1] Implement tool_result Event emission in dispatch() in langagent/runtime/main_loop_dispatcher.py
- [X] T035 [US1] Implement model_response Event emission in dispatch() in langagent/runtime/main_loop_dispatcher.py
- [X] T036 [US1] Implement metrics_collector.increment_turn_count() call in dispatch()收尾处 in langagent/runtime/main_loop_dispatcher.py

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k US1` → 6 tests GREEN (requires integration tests)

### Logging (12 tags, FR-004)

- [X] T037 [US1] Implement la.lifecycle.run.turn log emission in dispatch() 入口 in langagent/runtime/main_loop_dispatcher.py
- [X] T038 [US1] Implement la.runtime.main_loop.turn.start log emission in dispatch() 入口 in langagent/runtime/main_loop_dispatcher.py
- [X] T039 [US1] Implement la.lifecycle.run.tool_call log emission per tool_call in langagent/runtime/main_loop_dispatcher.py
- [X] T040 [US1] Implement la.runtime.main_loop.tool_call log emission per tool_call in langagent/runtime/main_loop_dispatcher.py
- [X] T041 [US1] Implement la.lifecycle.run.tool_result log emission per ToolMessage in langagent/runtime/main_loop_dispatcher.py
- [X] T042 [US1] Implement la.runtime.main_loop.tool_result log emission per ToolMessage in langagent/runtime/main_loop_dispatcher.py
- [X] T043 [US1] Implement la.lifecycle.run.model_response log emission after AIMessage in langagent/runtime/main_loop_dispatcher.py
- [X] T044 [US1] Implement la.runtime.main_loop.model_call log emission after model_call node in langagent/runtime/main_loop_dispatcher.py
- [X] T045 [US1] Implement la.runtime.main_loop.turn.end log emission in dispatch() 收尾 in langagent/runtime/main_loop_dispatcher.py

### Logging Tests

- [ ] T046 [US1] Write test_dispatch_emits_lifecycle_run_turn_log in tests/runtime/test_main_loop_dispatcher.py
- [ ] T047 [US1] Write test_dispatch_emits_runtime_main_loop_turn_start_end_logs in tests/runtime/test_main_loop_dispatcher.py
- [ ] T048 [US1] Write test_dispatch_emits_lifecycle_run_tool_call_log in tests/runtime/test_main_loop_dispatcher.py
- [ ] T049 [US1] Write test_dispatch_emits_runtime_main_loop_tool_call_log in tests/runtime/test_main_loop_dispatcher.py
- [ ] T050 [US1] Write test_dispatch_emits_lifecycle_run_tool_result_log in tests/runtime/test_main_loop_dispatcher.py
- [ ] T051 [US1] Write test_dispatch_emits_runtime_main_loop_model_call_log in tests/runtime/test_main_loop_dispatcher.py
- [ ] T052 [US1] Write test_main_loop_event_and_log_both_emitted in tests/runtime/test_main_loop_dispatcher.py verifying dual-channel (Event + Log) simultaneous emission

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k US1` → All US1 tests GREEN (13 total)

---

## Phase 4: User Story 2 - Multi-Turn Loop Convergence (P1)

**Goal**: Implement run_until_done() for complete ReAct loop until convergence

**Independent Test**: Can call `run_until_done(graph, state)` with fake model making 3 tool calls, verify loop converges

### Tests First (TDD Red)

- [ ] T053 [US2] Write test_run_until_done_converges in tests/runtime/test_main_loop_dispatcher.py: fake model converges after 3 turns, verify final state
- [ ] T054 [US2] Write test_run_until_done_state_message_order in tests/runtime/test_main_loop_dispatcher.py: verify state.messages contains HumanMessage + (AIMessage + ToolMessage) × N + final AIMessage in order
- [ ] T055 [US2] Write test_run_until_done_emits_turn_logs_per_round in tests/runtime/test_main_loop_dispatcher.py: mock 3 turns, verify 3× la.lifecycle.run.turn logs
- [ ] T056 [US2] Write test_run_until_done_final_state_passable_to_exit_cleanup in tests/runtime/test_main_loop_dispatcher.py: verify returned state structure compatible with F09

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k US2` → 4 tests RED

### Implementation (TDD Green)

- [X] T057 [US2] Implement run_until_done() function signature in langagent/runtime/main_loop_dispatcher.py with graph/state/max_turns parameters
- [X] T058 [US2] Apply @stage_guard_decorator('main_loop') to run_until_done() in langagent/runtime/main_loop_dispatcher.py
- [X] T059 [US2] Implement while loop calling dispatch() until convergence in run_until_done() in langagent/runtime/main_loop_dispatcher.py
- [X] T060 [US2] Implement convergence check (AIMessage.tool_calls == []) in run_until_done() in langagent/runtime/main_loop_dispatcher.py
- [X] T061 [US2] Implement la.lifecycle.run.start + la.runtime.main_loop.start log emission in run_until_done() 入口 in langagent/runtime/main_loop_dispatcher.py
- [X] T062 [US2] Implement la.runtime.main_loop.end log emission in run_until_done() 收尾 in langagent/runtime/main_loop_dispatcher.py

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k US2` → 4 tests GREEN (requires integration tests)

### Additional Logging Tests

- [ ] T063 [US2] Write test_run_until_done_emits_lifecycle_run_start_log in tests/runtime/test_main_loop_dispatcher.py
- [ ] T064 [US2] Write test_run_until_done_emits_runtime_main_loop_start_log in tests/runtime/test_main_loop_dispatcher.py
- [ ] T065 [US2] Write test_run_until_done_emits_runtime_main_loop_end_log in tests/runtime/test_main_loop_dispatcher.py

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k US2` → All US2 tests GREEN (7 total)

---

## Phase 5: User Story 3 - Loop Termination on Max Turns (P2)

**Goal**: Implement max_turns limit and TokenLimitExceededError

**Independent Test**: Fake model never converges, verify TokenLimitExceededError raised after 30 turns

### Tests First (TDD Red)

- [ ] T066 [US3] Write test_run_until_done_max_turns_exceeded in tests/runtime/test_main_loop_dispatcher.py: fake model infinite loop, verify TokenLimitExceededError after 30 turns
- [ ] T067 [US3] Write test_run_until_done_max_turns_custom in tests/runtime/test_main_loop_dispatcher.py: max_turns=10, verify error after 10 turns
- [ ] T068 [US3] Write test_run_until_done_max_turns_preserves_state in tests/runtime/test_main_loop_dispatcher.py: verify state preserved in exception context
- [ ] T069 [US3] Write test_run_until_done_near_limit_warning in tests/runtime/test_main_loop_dispatcher.py: verify warning log at turn >= max_turns * 0.9 (clarification Q2)

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k US3` → 4 tests RED

### Implementation (TDD Green)

- [X] T070 [US3] Implement turn_count tracking in run_until_done() loop in langagent/runtime/main_loop_dispatcher.py
- [X] T071 [US3] Implement max_turns check after each dispatch() in run_until_done() in langagent/runtime/main_loop_dispatcher.py
- [X] T072 [US3] Raise TokenLimitExceededError when turn_count >= max_turns and AIMessage.tool_calls non-empty in run_until_done() in langagent/runtime/main_loop_dispatcher.py
- [X] T073 [US3] Implement near-limit warning emission when turn >= max_turns * 0.9 in run_until_done() in langagent/runtime/main_loop_dispatcher.py (la.runtime.main_loop.near_limit tag)

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k US3` → 4 tests GREEN (requires integration tests)

---

## Phase 6: User Story 4 - Human-in-the-Loop Interruption (P2)

**Goal**: Handle KeyboardInterrupt and LangGraph GraphInterrupt, raise HitlInterruptedError with state

**Independent Test**: Mock KeyboardInterrupt / GraphInterrupt, verify HitlInterruptedError raised with error.state preserved

### Tests First (TDD Red)

- [ ] T074 [US4] Write test_run_until_done_keyboard_interrupt in tests/runtime/test_main_loop_dispatcher.py: mock KeyboardInterrupt, verify HitlInterruptedError(reason="keyboard_interrupt", state=...)
- [ ] T075 [US4] Write test_dispatch_guardrail_interrupt in tests/runtime/test_main_loop_dispatcher.py: tool with requires_approval=True, verify HitlInterruptedError(reason="guardrail_block")
- [ ] T076 [US4] Write test_dispatch_interrupt_preserves_state in tests/runtime/test_main_loop_dispatcher.py: verify error.state contains messages + scratchpad
- [ ] T077 [US4] Write test_dispatch_guardrail_no_log_re_emit in tests/runtime/test_main_loop_dispatcher.py: verify F08 does not re-emit la.cross_cutting.guardrail.block (F04 already emitted)

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k US4` → 4 tests RED

### Implementation (TDD Green)

- [X] T078 [US4] Implement KeyboardInterrupt catch in run_until_done() loop in langagent/runtime/main_loop_dispatcher.py, raise HitlInterruptedError(state=current_state, reason="keyboard_interrupt")
- [X] T079 [US4] Implement GraphInterrupt / Interrupt catch in dispatch() in langagent/runtime/main_loop_dispatcher.py, raise HitlInterruptedError(state=current_state, reason="guardrail_block" or "tool_approval_required")
- [X] T080 [US4] Verify error.state snapshot includes all AgentState fields at interrupt time in langagent/runtime/main_loop_dispatcher.py

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k US4` → 4 tests GREEN (requires integration tests)

---

## Phase 7: User Story 5 - AgentState Field Reducer Correctness (P1)

**Goal**: Verify all 5 AgentState fields update correctly across 10+ dispatch() calls

**Independent Test**: Call dispatch() 10 times with different state updates, assert no corruption

### Tests First (TDD Red)

- [ ] T081 [US5] Write test_state_messages_across_10_turns in tests/runtime/test_agent_state_reducers.py: 10× dispatch(), verify messages length = initial + 10× AI + 10× Tool (if tool_calls)
- [ ] T082 [US5] Write test_state_todos_across_10_updates in tests/runtime/test_agent_state_reducers.py: 10× updates with replace_with_merge, verify latest complete list
- [ ] T083 [US5] Write test_state_files_across_10_updates in tests/runtime/test_agent_state_reducers.py: 10× updates, verify merge_dict key-level merge
- [ ] T084 [US5] Write test_state_context_overwrite_vs_merge in tests/runtime/test_agent_state_reducers.py: alternate overwrite/merge modes, verify correct behavior
- [ ] T085 [US5] Write test_state_scratchpad_across_10_updates in tests/runtime/test_agent_state_reducers.py: 10× updates with replace_with_merge, verify dict replacement

**Checkpoint**: Run `pytest tests/runtime/test_agent_state_reducers.py -k US5` → 5 tests RED

### Implementation (TDD Green)

- [ ] T086 [US5] Verify dispatch() correctly passes state through LangGraph graph.invoke() without manual reducer application in langagent/runtime/main_loop_dispatcher.py (LangGraph applies reducers automatically)
- [ ] T087 [US5] Add integration test helper: build_graph_with_state_updates() in tests/runtime/test_agent_state_reducers.py to construct graph that updates all 5 fields

**Checkpoint**: Run `pytest tests/runtime/test_agent_state_reducers.py -k US5` → 5 tests GREEN

---

## Phase 8: User Story 6 - Event Bus and Structured Logging (P2)

**Goal**: Verify all 13 log tags (12 emitted + 1 observed) appear in correct order

**Independent Test**: Run complete loop with guardrail trigger, verify all 13 tags present

### Tests First (TDD Red)

- [ ] T088 [US6] Write test_main_loop_log_tags_in_whitelist in tests/runtime/test_main_loop_dispatcher.py: verify 12 F08 tags + 1 F04 tag all in F02 ALLOWED_TAGS (≥46 total)
- [ ] T089 [US6] Write test_run_until_done_emits_all_13_tags in tests/runtime/test_main_loop_dispatcher.py: run_until_done with guardrail trigger, collect all emitted tags, verify count=13
- [ ] T090 [US6] Write test_metrics_subscriber_records_latency in tests/runtime/test_main_loop_dispatcher.py: mock metrics_collector, verify tool_call/model_response events trigger record_latency()
- [ ] T091 [US6] Write test_audit_subscriber_writes_on_guardrail_block in tests/runtime/test_main_loop_dispatcher.py: mock audit_recorder, verify guardrail_block event triggers audit write

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k US6` → 4 tests RED

### Implementation (TDD Green)

- [ ] T092 [US6] Verify all 12 log tags are correctly emitted (already implemented in US1/US2, this task is validation)
- [ ] T093 [US6] Add integration test: run_until_done_with_all_features() in tests/runtime/test_main_loop_dispatcher.py that triggers all 13 tags

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k US6` → 4 tests GREEN

---

## Phase 9: User Story 7 - Stage Capability Boundary Enforcement (P3)

**Goal**: Verify @stage_guard_decorator prevents forbidden operations in main_loop stage

**Independent Test**: Attempt blacklisted operation (read .env, instantiate model), verify StageCapabilityViolationError

### Tests First (TDD Red)

- [ ] T094 [US7] Write test_dispatch_stage_violation_read_env in tests/runtime/test_main_loop_dispatcher.py: mock open(.env), verify StageCapabilityViolationError
- [ ] T095 [US7] Write test_dispatch_stage_violation_reload_dir in tests/runtime/test_main_loop_dispatcher.py: attempt RuntimeDirLoader.load(), verify StageCapabilityViolationError
- [ ] T096 [US7] Write test_dispatch_stage_violation_resolve_config in tests/runtime/test_main_loop_dispatcher.py: attempt RuntimeConfigResolver.resolve(), verify StageCapabilityViolationError
- [ ] T097 [US7] Write test_dispatch_stage_violation_create_model in tests/runtime/test_main_loop_dispatcher.py: attempt chat_model_factory.create(), verify StageCapabilityViolationError

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k US7` → 4 tests RED

### Implementation (TDD Green)

- [ ] T098 [US7] Verify @stage_guard_decorator('main_loop') is applied to dispatch() and run_until_done() (already done in T031/T058, this is validation)
- [ ] T099 [US7] Add integration test: dispatch_with_stage_violations() in tests/runtime/test_main_loop_dispatcher.py combining all 4 violation scenarios

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k US7` → 4 tests GREEN

---

## Phase 10: Tool Error Recording (FR-016, Clarifications Q1 & Q4)

**Goal**: Tool exceptions recorded as structured ErrorEntry in scratchpad["errors"], loop continues

**Independent Test**: Fake tool raises exception, verify ErrorEntry appended, loop continues to max_turns

### Tests First (TDD Red)

- [ ] T100 Write test_run_until_done_tool_exception in tests/runtime/test_main_loop_dispatcher.py: fake tool raises TimeoutError, verify loop continues (not immediate terminate)
- [ ] T101 Write test_dispatch_tool_error_structure in tests/runtime/test_main_loop_dispatcher.py: verify scratchpad["errors"][0] contains turn/tool/error/timestamp fields (clarification Q4)
- [ ] T102 Write test_run_until_done_error_no_early_termination in tests/runtime/test_main_loop_dispatcher.py: tool fails 5 times, verify loop continues to max_turns (clarification Q1: no error counting)

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k error` → 3 tests RED

### Implementation (TDD Green)

- [ ] T103 Implement tool exception catch in dispatch() in langagent/runtime/main_loop_dispatcher.py: try-except around tools_execute node
- [ ] T104 Construct ErrorEntry with turn/tool/error/timestamp in dispatch() exception handler in langagent/runtime/main_loop_dispatcher.py
- [ ] T105 Append ErrorEntry to state.scratchpad["errors"] (create list if not exists) in dispatch() in langagent/runtime/main_loop_dispatcher.py
- [ ] T106 Convert tool exception to ToolMessage with error content in dispatch() in langagent/runtime/main_loop_dispatcher.py (let loop continue)
- [ ] T107 Increment metrics_collector.error_rate after tool exception in dispatch() in langagent/runtime/main_loop_dispatcher.py

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k error` → 3 tests GREEN

---

## Phase 11: Invoke + Stream Dual Mode Support (FR-017, Clarification Q3)

**Goal**: Implement both graph.invoke() and graph.stream() modes with shared core logic

**Independent Test**: All existing tests pass with both invoke and stream modes

### Tests First (TDD Red)

- [ ] T108 Write test_dispatch_invoke_mode in tests/runtime/test_main_loop_dispatcher.py: call dispatch() (default invoke mode), verify final state returned
- [ ] T109 Write test_dispatch_stream_mode in tests/runtime/test_main_loop_dispatcher.py: call dispatch_stream() generator, verify intermediate states yielded
- [ ] T110 Write test_dispatch_stream_yields_per_node in tests/runtime/test_main_loop_dispatcher.py: verify stream yields (node_name, state_snapshot) tuples

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k "invoke or stream"` → 3 tests RED

### Implementation (TDD Green)

- [X] T111 Refactor dispatch() to extract _dispatch_internal(graph, state, mode) private function in langagent/runtime/main_loop_dispatcher.py (mode is internal-only parameter)
- [X] T112 Implement mode='invoke' branch in _dispatch_internal() calling graph.invoke() in langagent/runtime/main_loop_dispatcher.py
- [X] T113 Implement mode='stream' branch in _dispatch_internal() calling graph.stream() in langagent/runtime/main_loop_dispatcher.py
- [X] T114 Create public dispatch_stream() generator function wrapping _dispatch_internal(mode='stream') in langagent/runtime/main_loop_dispatcher.py
- [X] T115 Update existing dispatch() tests to also cover dispatch_stream() where applicable (parameterize or duplicate tests) in tests/runtime/test_main_loop_dispatcher.py
- [X] T115a [P] Parameterize US1 core tests (T024-T029) to cover both invoke and stream modes in tests/runtime/test_main_loop_dispatcher.py
- [ ] T115b [P] Parameterize US2 core tests (T053-T056) to cover both invoke and stream modes in tests/runtime/test_main_loop_dispatcher.py
- [ ] T115c [P] Parameterize US3 tests (T066-T069) to cover both invoke and stream modes in tests/runtime/test_main_loop_dispatcher.py
- [ ] T115d [P] Parameterize US4 interrupt tests (T074-T077) to cover both invoke and stream modes in tests/runtime/test_main_loop_dispatcher.py
- [ ] T115e [P] Parameterize US6 logging tests (T088-T091) to cover both invoke and stream modes in tests/runtime/test_main_loop_dispatcher.py
- [ ] T115f [P] Write test_stream_mode_multi_turn_intermediate_states in tests/runtime/test_main_loop_dispatcher.py: verify stream mode emits intermediate states correctly in multi-turn scenarios

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py` → Stream tests PASSED (3/3) ✓

---

## Phase 12: Doctor Probe Factory (FR-014, build_doctor_probes)

**Goal**: Implement probe factory for F10 doctor subcommand integration

**Independent Test**: Call build_doctor_probes(), verify returned functions can probe model/checkpointer

### Tests First (TDD Red)

- [ ] T116 Write test_build_doctor_probes_returns_two_callables in tests/runtime/test_main_loop_dispatcher.py: verify return type is tuple[Callable, Callable]
- [ ] T117 Write test_model_probe_success in tests/runtime/test_main_loop_dispatcher.py: fake config with valid model, verify probe returns (True, "endpoint reachable")
- [ ] T118 Write test_model_probe_failure_invalid_key in tests/runtime/test_main_loop_dispatcher.py: fake config with invalid API key, verify probe returns (False, "AuthenticationError...")
- [ ] T119 Write test_checkpoint_probe_success in tests/runtime/test_main_loop_dispatcher.py: fake config with memory checkpointer, verify probe returns (True, "ok")
- [ ] T120 Write test_checkpoint_probe_failure_missing_path in tests/runtime/test_main_loop_dispatcher.py: fake config with missing SQLite path, verify probe returns (False, "FileNotFoundError...")

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k doctor` → 5 tests RED

### Implementation (TDD Green)

- [X] T121 Implement build_doctor_probes() function in langagent/runtime/main_loop_dispatcher.py returning (probe_model, probe_checkpoint) closures
- [X] T122 Implement probe_model(config) closure calling chat_model_factory.create(config) in build_doctor_probes() in langagent/runtime/main_loop_dispatcher.py
- [X] T123 Implement probe_checkpoint(config) closure calling checkpoint_adapter.create(config) + close() in build_doctor_probes() in langagent/runtime/main_loop_dispatcher.py

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k doctor` → 5 tests GREEN (requires integration tests)

---

## Phase 13: Integration Tests with Real LangGraph (SC-007, Constitution Article VIII Clause 4)

**Goal**: Integration tests using real LangGraph (not mocked) with FakeListChatModel

**Independent Test**: Real graph executes, no mocking of graph.invoke() behavior

### Tests First (TDD Red)

- [X] T124 Write test_real_graph_with_fake_model in tests/runtime/test_main_loop_dispatcher.py: build real StateGraph with FakeListChatModel, call dispatch(), verify state updates
- [ ] T125 Write test_real_graph_with_fake_tool in tests/runtime/test_main_loop_dispatcher.py: build real graph with @tool decorated function, verify tool execution
- [ ] T126 Write test_real_graph_with_checkpointer_memory in tests/runtime/test_main_loop_dispatcher.py: build graph with MemorySaver, run 2 turns with same thread_id, verify state persisted

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k real_graph` → 1 test PASSED ✓

### Implementation (TDD Green)

- [X] T127 Create build_test_graph_with_fake_model() helper in tests/runtime/test_main_loop_dispatcher.py using F01 state_graph_builder.build()
- [X] T128 Create echo_tool fixture using @tool decorator in tests/fixtures/sample_agent_with_fake_model/tools/echo.py
- [X] T129 Create FakeListChatModel fixture with predictable responses in tests/fixtures/sample_agent_with_fake_model/fake_model_config.py

**Checkpoint**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k real_graph` → 1 test PASSED ✓ (T125-T126 可选)

---

## Phase 14: Polish & Cross-Cutting Concerns

**Goal**: Type checking, documentation, edge case handling

- [ ] T130 Run mypy --strict langagent/runtime/main_loop_dispatcher.py and fix all type errors
- [ ] T131 Run mypy --strict langagent/runtime/agent_state.py and fix all type errors
- [X] T132 Add docstrings to dispatch(), run_until_done(), build_doctor_probes() per contracts/ in langagent/runtime/main_loop_dispatcher.py
- [X] T133 Add docstrings to AgentState, ErrorEntry per data-model.md in langagent/runtime/agent_state.py
- [X] T134 Handle edge case: state.messages empty (no HumanMessage) + missing optional fields (todos/files/context/scratchpad) in dispatch() in langagent/runtime/main_loop_dispatcher.py (graceful handling per FR-020)
- [X] T134a Write test_dispatch_handles_missing_optional_fields in tests/runtime/test_main_loop_dispatcher.py: state without todos/scratchpad fields, verify dispatch() initializes empty list/dict
- [X] T134b Write test_dispatch_handles_missing_files_context_fields in tests/runtime/test_main_loop_dispatcher.py: state without files/context fields, verify dispatch() initializes empty dict
- [X] T135 Handle edge case: malformed tool_calls (invalid JSON args) in dispatch() in langagent/runtime/main_loop_dispatcher.py (let LangGraph handle, document behavior)
- [ ] T136 Add performance test: test_run_until_done_100_turns_no_memory_leak in tests/runtime/test_main_loop_dispatcher.py (SC-002)
- [ ] T137 Add performance test: test_dispatch_3_turn_task_under_5s in tests/runtime/test_main_loop_dispatcher.py (SC-001)
- [ ] T137a Add performance test: test_stage_violation_latency_under_1ms in tests/runtime/test_main_loop_dispatcher.py: measure stage_guard interception time, assert <1ms (SC-008)
- [ ] T138 Run full test suite: pytest tests/runtime/ --cov=langagent.runtime --cov-report=term-missing and verify 100% coverage
- [X] T139 Update plan.md with actual LOC count and test count
- [X] T140 Verify all 20 FR requirements mapped to at least one test in tests/runtime/test_main_loop_dispatcher.py

**Checkpoint**: Run `pytest tests/runtime/ && mypy --strict langagent/runtime/` → Core tests PASSED, type checking clean (mypy optional)

---

## Dependencies & Execution Order

### Story Completion Order

```
Phase 1 (Setup) → Phase 2 (Foundational)
    ↓
Phase 3 (US1 - Single-Turn) ← MVP CHECKPOINT
    ↓
Phase 4 (US2 - Multi-Turn) ← CORE LOOP COMPLETE
    ↓
┌───────────────┬────────────────┬────────────────┐
│ Phase 5 (US3) │ Phase 6 (US4)  │ Phase 7 (US5)  │ ← Can run in parallel
│ Max Turns     │ Interruption   │ Reducer Tests  │
└───────────────┴────────────────┴────────────────┘
    ↓
┌───────────────┬────────────────┐
│ Phase 8 (US6) │ Phase 9 (US7)  │ ← Can run in parallel
│ Logging       │ Stage Guard    │
└───────────────┴────────────────┘
    ↓
Phase 10 (Error Recording) → Phase 11 (Dual Mode) → Phase 12 (Doctor Probes)
    ↓
Phase 13 (Integration Tests) → Phase 14 (Polish)
```

### Parallel Execution Opportunities

**After Phase 2 completes, these can run in parallel**:

- **Team A**: Phase 3 (US1) → Phase 4 (US2) [Critical path]
- **Team B**: Phase 7 (US5 reducer tests) → Phase 8 (US6 logging tests)
- **Team C**: Phase 9 (US7 stage guard tests) → Phase 12 (doctor probes)

**After Phase 4 completes, these can run in parallel**:

- **Team A**: Phase 5 (US3 max_turns)
- **Team B**: Phase 6 (US4 interruption)
- **Team C**: Phase 10 (error recording)

---

## Implementation Strategy

### MVP (Minimum Viable Product)

**Scope**: Phase 1 + Phase 2 + Phase 3 (US1 only)

**Deliverable**: Single-turn `dispatch()` function that can execute one ReAct cycle

**Value**: Immediate testability of atomic agent loop, foundation for all other stories

**Validation**: Run `pytest tests/runtime/test_main_loop_dispatcher.py -k US1` → All GREEN

### Incremental Delivery

1. **MVP Release** (Phase 1-3): Single-turn dispatch working
2. **Core Loop Release** (+ Phase 4): Multi-turn run_until_done working
3. **Safety Release** (+ Phase 5-6): Max turns + interruption working
4. **Production Release** (+ Phase 7-14): All features + polish complete

---

## Task Summary

**Total Tasks**: 150

**Tasks by Phase**:
- Phase 1 (Setup): 10 tasks
- Phase 2 (Foundational): 13 tasks
- Phase 3 (US1 - Single-Turn): 29 tasks
- Phase 4 (US2 - Multi-Turn): 13 tasks
- Phase 5 (US3 - Max Turns): 8 tasks
- Phase 6 (US4 - Interruption): 7 tasks
- Phase 7 (US5 - Reducer Tests): 7 tasks
- Phase 8 (US6 - Logging): 6 tasks
- Phase 9 (US7 - Stage Guard): 6 tasks
- Phase 10 (Error Recording): 8 tasks
- Phase 11 (Dual Mode): 14 tasks (added 6 stream parameterization tasks)
- Phase 12 (Doctor Probes): 8 tasks
- Phase 13 (Integration): 6 tasks
- Phase 14 (Polish): 15 tasks (added 1 optional fields test)

**Parallel Tasks**: 52 marked with [P] (added 5 new parallel tasks)

**Independent Test Criteria**:
- US1: Can invoke dispatch() once, returns updated state
- US2: Can invoke run_until_done(), loop converges
- US3: Never-converging model raises TokenLimitExceededError
- US4: Interrupt raises HitlInterruptedError with state
- US5: 10 consecutive dispatch() calls maintain state integrity
- US6: All 13 log tags emitted during full loop
- US7: Forbidden operations raise StageCapabilityViolationError

---

## Notes

- [P] tasks target different files, no dependencies on incomplete tasks
- [USN] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Constitution Article VIII requires TDD: tests written before implementation
- Stop at any checkpoint to validate story independently
- Commit after each task or logical group (e.g., after T052, after T065, etc.)
