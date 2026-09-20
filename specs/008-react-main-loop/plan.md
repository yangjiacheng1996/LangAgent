# Implementation Plan: ReAct Main Loop Runtime Dispatcher

**Branch**: `008-react-main-loop` | **Date**: 2026-09-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-react-main-loop/spec.md`

**Constitutional Alignment**: Article XV (Top-Level Design Primacy), Article VI (Agent Loop and State), Article VIII (TDD Rigidity), Article IX (Quality Diagnostics)

## Summary

Implement the runtime layer stage 5 `main_loop` dispatcher that drives LangGraph `CompiledStateGraph` to execute the ReAct loop (reasoning → tools → observation) until task completion, user interruption, or max_turns termination. The dispatcher provides two core APIs: `dispatch()` for single-turn execution and `run_until_done()` for complete loop execution. It must support both `graph.invoke()` and `graph.stream()` invocation modes, emit dual-channel telemetry (Event + Log), enforce stage capability boundaries via `@stage_guard_decorator`, and handle interruptions by raising `HitlInterruptedError` with preserved state. Tool errors are recorded as structured entries in `state.scratchpad["errors"]` without early termination, relying on max_turns for natural loop completion.

## Technical Context

**Language/Version**: Python 3.11+ (per `pyproject.toml` requires-python constraint in constitution Article II)

**Primary Dependencies**: 
- LangGraph (via `langagent.primitives.langchain_types` re-exports) - graph execution
- LangChain Core (via primitives re-exports) - BaseMessage, add_messages, interrupt primitives
- F01 primitives layer (state_graph_builder, langchain_types, state_reducers, chat_model_factory, checkpoint_adapter)
- F02 cross_cutting_logger (structured logging with 12 tags)
- F03 protocol_event_bus (Event publishing for tool_call/tool_result/model_response)
- F04 cross_cutting_guardrail_middleware (interrupts via GraphInterrupt)
- F06 cross_cutting_stage_guard (stage capability boundary enforcement)

**Storage**: 
- In-memory AgentState TypedDict (no direct persistence - checkpointer handled by LangGraph)
- Structured logs written to `~/.local/share/langagent/logs/<run-id>.jsonl` (F02 responsibility)
- MetricsSnapshot in-memory (F02 cross_cutting_metrics_collector)

**Testing**: pytest + pytest-asyncio
- Unit tests: ≥28 test cases for dispatch/run_until_done/reducers/events/logs (constitution Article VIII - TDD rigidity)
- Integration tests: Real LangGraph with FakeListChatModel and real BaseTool (no mocking graph behavior per constitution Article VIII clause 4)
- Reducer tests: 5 AgentState fields across 10+ consecutive dispatch() calls
- Stage guard tests: Verify StageCapabilityViolationError on blacklisted operations

**Target Platform**: Linux server (primary), macOS development workstations (secondary)

**Project Type**: CLI/library hybrid (LangAgent is a packaged agent runtime, not a user-programmable SDK per constitution Article I clause 1)

**Performance Goals**: 
- 3-turn task converges in <5 seconds on local vLLM (Qwen3.8-27B) - SC-001
- 100-turn stress test without memory leaks - SC-002
- Stage violation detection <1ms - SC-008

**Constraints**: 
- No direct imports of `langchain` or `langgraph` packages (must use `primitives.langchain_types` re-exports per constitution Article VI clause 2 + Article VIII clause 4)
- Main_loop stage cannot re-load directories, re-parse config, or instantiate models (stage capability boundary per workflow.md stage 5)
- Must emit 12 log tags + observe 1 from F04 (13 total) per workflow.md
- Dual-channel emission (Event + Log) mandatory for tool_call/tool_result/model_response

**Scale/Scope**: 
- Single main_loop_dispatcher module (~340 LOC estimated per architecture_modules.md)
- 143 tasks total (setup + foundational + 7 user stories + specialized features + polish)
- 5 AgentState fields with 3 unique reducer functions (from primitives layer)
- 2 invocation modes (invoke + stream) both required per clarification

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Article I: Project Identity & Boundaries

✅ **PASS** - F08 is an internal runtime module, not exposed as public API. Users interact via `langagent run` CLI, not by importing F08 directly.

### Article II: Technology Stack & Dependency Scope

✅ **PASS** - All dependencies (LangGraph, LangChain) are from approved stack. No new third-party libraries introduced.

### Article III: LangSmith Separation Principle

✅ **PASS** - No LangSmith dependencies. Tracing handled by F02 logger + F03 event_bus (self-hosted).

### Article IV: Model Abstraction Layer

✅ **PASS** - F08 does not instantiate models. Models provided by RuntimeConfig.model (populated by F01 in model_adapt stage). `build_doctor_probes()` imports `chat_model_factory.create()` via hardcoded exception per architecture_modules.md v2.4.0 (2 hardcoded edges: `runtime_main_loop_dispatcher → primitives_chat_model_factory/checkpoint_adapter`).

### Article V: Agent Directory Contract

✅ **PASS** - F08 does not modify agent directory. LoadedAgent provided by F02 dir_load stage.

### Article VI: Agent Loop & State Design

✅ **PASS** - Core implementation of Article VI:
- Main loop is LangGraph-driven (dispatch invokes CompiledStateGraph)
- AgentState is self-defined 5-field TypedDict (not LangGraph MessagesState)
- Reducers: `add_messages` (LangGraph), `replace_with_merge`/`merge_dict`/`overwrite_or_merge` (from primitives.state_reducers)
- Nodes: model_call/tools_execute/should_continue (provided by F01 graph_compose)
- Edges: LangGraph native conditional edges (F01 responsibility)
- HITL: LangGraph `interrupt()` mechanism (GraphInterrupt caught, HitlInterruptedError raised with state)

### Article VIII: TDD Rigidity

✅ **PASS** - Feature includes ≥28 test cases written before implementation (Red-Green-Refactor). Integration tests use real LangGraph + FakeListChatModel (no mocking graph behavior per clause 4).

### Article IX: Quality Diagnostics Capability Matrix

✅ **PASS** - F08 implements Tracing/Monitoring/Guardrails sub-capabilities:
- **Tracing**: Emits 12 structured log tags via F02 logger (la.lifecycle.run.* + la.runtime.main_loop.*)
- **Monitoring**: Publishes 3 Event types via F03 event_bus (tool_call/tool_result/model_response) for F02 metrics_collector subscription
- **Guardrails**: Cooperates with F04 guardrail_middleware (catches GraphInterrupt, converts to HitlInterruptedError)

### Article X: Security & Privacy

✅ **PASS** - F08 does not transmit data externally. Stage guard prevents .env re-reading during main_loop.

### Article XI: Packaging & Distribution

✅ **PASS** - F08 is an internal module packaged with `langagent` binary. No separate distribution.

### Article XII: Configuration & Observability Contract

✅ **PASS** - F08 emits startup logs (la.lifecycle.run.start, la.runtime.main_loop.start) with turn counts, does not log secrets.

### Article XIII: Prohibited Items (Hard No)

✅ **PASS** - No LangSmith dependencies, no hardcoded API keys, no direct provider SDK calls, TDD enforced.

### Article XV: Top-Level Design Primacy

✅ **PASS** - Plan references workflow.md (stage 5 main_loop), architecture_modules.md (mod-runtime-main-loop-dispatcher), module_schemas.md (schema-agent-state). Alignment checklist in spec Constitutional Alignment section.

**Gate Result**: ✅ ALL CHECKS PASS - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/008-react-main-loop/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output (decisions on invoke vs stream, error structure, interrupt handling)
├── data-model.md        # Phase 1 output (AgentState, HitlInterruptedError, MetricsSnapshot)
├── quickstart.md        # Phase 1 output (validation scenarios)
├── contracts/           # Phase 1 output (dispatch/run_until_done/build_doctor_probes API contracts)
│   ├── dispatch.md
│   ├── run_until_done.md
│   └── build_doctor_probes.md
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
langagent/
├── runtime/
│   ├── main_loop_dispatcher.py       # F08 core module (dispatch, run_until_done, build_doctor_probes)
│   ├── agent_state.py                # AgentState TypedDict (imports reducers from primitives)
│   ├── config_resolver.py            # F03 (existing, dependency)
│   ├── dir_loader.py                 # F02 (existing, dependency)
│   └── exit_handler.py               # F06 (existing, dependency)
│
├── primitives/
│   ├── langchain_types.py            # F01 (existing, re-exports BaseMessage, add_messages, interrupt)
│   ├── state_reducers.py             # F01 (existing, provides replace_with_merge, merge_dict, overwrite_or_merge)
│   ├── state_graph_builder.py        # F01 (existing, provides CompiledStateGraph)
│   ├── chat_model_factory.py         # F01 (existing, used by build_doctor_probes)
│   └── checkpoint_adapter.py         # F01 (existing, used by build_doctor_probes)
│
├── cross_cutting/
│   ├── logger.py                     # F02 (existing, provides emit() + ALLOWED_TAGS)
│   ├── stage_guard.py                # F06 (existing, provides @stage_guard_decorator + blacklist)
│   ├── metrics_collector.py          # F02 (existing, subscribes to Event bus)
│   └── guardrail_middleware.py       # F04 (existing, raises GraphInterrupt)
│
└── protocol/
    └── event_bus.py                  # F03 (existing, provides publish/subscribe)

tests/
├── runtime/
│   ├── test_main_loop_dispatcher.py  # ≥28 unit + integration tests
│   └── test_agent_state_reducers.py  # 5 reducer tests (may already exist in primitives tests)
│
└── fixtures/
    └── sample_agent_with_fake_model/ # FakeListChatModel fixture for integration tests
```

