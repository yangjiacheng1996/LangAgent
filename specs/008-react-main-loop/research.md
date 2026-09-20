# Phase 0: Research & Decisions

**Feature**: ReAct Main Loop Runtime Dispatcher (F08)  
**Date**: 2026-09-20  
**Status**: Completed

---

## 1. LangGraph invoke vs stream modes

### Decision
Implement both `graph.invoke()` and `graph.stream()` with **shared core dispatch logic** plus mode-specific wrappers.

### Rationale
- **Shared logic**: Both modes execute the same graph with the same state updates. Core logic (event emission, log emission, stage guard, exception handling) should not duplicate.
- **Mode-specific wrappers**: 
  - `invoke()` returns final state after graph completes
  - `stream()` yields intermediate states/events as graph progresses
- **Implementation strategy**: 
  - Core `_dispatch_internal(graph, state, mode)` handles common logic
  - Public `dispatch()` calls `_dispatch_internal(mode='invoke')`
  - Future `dispatch_stream()` calls `_dispatch_internal(mode='stream')` and wraps with generator
- **Testing**: All 28+ test cases cover invoke mode; add 5+ stream-specific tests for yield behavior

### Alternatives Considered
- **A: Separate implementations** - Rejected because it doubles maintenance burden and risks behavior drift between modes
- **B: Stream-only with buffering** - Rejected because invoke is simpler for CLI use case and stream adds latency overhead
- **C: Invoke-only, defer stream to F08.1** - Rejected per clarification Q3 answer (both modes required in F08 deliverable)

### References
- LangGraph documentation: `graph.stream()` yields `(node_name, state_update)` tuples
- LangGraph documentation: `graph.invoke()` returns final state directly
- Clarification session 2026-09-20 Q3: "F08 必须同时实现 invoke() 和 stream() 两种模式"

---

## 2. HitlInterruptedError state attachment pattern

### Decision
Custom exception class with **frozen dataclass** containing `state` and `reason` attributes.

```python
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class HitlInterruptedError(Exception):
    """Raised when loop is interrupted by user or guardrail."""
    state: dict[str, Any]  # Current AgentState at interruption
    reason: str            # "keyboard_interrupt" | "guardrail_block" | "tool_approval_required"
    message: str = "Agent execution interrupted"
    
    def __str__(self) -> str:
        return f"{self.message}: {self.reason}"
```

### Rationale
- **Frozen dataclass**: Immutable, mypy-friendly, auto-generates `__init__` and `__repr__`
- **State preservation**: Callers access via `error.state` (simple attribute access)
- **Reason field**: Allows F10 (CLI) vs F11 (eval) to differentiate interrupt types
- **Message field**: Human-readable error for logging/debugging
- **Exit code mapping**: F10 uses reason to decide exit code (130 for keyboard/guardrail, per workflow.md)

### Alternatives Considered
- **A: Dict attribute `error.context`** - Rejected because untyped dict loses mypy type safety
- **B: Separate exception classes** - Rejected because reason string is sufficient; no need for `KeyboardInterruptError`, `GuardrailInterruptError`, etc.
- **C: State in exception args tuple** - Rejected because `error.args[0]` is cryptic and not self-documenting

### References
- Python exception best practices: Prefer named attributes over args tuple
- mypy strict mode: Dataclass fields are statically typed
- Clarification session 2026-09-20 Q5: "dispatch() 抛出 HitlInterruptedError 异常，异常对象携带当前 state"

---

## 3. Structured error recording format

### Decision
**JSON list** of error entries in `state.scratchpad["errors"]`, each entry containing 4 required fields:

```python
ErrorEntry = TypedDict('ErrorEntry', {
    'turn': int,              # Turn number when error occurred (1-indexed)
    'tool': str,              # Tool name (e.g., "echo", "search")
    'error': str,             # Error message (exception.__class__.__name__ + str(exception))
    'timestamp': str,         # ISO8601 UTC timestamp (e.g., "2026-09-20T10:30:45.123456Z")
})

# Example:
state.scratchpad["errors"] = [
    {
        "turn": 3,
        "tool": "echo",
        "error": "TimeoutError: Operation timed out after 5s",
        "timestamp": "2026-09-20T10:30:45.123456Z"
    }
]
```

