# Data Model: Eval Subsystem (F11)

**Feature**: 011-eval-subsystem  
**Date**: 2026-09-21  
**Phase**: 1 (Design & Contracts)

## Purpose

Define all data entities, validation rules, and state transitions for the eval subsystem. These schemas align with `harness/top_level_design/module_schemas.md` specifications.

---

## Entity 1: EvalTaskSpec

### Description
A single evaluation task specification loaded from `<agent-dir>/evals/*.yaml`. Defines input, expected output, grading method, and timeout.

### Fields

| Field | Type | Required | Default | Validation Rules |
|-------|------|----------|---------|------------------|
| `task_id` | `str` | Yes | — | Non-empty, alphanumeric + underscore/hyphen |
| `input` | `str` | Yes | — | Non-empty string, agent input prompt |
| `expected` | `str \| list[str] \| dict[str, Any] \| None` | No | `None` | Type must match grader requirements |
| `grader` | `Literal['exact_match', 'contains', 'regex', 'llm_judge', 'tool_call_match']` | No | `'exact_match'` | Must be one of 5 valid values |
| `timeout_s` | `int` | No | `60` | ≥1 (Pydantic `Field(ge=1)`) |
| `metadata` | `dict[str, Any]` | No | `{}` | Arbitrary user metadata |
| `grader_extensibility` | `list[str]` | No | `[]` | Future grader extensions (v1 unused) |
| `case_sensitive` | `bool` | No | `True` | Controls case matching for contains/regex graders |

### Validation Rules

1. **task_id uniqueness**: Loader must detect duplicate task_ids across YAML files
2. **grader-expected type alignment**: 
   - `tool_call_match` requires `expected: dict` (enforced by `@field_validator`)
   - Other graders accept `str | list[str]`
3. **grader-case_sensitive alignment**:
   - `exact_match` + `case_sensitive=false` combination is INVALID (rejected by `@field_validator`)
   - Only `contains` and `regex` graders support `case_sensitive` parameter
4. **timeout range**: Must be ≥1 second (Pydantic constraint)
5. **metadata immutability**: frozen=True after load

### Pydantic Schema

```python
from pydantic import BaseModel, Field, field_validator
from typing import Any, Literal

class EvalTaskSpec(BaseModel, frozen=True):
    model_config = {"frozen": True}
    
    task_id: str
    input: str
    expected: str | list[str] | dict[str, Any] | None = None
    grader: Literal['exact_match', 'contains', 'regex', 'llm_judge', 'tool_call_match'] = 'exact_match'
    timeout_s: int = Field(default=60, ge=1)
    metadata: dict[str, Any] = {}
    grader_extensibility: list[str] = []
    case_sensitive: bool = True
    
    @field_validator('expected')
    @classmethod
    def validate_expected_by_grader(cls, v, info):
        grader = info.data.get('grader')
        if grader == 'tool_call_match' and v is not None and not isinstance(v, dict):
            raise ValueError(
                f"tool_call_match grader requires expected as dict (got {type(v).__name__})"
            )
        return v
    
    @field_validator('case_sensitive')
    @classmethod
    def validate_case_sensitive_by_grader(cls, v, info):
        grader = info.data.get('grader')
        if grader == 'exact_match' and v is False:
            raise ValueError(
                f"exact_match grader does not support case_sensitive=false (always case-sensitive)"
            )
        return v
```

### State Transitions
- **Created**: Loaded from YAML by task_loader
- **Validated**: Pydantic validation passes
- **Executed**: Runner calls _run_one_task()
- **Graded**: Grader returns bool result
- *(Immutable: no state mutations after creation)*

### Related Schemas
- Produces: `TaskResult` (internal runner type)
- References: `EvalReport.task_results` (aggregated)

---

## Entity 2: TaskResult