**Structure Decision**: Single project structure (Option 1). LangAgent is a monolithic Python package with 5 layers (cli/runtime/protocol/cross_cutting/primitives per architecture_modules.md). F08 adds 1 module to the runtime layer (`main_loop_dispatcher.py`) plus 1 schema file (`agent_state.py` - though AgentState may already be partially defined; F08 ensures 5-field TypedDict is authoritative). Tests follow `tests/runtime/` hierarchy matching source structure.

## Complexity Tracking

> No constitution violations requiring justification. Gate checks all passed.

---

## Phase 0: Research & Decisions

### Research Tasks

1. **LangGraph invoke vs stream modes**
   - Decision needed: Implementation strategy for dual-mode support
   - Research question: How does `graph.stream()` differ from `graph.invoke()` in state handling and event emission?
   - Research question: Can both modes share the same dispatch() core logic, or do they require separate code paths?

2. **HitlInterruptedError state attachment pattern**
   - Decision needed: Exception design pattern for carrying AgentState
   - Research question: Best practice for exception attributes in Python (dataclass vs dict vs custom property)?
   - Research question: How should F10/F11 callers access error.state (direct attribute or getter method)?

3. **Structured error recording format**
   - Decision needed: Exact JSON schema for scratchpad["errors"] entries
   - Research question: Should timestamp be ISO8601 string or Unix epoch float?
   - Research question: Should we include additional fields (traceback, tool args) for debugging?