### Rationale
- **ISO8601 string**: Human-readable, sortable, timezone-aware (always UTC)
- **4 fields minimum**: Sufficient for debugging without bloating state
- **No traceback by default**: Traceback can be >1KB, causes state serialization bloat; log full traceback via F02 logger instead
- **Error format**: `ExceptionClass: message` mirrors Python's default exception repr

### Alternatives Considered
- **A: Unix epoch float** - Rejected because ISO8601 is more human-readable in logs/debugging
- **B: Add traceback field** - Rejected because state serialization should be compact; full traceback goes to logs
- **C: Add tool_args field** - Rejected because args may contain secrets (API keys); safer to omit unless explicitly needed

### References
- ISO8601: `datetime.datetime.utcnow().isoformat() + "Z"`
- Clarification session 2026-09-20 Q4: "结构化列表，含时间戳、工具名、错误消息、轮次"
- Spec FR-016: "record tool execution errors in state.scratchpad["errors"] as structured entries"

---

## 4. Stage guard integration

### Decision
Apply `@cross_cutting_stage_guard_decorator('main_loop')` to **both `dispatch()` and `run_until_done()`** at function level.

```python
from langagent.cross_cutting.stage_guard import stage_guard_decorator

@stage_guard_decorator('main_loop')
def dispatch(graph: CompiledStateGraph, state: AgentState) -> AgentState:
    """Execute one ReAct turn with stage capability boundary enforcement."""
    ...

@stage_guard_decorator('main_loop')
def run_until_done(graph: CompiledStateGraph, state: AgentState, max_turns: int = 30) -> AgentState:
    """Run ReAct loop until convergence with stage capability boundary enforcement."""
    ...
```

### Rationale
- **Function-level decoration**: Cleanest, most Pythonic pattern; decorator wraps entire function body
- **No nested call issues**: `run_until_done()` calls `dispatch()` internally, but each has its own decorator context; blacklist enforcement is idempotent (monkeypatch already active in outer context)
- **Both functions decorated**: Even though `run_until_done` calls `dispatch`, decorating both ensures stage guard is active regardless of entry point (e.g., test calling `dispatch()` directly)
- **Blacklist from F06**: `stage_guard.STAGE_BLACKLIST_TABLE['main_loop']` provides monkeypatch + audit_event blacklists

### Alternatives Considered
- **A: Decorate run_until_done only** - Rejected because direct `dispatch()` calls (e.g., in tests) would bypass stage guard
- **B: Manual context manager** - Rejected because decorator is cleaner and less error-prone
- **C: Conditional decoration based on caller** - Rejected because overly complex and violates clarity principle

### References
- F06 cross_cutting_stage_guard module provides `@stage_guard_decorator`
- architecture_modules.md v2.3.0: stage_guard moved from runtime to cross_cutting layer
- Spec FR-012: "System MUST apply @cross_cutting_stage_guard_decorator('main_loop')"

---

## 5. Dual-channel emission timing

