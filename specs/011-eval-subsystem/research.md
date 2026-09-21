# Research: Eval Subsystem (F11)

**Feature**: 011-eval-subsystem  
**Date**: 2026-09-21  
**Phase**: 0 (Outline & Research)

## Purpose

Resolve technical unknowns and establish implementation patterns for F11 eval subsystem before design phase. All NEEDS CLARIFICATION items from Technical Context are addressed below.

---

## Research Item 1: Grader Implementation Patterns

### Question
What are best practices for implementing pluggable grader functions with consistent interfaces across 5 different matching strategies?

### Investigation
- **LangChain Evaluator Reference**: LangChain `langchain.evaluation` module uses protocol-based evaluators with `evaluate_strings()` method
- **Pattern Studied**: Strategy pattern with registry dictionary for runtime selection
- **Interface Contract**: All graders expose `grade(actual: str, expected: str | list[str] | dict, **kwargs) -> bool`

### Decision
**Use registry-based strategy pattern with uniform `grade()` interface**

### Rationale
- Enables runtime grader selection based on `EvalTaskSpec.grader` field
- Type-safe with literal enum for grader names
- Extensible: new graders register in `GRADER_REGISTRY` dict without modifying runner
- Testable: each grader is independent pure function

### Implementation Approach
```python
# langagent/eval/graders/__init__.py
from typing import Callable, Any

GraderFunction = Callable[[str, str | list[str] | dict[str, Any]], bool]

GRADER_REGISTRY: dict[str, GraderFunction] = {
    "exact_match": exact_match.grade,
    "contains": contains.grade,
    "regex": regex.grade,
    "llm_judge": llm_judge.grade,
    "tool_call_match": tool_call_match.grade,
}
```

### Alternatives Considered
- **Class-based inheritance**: Rejected (unnecessary OOP overhead for stateless functions)
- **Plugin discovery**: Rejected (v1 only supports 5 built-in graders)

---

## Research Item 2: Task Timeout Mechanism

### Question
How to implement per-task timeout that terminates F08 main_loop execution within 2s of threshold?

### Investigation
- **Python stdlib**: `signal.alarm()` (Unix-only), `threading.Timer` (cooperative), `asyncio.wait_for()` (async only)
- **LangGraph Feature**: CompiledStateGraph has no built-in timeout parameter
- **Pattern Studied**: Wrapper with thread-based timeout + exception handling

### Decision
**Use `concurrent.futures.ThreadPoolExecutor` with timeout parameter**

### Rationale
- Cross-platform (works on Windows unlike signal.alarm)
- Returns control within specified timeout
- Raises `concurrent.futures.TimeoutError` catchable by runner
- Does not require graph modification

### Implementation Approach
```python
from concurrent.futures import ThreadPoolExecutor, TimeoutError

def _run_one_task(spec: EvalTaskSpec, graph, state, config):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            main_loop_dispatcher.run_until_done, 
            graph, state, config
        )
        try:
            final_state = future.result(timeout=spec.timeout_s)
        except TimeoutError:
            raise EvalTimeoutError(f"Task {spec.task_id} exceeded {spec.timeout_s}s")
```

### Alternatives Considered
- **signal.alarm()**: Rejected (Unix-only, breaks Windows compatibility)
- **asyncio.wait_for()**: Rejected (F08 is synchronous, forcing async adds complexity)

---

## Research Item 3: LLM Judge Independent Model Instance

### Question
How to create independent BaseChatModel instance for llm_judge to avoid judge bias?

### Investigation
- **LangChain Pattern**: Each `ChatOpenAI()` / `ChatAnthropic()` constructor creates new HTTP client
- **Bias Risk**: Reusing agent's model instance shares conversation state/cache
- **F01 API**: `chat_model_factory.create(config)` returns fresh instance per call

### Decision
**Call `chat_model_factory.create(config)` once per eval run, not per task**

### Rationale
- Independent from agent's model instance (no shared state)
- Reuses same judge model across all llm_judge tasks (performance optimization)
- Config injected by F10 dispatch contains judge model credentials

### Implementation Approach
```python
# langagent/eval/runner.py
def run(agent_dir: str, *, config: RuntimeConfig, args: dict[str, Any]):
    # Create judge model once per run
    judge_model = chat_model_factory.create(config) if has_llm_judge_tasks else None
    
    for task in tasks:
        if task.grader == "llm_judge":
            result = llm_judge.grade(actual, task.expected, judge_model=judge_model)
```

### Alternatives Considered
- **Reuse agent model**: Rejected (judge bias risk per spec §五.4)
- **Create per task**: Rejected (unnecessary overhead, HTTP client warmup cost)

---

## Research Item 4: Exit Code Worst-Of Strategy

### Question
What algorithm aggregates per-task exit codes into single final exit code?

### Investigation
- **Unix Convention**: Exit code 0 = success, >0 = failure (higher = more severe)
- **Precedence**: Signal exits (130 SIGINT) > software (70) > config (78) > data (65) > usage (64) > I/O (4) > generic (1)
- **Spec Requirement**: "worst_of(all_failure_exit_codes)" per spec §3.2

### Decision
**Use `max(all_task_exit_codes + [0])` as final exit code**

### Rationale
- Simple, deterministic, preserves highest severity
- `+ [0]` ensures all-pass returns 0
- Aligns with workflow.md exit code severity ordering

