# Stage Guard Decorator API Contract

**Module**: `langagent.cross_cutting.stage_guard`

**Purpose**: Enforce stage capability boundaries to prevent cross-stage operations

## Public API

### cross_cutting_stage_guard_decorator()

```python
def cross_cutting_stage_guard_decorator(
    stage_name: str,
    *,
    monkeypatch_blacklist: list[type] | None = None,
    audit_event_blacklist: list[str] | None = None
) -> Callable
```

**Description**: Decorator to enforce stage capability boundaries by applying monkeypatches and audit hooks.

**Parameters**:
- `stage_name` (str): Name of the stage being protected (e.g., 'dir_load')
- `monkeypatch_blacklist` (list[type], optional): Classes to intercept
- `audit_event_blacklist` (list[str], optional): Audit events to block

**Returns**: Decorator function that wraps the target function

**Example**:
```python
from langagent.cross_cutting.stage_guard import cross_cutting_stage_guard_decorator
from langchain_core.language_models import BaseChatModel

@cross_cutting_stage_guard_decorator(
    'dir_load',
    monkeypatch_blacklist=[BaseChatModel]
)
def load_agent(agent_dir: str) -> LoadedAgent:
    # This function cannot instantiate models
    return RuntimeDirLoader.load(agent_dir)
```

---

## StageCapabilityViolationError

```python
class StageCapabilityViolationError(Exception):
    def __init__(self, stage_name: str, target: str, operation: str)
```

**Description**: Raised when a stage attempts an operation outside its defined scope.

**Attributes**:
- `stage_name` (str): Name of the stage that violated boundaries
- `target` (str): Class or module name that was accessed
- `operation` (str): Method or operation attempted

**Exit Code**: 1

**Example**:
```python
try:
    model = BaseChatModel()  # Blocked during dir_load stage
except StageCapabilityViolationError as e:
    print(f"Stage '{e.stage_name}' violated boundary")
    print(f"Attempted '{e.operation}' on '{e.target}'")
```

---

## STAGE_BLACKLIST_TABLE

Predefined stage restrictions:

```python
STAGE_BLACKLIST_TABLE = {
    'dir_load': {
        'BaseChatModel': ['__init__'],
        'StateGraph': ['compile'],
        'dotenv': ['load_dotenv', 'find_dotenv'],
    },
    'config_load': {
        'StateGraph': ['compile'],
    },
    'agent_init': {
        'StateGraph': ['compile'],
    },
    'graph_compile': {},
    'executor_run': {},
    'eval_score': {},
}
```

---

## Stage Enforcement Mechanisms

### 1. Monkeypatch Interception

The decorator temporarily replaces class methods with blocking stubs that raise `StageCapabilityViolationError`.

**Implementation**:
- Uses `Monkeystack` class for safe nested patching
- Automatically restores methods after execution (even on exceptions)
- Thread-safe for single-threaded execution

### 2. Audit Hook Blocking

The decorator registers CPython audit hooks to intercept file system and import operations.

**Limitations**:
- Audit hooks cannot be truly unregistered in CPython
- Single-threaded execution only (v1 constraint)
- Complex to test in isolation

---

## Usage Patterns

### Pattern 1: Protect Runtime Stage

```python
@cross_cutting_stage_guard_decorator('dir_load')
def load_agent(agent_dir: str) -> LoadedAgent:
    # Cannot instantiate models or compile graphs here
    return RuntimeDirLoader.load(agent_dir)
```

### Pattern 2: Custom Blacklist

```python
@cross_cutting_stage_guard_decorator(
    'custom_stage',
    monkeypatch_blacklist=[MyCustomClass],
    audit_event_blacklist=['open', 'import']
)
def custom_operation():
    # Custom restrictions applied
    pass
```

### Pattern 3: Nested Decorators

```python
@cross_cutting_stage_guard_decorator('outer_stage')
def outer_function():
    @cross_cutting_stage_guard_decorator('inner_stage')
    def inner_function():
        pass
    return inner_function()
```

---

## Constraints

1. **Single-threaded only**: Stage guard is not thread-safe (v1 constraint)
2. **Cleanup guaranteed**: Methods restored in finally block
3. **No side effects**: Decorator does not modify original functions
4. **Constitution compliance**: Aligns with Article XV (Top-Level Design Primacy)