### Decision
**Sequential emission with Event first, then Log**:
1. `protocol_event_bus.publish(event)` - may be async internally
2. `cross_cutting_logger.emit(tag, payload)` - synchronous
3. If Event publish fails, log the failure but still emit Log (don't block observability)

```python
# Pseudo-code pattern
try:
    event_bus.publish(Event(type="tool_call", payload={...}))
except Exception as e:
    logger.emit("la.runtime.main_loop.event_publish_failed", {"error": str(e)})
finally:
    logger.emit("la.lifecycle.run.tool_call", {...})  # Always emit log
```

### Rationale
- **Event first**: Subscribers (metrics_collector, audit_recorder) need event data before log appears
- **Log always emits**: Even if Event bus fails, structured logs must be available for debugging
- **No atomicity requirement**: Event and Log are independent channels; it's acceptable if one succeeds and other fails
- **Failure isolation**: Event bus failure should not crash dispatch loop; log the failure and continue

### Alternatives Considered
- **A: Log first, Event second** - Rejected because metrics_collector may miss timing window if log appears before event
- **B: Atomic dual-emit** - Rejected because too complex and unnecessary; both channels are best-effort telemetry
- **C: Async event + sync log in parallel** - Rejected because adds thread safety complexity without meaningful benefit

### References
- Spec FR-019: "System MUST emit dual-channel signals (Event + Log) simultaneously"
- Spec section 3.5: "F08 在 main_loop 阶段同时通过 Event 总线 + 结构化日志双通道发射信号"
- F03 protocol_event_bus: publish() may be async internally but returns immediately

---

## 6. LangGraph Best Practices (consolidated)

### graph.invoke() vs graph.stream()
- **invoke()**: Blocking call, returns final state only
  ```python
  final_state = graph.invoke(initial_state, config={"configurable": {"thread_id": "x"}})
  ```
- **stream()**: Generator, yields `(node_name, state_snapshot)` tuples after each node execution
  ```python
  for node_name, state_snapshot in graph.stream(initial_state, config={...}):
      # Process intermediate state
  ```
- **Common config keys**: `thread_id` (for checkpointer), `recursion_limit` (max graph depth)

### GraphInterrupt handling
- **When raised**: Tool with `requires_approval=True` or F04 guardrail calls `interrupt()`
- **Catching**: Use `try...except GraphInterrupt` at dispatch level
- **State preservation**: LangGraph automatically checkpoints state before raising GraphInterrupt
- **Resumption**: Call `graph.invoke(state, config={...})` again to resume (F08 does NOT handle resumption; F10 CLI would need to)

### Checkpointer usage
- **F08 responsibility**: NONE - checkpointer is configured in F01 graph_compose stage
- **F08 must NOT**: Call `checkpointer.save()` or `checkpointer.load()` manually
- **LangGraph handles automatically**: State saved after each node execution if checkpointer configured

### References
- LangGraph documentation: `harness/LangGraph_doc/` per constitution Article II clause 4
- Constitution Article VI clause 6: "Interrupt 必须基于 LangGraph 的 interrupt() 机制"

---

## 7. Python Exception Design (consolidated)

### Custom exception with state
- **Pattern**: Frozen dataclass inheriting from Exception
- **Type hints**: Use `dict[str, Any]` for AgentState (TypedDict would require import cycle)
- **mypy compliance**: Dataclass fields are fully typed, `--strict` passes
- **Serialization**: If exception needs to cross process boundaries (unlikely for F08), use `asdict(error)` from dataclasses module

### Best practices
- **Immutable**: Use `frozen=True` to prevent accidental mutation
- **Self-documenting**: Named attributes (`error.state`, `error.reason`) over positional args
- **__str__ override**: Provide human-readable representation for logs

### References
- PEP 8: Exception names should end in "Error"
- mypy documentation: Dataclasses are statically typed

---

## 8. pytest Patterns for Integration Tests (consolidated)

### Testing real LangGraph without mocking
- **Use FakeListChatModel**: LangChain's built-in fake for deterministic responses
  ```python
  from langchain_core.language_models.fake import FakeListChatModel
  
  fake_model = FakeListChatModel(responses=[
      AIMessage(content="Let me use the echo tool", tool_calls=[{...}]),
      AIMessage(content="Final answer: done")
  ])
  ```
- **Use real BaseTool**: Define minimal tool with `@tool` decorator or BaseTool subclass
  ```python
  from langchain_core.tools import tool
  
  @tool
  def echo(text: str) -> str:
      """Echo the input text."""
      return text
  ```
- **Build real graph**: Call F01 `state_graph_builder.build()` with fake model + real tools
- **No mocking graph.invoke()**: Let LangGraph execute real nodes and edges

### Fixture organization
- **Location**: `tests/fixtures/sample_agent_with_fake_model/`
- **Contents**: Minimal agent directory with fake model config
- **Reusability**: Multiple test files can import same fixture

### References
- Constitution Article VIII clause 4: "不可 mock LangGraph 行为：图必须真实跑"
- LangChain documentation: `FakeListChatModel` in `langchain_core.language_models.fake`

---

## Summary of Decisions

| Research Topic | Decision | Impact on Implementation |
|----------------|----------|--------------------------|
| Invoke vs Stream | Shared core + mode wrappers | Add `_dispatch_internal()` private function, public `dispatch()` for invoke, future `dispatch_stream()` for stream |
| Exception Design | Frozen dataclass with state/reason | Define `HitlInterruptedError` class in `main_loop_dispatcher.py` |
| Error Structure | 4-field JSON entries (turn/tool/error/timestamp) | Add error recording logic in dispatch loop try-except |
| Stage Guard | Decorate both dispatch + run_until_done | Import from cross_cutting.stage_guard, apply @decorator |
| Dual-channel | Event first, Log always | Wrap event publish in try-except, emit log in finally block |

**All NEEDS CLARIFICATION items resolved.** Proceed to Phase 1 design artifacts.