### Description
Internal runner entity capturing the outcome of a single task execution. Not persisted to disk (aggregated into EvalReport).

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_id` | `str` | Yes | References EvalTaskSpec.task_id |
| `passed` | `bool` | Yes | Grader result (True=pass, False=fail) |
| `actual_output` | `str` | Yes | Agent's final output (extracted from AIMessage) |
| `expected_output` | `str \| list[str] \| dict[str, Any] \| None` | Yes | Original expected value from EvalTaskSpec |
| `grader_used` | `str` | Yes | Grader name that evaluated this task |
| `latency_ms` | `float` | Yes | Task execution time in milliseconds |
| `exit_code` | `int` | Yes | Task-level exit code (0=success, >0=failure) |
| `error_message` | `str \| None` | No | Error message if task crashed |
| `token_usage` | `dict[str, dict[str, int]]` | Yes | Per-model token counts: `{model_name: {input: N, output: M}}` |

### Validation Rules

1. **latency_ms**: Must be ≥0
2. **exit_code**: Standard Unix codes (0, 1, 4, 64, 65, 66, 70, 78, 130)
3. **passed/error_message correlation**: If `error_message` is not None, `passed` must be False
4. **token_usage**: Keys must be valid model identifiers
5. **grader_used**: Must match one of 5 valid grader names

### Pydantic Schema

```python
from pydantic import BaseModel, Field
from typing import Any, Optional

class TaskResult(BaseModel, frozen=True):
    model_config = {"frozen": True}
    
    task_id: str
    passed: bool
    actual_output: str
    expected_output: str | list[str] | dict[str, Any] | None
    grader_used: str
    latency_ms: float = Field(ge=0.0)
    exit_code: int
    error_message: Optional[str] = None
    token_usage: dict[str, dict[str, int]]
```

### State Transitions
- **Executing**: _run_one_task() in progress
- **Completed**: Grader returned bool
- **Failed**: Exception caught, error field populated
- **Aggregated**: Consumed by report_aggregator

### Related Schemas
- Produced by: `eval.runner._run_one_task()`
- Consumed by: `eval.report_aggregator.aggregate()`

---

## Entity 3: EvalReport

### Description
Aggregated evaluation report containing pass rate, latency percentiles, token usage, and cost estimates. Persisted to `~/.local/share/langagent/reports/<agent-name>-<timestamp>.json`.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `report_id` | `str` | Yes | UUID v4 unique identifier |
| `generated_at` | `datetime` | Yes | Report generation timestamp |
| `agent_dir` | `str` | Yes | Absolute path to agent directory |
| `task_results` | `list[dict]` | Yes | TaskResult serialized as dicts |
| `pass_rate` | `float` | Yes | Passed tasks / total tasks (0.0-1.0) |
| `p50_latency_ms` | `float` | Yes | Median task latency |
| `p95_latency_ms` | `float` | Yes | 95th percentile latency |
| `token_usage` | `dict[str, dict[str, int]]` | Yes | Aggregated by model: `{model: {input: N, output: M}}` |
| `cost_usd` | `float` | Yes | Estimated cost (model pricing × token usage) |

### Validation Rules

1. **pass_rate**: 0.0 ≤ pass_rate ≤ 1.0
2. **p95 ≥ p50**: 95th percentile must be ≥ median
3. **cost_usd**: ≥0 (computed from token_usage)
4. **task_results**: Non-empty if any tasks executed

### Pydantic Schema

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any

class EvalReport(BaseModel, frozen=True):
    model_config = {"frozen": True}
    
    report_id: str
    generated_at: datetime
    agent_dir: str
    task_results: list[dict[str, Any]]
    pass_rate: float = Field(ge=0.0, le=1.0)
    p50_latency_ms: float = Field(ge=0.0)
    p95_latency_ms: float = Field(ge=0.0)
    token_usage: dict[str, dict[str, int]]
    cost_usd: float = Field(ge=0.0)
```

### State Transitions
- **Aggregating**: report_aggregator processing TaskResults
- **Generated**: Frozen EvalReport instance created
- **Returned**: Wrapped in EvalRunResult by runner
- **Persisted**: Written to disk by F09 exit_handler.cleanup()