### Implementation Approach
```python
# langagent/eval/runner.py
def run(agent_dir, *, config, args):
    task_exit_codes = []
    for task in tasks:
        try:
            result = _run_one_task(task, agent, graph, config)
            task_exit_codes.append(result.exit_code)
        except Exception as e:
            task_exit_codes.append(map_exception_to_exit_code(e))
    
    exit_code = max(task_exit_codes + [0])
    return EvalRunResult(eval_report, final_state, exit_code)
```

### Alternatives Considered
- **First failure wins**: Rejected (loses information about later severe failures)
- **Count-based threshold**: Rejected (doesn't capture failure severity)

---

## Research Item 5: Tool Call Matching Algorithm

### Question
How to match `expected: dict` against `AIMessage.tool_calls` for tool_call_match grader?

### Investigation
- **LangChain AIMessage Schema**: `tool_calls: list[dict]` with keys `name`, `args`, `id`
- **Matching Requirement**: Match both tool name and args dict (spec §3.3)
- **Partial Match**: Subset match sufficient (expected args ⊆ actual args)

### Decision
**Use tool name exact match + args dict subset comparison**

### Rationale
- Flexible: allows grader to specify only critical args, ignore incidental fields
- Matches LangChain tool_calls schema directly
- Handles list of tool_calls (multi-tool scenarios)

### Implementation Approach
```python
# langagent/eval/graders/tool_call_match.py
def grade(expected: dict, actual_ai_message: AIMessage) -> bool:
    expected_tool_id = expected["tool_id"]
    expected_args = expected["args"]
    
    for call in actual_ai_message.tool_calls:
        if call["name"] == expected_tool_id:
            # Check if expected args are subset of actual args
            if all(call["args"].get(k) == v for k, v in expected_args.items()):
                return True
    return False
```

### Alternatives Considered
- **Exact match**: Rejected (too strict, fails on harmless extra args)
- **JSON schema validation**: Rejected (overkill for v1, deferred to grader_extensibility)

---

## Research Item 6: Event Bus Integration

### Question
How does F11 publish `eval_task_started`/`eval_task_done` events to F03 protocol_event_bus?

### Investigation
- **F03 API**: `protocol_event_bus.publish(event_type: str, payload: dict)`
- **F02 Subscription**: metrics_collector subscribes to these 2 event types
- **Spec Requirement**: Per spec §3.1, F11 emits events for task-level latency tracking

### Decision
**Call `event_bus.publish()` at task boundaries with latency payload**

### Rationale
- Decoupled: F11 publishes, F02 subscribes (no direct dependency)
- Payload includes task_id, passed/failed, latency_ms for metrics
- Aligns with workflow.md event lifecycle

### Implementation Approach
```python
# langagent/eval/runner.py
from langagent.protocol.event_bus import publish

def _run_one_task(spec, agent, graph, config):
    publish("eval_task_started", {"task_id": spec.task_id, "timestamp": time.time()})
    
    start = time.perf_counter()
    try:
        final_state = main_loop_dispatcher.run_until_done(graph, state, config)
        passed = grade_output(final_state, spec)
    finally:
        latency_ms = (time.perf_counter() - start) * 1000
        publish("eval_task_done", {
            "task_id": spec.task_id,
            "passed": passed,
            "latency_ms": latency_ms,
        })
```

### Alternatives Considered
- **Direct F02 call**: Rejected (violates layer separation)
- **Return events in result**: Rejected (breaks real-time metrics collection)

---

## Research Item 7: Report Persistence Path Resolution

### Question
Where should `~/.local/share/langagent/reports/<agent-name>-<timestamp>.json` resolve on different platforms?

### Investigation
- **Linux**: `~/.local/share/` (XDG Base Directory spec)
- **macOS**: `~/Library/Application Support/` preferred over `~/.local/share/`
- **Windows**: `%LOCALAPPDATA%` (e.g., `C:\Users\Alice\AppData\Local\`)
- **Python stdlib**: `pathlib.Path.home()` resolves `~` cross-platform

### Decision
**Use platform-specific user data directory via `platformdirs` library**

### Rationale
- Follows OS conventions (XDG on Linux, Application Support on macOS, AppData on Windows)
- `platformdirs.user_data_dir("langagent")` returns correct path per platform
- Already used by LangChain for cache directories

### Implementation Approach
```python
# langagent/runtime/exit_handler.py
from platformdirs import user_data_dir
from pathlib import Path

def cleanup(..., eval_report: EvalReport | None):
    if eval_report:
        reports_dir = Path(user_data_dir("langagent")) / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        agent_name = Path(eval_report.agent_dir).name
        report_path = reports_dir / f"{agent_name}-{timestamp}.json"
        
        report_path.write_text(eval_report.model_dump_json(indent=2))
```

### Alternatives Considered
- **Hard-code ~/.local/share**: Rejected (breaks macOS/Windows conventions)
- **CWD-relative reports/**: Rejected (pollutes agent directory)

---

## Summary of Decisions

| Research Item | Decision | Key Rationale |
|---------------|----------|---------------|
| Grader Patterns | Registry-based strategy pattern | Runtime selection, extensible, testable |
| Task Timeout | ThreadPoolExecutor with timeout | Cross-platform, non-invasive to graph |
| LLM Judge Model | Independent instance per run | Avoid bias, reuse across tasks |
| Exit Code Aggregation | max(all_exit_codes + [0]) | Preserves highest severity |
| Tool Call Matching | Name + args subset match | Flexible, matches LangChain schema |
| Event Bus Integration | Publish at task boundaries | Decoupled, real-time metrics |
| Report Persistence | platformdirs.user_data_dir() | Cross-platform OS conventions |

**All NEEDS CLARIFICATION items resolved**. Ready for Phase 1 design.
