# Contract: state_reducers

**Module**: `langagent.primitives.state_reducers`  
**Owner**: F01 Primitives Layer  
**Version**: 1.0.0

---

## Overview

The `state_reducers` module provides 3 pure reducer functions for `AgentState` fields. These reducers handle LangGraph state updates with defensive type conversion to tolerate malformed LLM outputs (clarification Q4: "有的大模型智力低下，确实会把 todo 变成字符串，或者输出残缺或非法的json").

All reducers comply with FR-035 (pure functions), FR-036 (immutability), and FR-040 (no exceptions, degrade gracefully).

---

## Public Interface

### `replace_with_merge(current, update) -> list[dict]`

Reducer for `AgentState.todos` and `AgentState.scratchpad` fields.

**Signature**:
```python
def replace_with_merge(
    current: list[dict[str, Any]] | None,
    update: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
```

**Merge Strategy** (FR-037):
- If `update` is `None`: return `current or []`
- If `update` is proper `list[dict]`: return `update` (replace)
- If `update` is malformed: attempt type conversion (research.md Decision 6), then degrade to `current or []`

**Type Conversions** (clarification Q4):
- `str` → Parse JSON → `list[dict]`, or wrap as `[{"description": str}]` if not JSON
- `dict` → Wrap as `[dict]`
- `list[str]` → Convert each to `{"description": str}`
- Partial JSON → Attempt repair (add missing brackets, fix quotes)

**Pure Function** (FR-035): No side effects, no global state mutation.

**No Exceptions** (FR-040): Log conversion errors via `cross_cutting_logger.emit`, return `current or []` on failure.

---

### `merge_dict(current, update) -> dict[str, dict]`

Reducer for `AgentState.files` field.

**Signature**:
```python
def merge_dict(
    current: dict[str, dict[str, Any]] | None,
    update: dict[str, dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
```

**Merge Strategy** (FR-038):
- Merge by key: `{**current, **update}`
- Update values override current values
- If `update` is `None`: return `current or {}`
- If `update` is malformed: attempt type conversion, then degrade to `current or {}`

**Type Conversions** (clarification Q4):
- `str` → Parse JSON → `dict[str, dict]`
- `list` → Extract keyed structure from `path`/`name`/`id` fields, or index-keyed dict
- Nested validation: Drop invalid entries, sanitize valid ones

**Pure Function** (FR-035): Returns new dict, doesn't mutate inputs.

**No Exceptions** (FR-040): Log conversion errors, degrade gracefully.

---

### `overwrite_or_merge(current, update, *, mode) -> dict[str, Any]`

Reducer for `AgentState.context` field.

**Signature**:
```python
def overwrite_or_merge(
    current: dict[str, Any] | None,
    update: dict[str, Any] | None,
    *,
    mode: Literal['overwrite', 'merge_with_prior'] = 'merge_with_prior',
) -> dict[str, Any]:
```

**Merge Strategy** (FR-039):
- `mode='overwrite'`: return `dict(update)`, discard `current`
- `mode='merge_with_prior'`: return `{**current, **update}`
- If `update` is `None`: return `current or {}`
- If `update` is malformed: attempt type conversion, then degrade to `current or {}`

**Type Conversions** (clarification Q4):
- `str` → Parse JSON → `dict[str, Any]`
- `list` → Convert to index-keyed dict: `{"0": item, "1": item, ...}`

**Mode Parameter**: Injected via LangGraph `Annotated[dict, overwrite_or_merge]` mechanism.

**Pure Function** (FR-035): No side effects.

**No Exceptions** (FR-040): Degrade gracefully.

---

## Type Conversion Table (research.md Decision 6)

| Input Type | Expected Type | Field | Conversion Strategy | Fallback |
|------------|---------------|-------|---------------------|----------|
| `str` | `list[dict]` | todos/scratchpad | Parse JSON → validate/convert → wrap dict in list → wrap plain string | `current or []` |
| `dict` | `list[dict]` | todos/scratchpad | Wrap in list: `[dict]` | `current or []` |
| `list[str]` | `list[dict]` | todos/scratchpad | Convert each: `{"description": str}` | `current or []` |
| `None` | `list[dict]` | todos/scratchpad | Return `current or []` | `[]` |
| `str` | `dict[str, dict]` | files | Parse JSON → validate nested structure | `current or {}` |
| `list` | `dict[str, dict]` | files | Extract keys from `path`/`name`/`id` fields | `current or {}` |
| `None` | `dict[str, dict]` | files | Return `current or {}` | `{}` |
| `str` | `dict[str, Any]` | context | Parse JSON → validate | `current or {}` |
| `list` | `dict[str, Any]` | context | Index-keyed dict: `{"0": item, ...}` | `current or {}` |
| `None` | `dict[str, Any]` | context | Return `current or {}` | `{}` |
| Partial JSON | Any | Any | Repair: add brackets, fix quotes, remove trailing commas | `current or empty container` |

---

## JSON Repair Utility (research.md Decision 6)