4. **Stage guard integration**
   - Decision needed: How to apply @stage_guard_decorator to dispatch/run_until_done
   - Research question: Does decorator apply to entire function or specific code blocks?
   - Research question: How to handle nested calls (dispatch called within run_until_done)?

5. **Dual-channel emission timing**
   - Decision needed: Order of Event publish vs Log emit (simultaneous or sequential?)
   - Research question: If event bus is async and logger is sync, how to ensure atomicity?
   - Research question: Should failed event publish block log emit or vice versa?

### Best Practices Tasks

1. **LangGraph best practices**
   - Find: Official LangGraph patterns for graph.invoke() vs graph.stream()
   - Find: LangGraph error handling recommendations for GraphInterrupt
   - Find: LangGraph checkpointer usage patterns (what F08 should NOT do)

2. **Python exception design**
   - Find: Best practices for custom exception classes with state preservation
   - Find: Type hints for exception attributes (mypy --strict compliance)

3. **pytest patterns for integration tests**
   - Find: Patterns for testing real LangGraph without mocking (per constitution Article VIII clause 4)
   - Find: How to use FakeListChatModel with real CompiledStateGraph

---

## Phase 1 Outputs

Phase 1 will generate:
- `research.md` - Consolidation of research findings with decisions + rationale
- `data-model.md` - AgentState schema, HitlInterruptedError exception class, MetricsSnapshot integration
- `contracts/dispatch.md` - dispatch() API contract (signature, parameters, return value, exceptions, side effects)
- `contracts/run_until_done.md` - run_until_done() API contract
- `contracts/build_doctor_probes.md` - build_doctor_probes() API contract
- `quickstart.md` - Validation scenarios (how to run single-turn test, multi-turn test, interrupt test)

---

## Notes

- **Clarifications applied**: 5 decisions from 2026-09-20 clarification session integrated (error recovery strategy, warning threshold, stream mode requirement, error data structure, interrupt return behavior)
- **Dependency on F01**: F08 cannot proceed until F01 primitives layer is complete (state_graph_builder, langchain_types, state_reducers all required)
- **Dependency on F02/F03/F04/F06**: Cross-cutting layers must be functional for event/log emission and stage guard enforcement
- **Test data requirements**: Need fixtures with FakeListChatModel that produces predictable tool_calls sequence for deterministic testing
- **Mypy strict compliance**: All type hints must pass `mypy --strict` (per constitution Article VIII and spec deliverable checklist)