### Related Schemas
- Produced by: `eval.report_aggregator.aggregate()`
- Consumed by: `EvalRunResult.eval_report` field
- Persisted by: `runtime.exit_handler.cleanup()`

---

## Entity 4: EvalRunResult

### Description
Runner's return value wrapping EvalReport + final AgentState + exit code. Not persisted (EvalReport persisted separately).

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `eval_report` | `EvalReport` | Yes | Aggregated report (see Entity 3) |
| `final_state` | `AgentState` | Yes | Last task's final state (for cleanup) |
| `exit_code` | `int` | Yes | max(all_task_exit_codes + [0]) |

### Validation Rules

1. **exit_code**: 0 if all tasks passed, >0 otherwise
2. **final_state**: Valid AgentState with 5 required fields
3. **eval_report.pass_rate**: Correlates with exit_code (0 → pass_rate=1.0)

### Dataclass Schema

```python
from dataclasses import dataclass
from langagent.runtime.agent_state import AgentState
from langagent.eval.report_aggregator import EvalReport

@dataclass(frozen=True)
class EvalRunResult:
    eval_report: EvalReport
    final_state: AgentState
    exit_code: int
```

### State Transitions
- **Aggregated**: Runner calls report_aggregator.aggregate()
- **Assembled**: Runner creates EvalRunResult with 3 fields
- **Returned**: F10 cli_runner.dispatch() receives result
- **Cleanup**: F10 calls exit_handler.cleanup(result.final_state, config, eval_report=result.eval_report)

### Related Schemas
- Wraps: `EvalReport` + `AgentState`
- Returned by: `eval.runner.run()`
- Consumed by: `cli.runner.dispatch()` eval branch

---

## Entity 5: GraderRegistry

### Description
Internal registry mapping grader names to grader functions. Not a Pydantic model (simple dict).

### Structure

```python
from typing import Callable, Any

GraderFunction = Callable[[str, str | list[str] | dict[str, Any], ...], bool]

GRADER_REGISTRY: dict[str, GraderFunction] = {
    "exact_match": exact_match.grade,
    "contains": contains.grade,
    "regex": regex.grade,
    "llm_judge": llm_judge.grade,
    "tool_call_match": tool_call_match.grade,
}
```

### Validation Rules

1. **Key uniqueness**: No duplicate grader names
2. **Function signature**: All graders accept `(actual: str, expected: ..., **kwargs) -> bool`
3. **Completeness**: All 5 EvalTaskSpec.grader Literal values must have entries

### State Transitions
- **Initialized**: Module import populates registry
- **Queried**: Runner looks up grader by EvalTaskSpec.grader field
- *(Immutable after module load)*

---

## Relationships Diagram

```
EvalTaskSpec (YAML)
    ↓ (task_loader.load_all)
List[EvalTaskSpec]
    ↓ (runner._run_one_task per task)
TaskResult (internal)
    ↓ (report_aggregator.aggregate)
EvalReport
    ↓ (runner.run wraps)
EvalRunResult → [eval_report, final_state, exit_code]
    ↓ (F10 dispatch)
exit_handler.cleanup(eval_report=...)
    ↓
~/.local/share/langagent/reports/<name>-<ts>.json
```

---

## Validation Summary

| Entity | Schema Type | Immutability | Persistence |
|--------|-------------|--------------|-------------|
| EvalTaskSpec | Pydantic BaseModel | frozen=True | YAML source (read-only) |
| TaskResult | Pydantic BaseModel | frozen=True | Not persisted (aggregated) |
| EvalReport | Pydantic BaseModel | frozen=True | JSON (reports dir) |
| EvalRunResult | dataclass | frozen=True | Not persisted (return value) |
| GraderRegistry | dict | Immutable after load | Not persisted (code) |

**All entities are immutable after creation** (Constitution Article VI reducer constraints).