```python
def _repair_incomplete_json(json_str: str) -> str:
    """Attempt to repair incomplete/malformed JSON from LLM output."""
    import re
    
    repaired = json_str.strip()
    
    # Add missing closing brackets/braces
    open_brackets = repaired.count('[') - repaired.count(']')
    open_braces = repaired.count('{') - repaired.count('}')
    repaired += ']' * open_brackets + '}' * open_braces
    
    # Remove trailing commas
    repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
    
    # Fix unquoted keys (basic heuristic)
    repaired = re.sub(r'(\w+):', r'"\1":', repaired)
    
    return repaired
```

---

## Logging Strategy (research.md Decision 6)

All reducers emit logs via `cross_cutting_logger.emit()` for debugging LLM output issues:

```python
# Before conversion attempt
emit("la.runtime.graph_compose.reducer_conversion_attempt", {
    "field": "todos",
    "input_type": "str",
    "strategy": "json_parse"
})

# After conversion failure
emit("la.runtime.graph_compose.reducer_conversion_fail", {
    "field": "todos",
    "input_type": "str",
    "expected_type": "list[dict]",
    "error": str(e)
})

# When dropping invalid items during sanitization
emit("la.runtime.graph_compose.reducer_sanitization", {
    "field": "files",
    "dropped_key": "invalid_entry",
    "reason": "unsupported_nested_type"
})

# When JSON repair succeeds
emit("la.runtime.graph_compose.reducer_json_repair_success", {
    "field": "todos",
    "original_length": len(update),
    "repaired_length": len(repaired)
})
```

**FR-040 Compliance**: Reducers MUST NOT raise exceptions. All errors are logged and gracefully degraded to `current` state.

---

## Usage Example

### In AgentState Definition

```python
# langagent/runtime/agent_state.py
from typing import TypedDict, Annotated, Any
from langagent.primitives.state_reducers import replace_with_merge, merge_dict, overwrite_or_merge
from langagent.primitives.langchain_types import BaseMessage, add_messages

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    todos: Annotated[list[dict[str, Any]], replace_with_merge]
    files: Annotated[dict[str, dict[str, Any]], merge_dict]
    context: Annotated[dict[str, Any], overwrite_or_merge]
    scratchpad: Annotated[list[dict[str, Any]], replace_with_merge]
```

### During Graph Execution

```python
# Node returns malformed update (LLM output)
update = {"todos": "fix bug"}  # ❌ String instead of list[dict]

# LangGraph calls reducer
new_todos = replace_with_merge(current_todos, update["todos"])
# Result: [{"description": "fix bug"}]  # ✅ Auto-converted

# Or if JSON-like string
update = {"todos": '[{"desc": "fix bug"'}  # ❌ Incomplete JSON

# Reducer attempts repair
new_todos = replace_with_merge(current_todos, update["todos"])
# Result: [{"desc": "fix bug"}]  # ✅ Repaired and parsed
```

---

## Testing Contract

### Unit Tests

1. `test_replace_with_merge_none_inputs` - Both `None`, returns `[]`
2. `test_replace_with_merge_valid_list_dict` - Proper `list[dict]`, returns `update`
3. `test_replace_with_merge_str_json` - JSON string, parses successfully
4. `test_replace_with_merge_str_plain` - Plain string, wraps as `[{"description": str}]`
5. `test_replace_with_merge_dict` - Single dict, wraps as `[dict]`
6. `test_replace_with_merge_list_str` - `list[str]`, converts each to dict
7. `test_replace_with_merge_incomplete_json` - Repairs and parses
8. `test_replace_with_merge_invalid_type` - Unexpected type, returns `current`
9. `test_merge_dict_none_inputs` - Both `None`, returns `{}`
10. `test_merge_dict_valid_dict` - Proper nested dict, merges by key
11. `test_merge_dict_str_json` - JSON string, parses successfully
12. `test_merge_dict_list` - Extracts keyed structure from list
13. `test_merge_dict_nested_validation` - Drops invalid nested entries
14. `test_overwrite_or_merge_mode_overwrite` - Discards `current`, returns `update`
15. `test_overwrite_or_merge_mode_merge` - Merges `{**current, **update}`
16. `test_overwrite_or_merge_str_json` - JSON string, parses successfully
17. `test_overwrite_or_merge_list` - Converts to index-keyed dict

### Property-Based Tests (optional, recommended)

1. `test_reducers_never_raise` - Generate 1000 random inputs, assert no exceptions
2. `test_reducers_always_return_correct_type` - Assert return types always match signature
3. `test_reducers_pure_functions` - Assert same inputs always produce same outputs

---

## Dependencies

**Imports**:
```python
from typing import Any, Literal
from langagent.cross_cutting.logger import emit
import json
import re
```

**No Dependencies On**:
- `langagent.runtime` layers
- `langagent.protocol` layers
- `langagent.primitives` other modules (except langchain_types for type hints)

---

## Version History

- **1.0.0** (2026-09-17): Initial contract definition
