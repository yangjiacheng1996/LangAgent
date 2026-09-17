# Contract: state_graph_builder

**Module**: `langagent.primitives.state_graph_builder`  
**Owner**: F01 Primitives Layer  
**Version**: 1.0.0

---

## Overview

The `state_graph_builder` module compiles a LangGraph `StateGraph` into a runnable `CompiledStateGraph` by injecting AgentState schema, custom reducers, user middleware, system guardrail middleware, tools, and checkpoint persistence. This is the graph_compose stage (stage 4) of the 6-stage workflow.

---

## Public Interface

### `build(loaded_agent: LoadedAgent, config: RuntimeConfig, checkpoint: BaseCheckpointSaver) -> CompiledStateGraph`

Compile a StateGraph with tools, middleware, and checkpointer.

**Parameters**:
- `loaded_agent: LoadedAgent` - Parsed agent directory metadata from F06:
  - `agent_dir: Path` - Used to locate `middleware/*.py` files
  - `tool_ids: list[str]` - Tool identifiers to bind to graph
  - Other fields (instructions, skill_names, metadata) not used by F01
- `config: RuntimeConfig` - Frozen configuration snapshot:
  - `middleware_ids: list[str]` - User middleware to load
  - `guardrail_policy: GuardrailPolicy | None` - System guardrail config
- `checkpoint: BaseCheckpointSaver` - Explicit checkpoint instance (not created internally per FR-014, review.md S-5)

**Returns**:
- `CompiledStateGraph` - Executable graph ready for invocation

**Raises**:
- `GraphCompileError` (exit code 70) - LangGraph compilation failed OR middleware syntax error (FR-021, clarification Q3)
  - Middleware syntax errors cause immediate failure with specific file path and error details
  - No partial loading: all middleware must be valid or entire build fails
- `ToolBindingError` (exit code 70) - Tool binding to model failed (FR-022)

**Side Effects**:
- Loads middleware from `agent_dir/middleware/<name>.py` using `importlib.util.spec_from_file_location` (FR-015)
  - Namespace: `langagent_dynamic_middleware_{name}` (research.md Decision 3)
  - Cleans up `sys.modules` entries after build completes (FR-016)
- Parses `MIDDLEWARE_SPEC` module-level constant from each middleware file (FR-017)
- Instantiates system guardrail middleware via `cross_cutting_guardrail_middleware.build_middleware(policy)` if policy not None (FR-019)
- Emits 5 log tags via `cross_cutting_logger.emit()`:
  - `la.runtime.graph_compose.start` - Function entry
  - `la.runtime.graph_compose.middleware_bind` - Per middleware injection
  - `la.runtime.graph_compose.tool_bind` - Per tool binding
  - `la.runtime.graph_compose.ok` - Success path
  - `la.runtime.graph_compose.fail` - Error path

**Stage Guard** (FR-046):
```python
@cross_cutting_stage_guard_decorator(
    'graph_compose',
    monkeypatch_blacklist=[
        BaseChatModel.__init__,
        chat_model_factory.create,
        RuntimeDirLoader.load
    ]
)
def build(...) -> CompiledStateGraph:
    ...
```

---

## Build Steps (Internal Logic)

Per plan.md Phase 1 contract specification:

1. **Import reducers** from `primitives.state_reducers` (FR-013)
2. **Define StateGraph** with AgentState TypedDict schema (FR-011)
3. **Load middleware** from `agent_dir/middleware/*.py`:
   - Use `importlib.util.spec_from_file_location` with unique namespace (FR-015)
   - Parse `MIDDLEWARE_SPEC` constant (FR-017)
   - Validate `hook_points` against LangGraph Runtime context protocol (FR-018)
   - On syntax error: raise `GraphCompileError` with file path and details (clarification Q3)
4. **Instantiate system guardrail middleware** if `guardrail_policy` not None (FR-019):
   - Call `cross_cutting_guardrail_middleware.build_middleware(policy=config.guardrail_policy)`
   - Returns `AgentMiddleware` instance (or LangGraph Runtime context equivalent per research.md Decision 2)
5. **Inject middleware** into graph in priority order (ascending):
   - User middleware from step 3
   - System guardrail middleware from step 4
   - Lower priority = earlier execution (FR-020)
6. **Bind tools** from `loaded_agent.tool_ids`:
   - Resolve tool instances via F05 tool_registry
   - Bind to model using `model.bind_tools(tools)`
   - On binding failure: raise `ToolBindingError` (FR-022)
7. **Clean up `sys.modules`**:
   - Remove all entries with prefix `langagent_dynamic_middleware_*` (FR-016)
   - Prevents memory leaks and stale module caching (research.md Decision 3)
8. **Compile graph** with checkpoint:
   - Call `builder.compile(checkpointer=checkpoint)`
   - Returns `CompiledStateGraph` (FR-023)

---

## AgentState Schema (FR-011)

Defined in `langagent.runtime.agent_state` with reducers from `langagent.primitives.state_reducers`:

```python
from typing import TypedDict, Annotated, Any
from langchain_core.messages import BaseMessage
from langagent.primitives.state_reducers import replace_with_merge, merge_dict, overwrite_or_merge
from langagent.primitives.langchain_types import add_messages

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    todos: Annotated[list[dict[str, Any]], replace_with_merge]
    files: Annotated[dict[str, dict[str, Any]], merge_dict]
    context: Annotated[dict[str, Any], overwrite_or_merge]
    scratchpad: Annotated[list[dict[str, Any]], replace_with_merge]
```

All reducers injected via LangGraph `Annotated` mechanism (FR-012, research.md Decision 2).

---

## Middleware Loading Protocol (FR-015 to FR-020)

### File Discovery

Middleware files located in `{loaded_agent.agent_dir}/middleware/*.py`.

Example directory structure:
```
agent_dir/
├── middleware/
│   ├── rate_limiter.py
│   ├── token_counter.py
│   └── pii_filter.py
└── ...
```

### MiddlewareSpec Format

Each middleware file must export `MIDDLEWARE_SPEC` module-level constant:

```python
# agent_dir/middleware/rate_limiter.py
MIDDLEWARE_SPEC = {
    "id": "rate_limiter",
    "priority": 100,
    "hook_points": ["on_node_start"]
}

def rate_limit_middleware(state, runtime):
    """Middleware implementation."""
    ...
```

**MiddlewareSpec Fields**:
- `id: str` - Must match filename without `.py`
- `priority: int` - Range [0, 1000], ascending order
- `hook_points: list[str]` - Valid LangGraph Runtime context hooks (FR-018)

**Important Finding** (research.md Decision 2): LangGraph does NOT have traditional "AgentMiddleware protocol". The spec incorrectly assumes LangChain middleware applies to LangGraph. Actual pattern is **LangGraph Runtime context**. F01 implementation must translate `MiddlewareSpec` to LangGraph's context injection pattern.

### Import Pattern (research.md Decision 3)

```python
import importlib.util
import sys
from pathlib import Path

# Unique namespace prevents collisions
unique_name = f"langagent_dynamic_middleware_{middleware_name}"

# Create spec WITHOUT polluting sys.path
spec = importlib.util.spec_from_file_location(unique_name, str(middleware_path))

# Create and execute module
module = importlib.util.module_from_spec(spec)
sys.modules[unique_name] = module  # Register BEFORE execution
spec.loader.exec_module(module)

# Parse MIDDLEWARE_SPEC
middleware_spec = MiddlewareSpec(**module.MIDDLEWARE_SPEC)

# ... use middleware_spec to inject into graph ...

# Cleanup after build
sys.modules.pop(unique_name, None)
```

### Syntax Error Handling (clarification Q3)

Per clarification Q3: "middleware是智能体内部代码。如果middleware语法错误，则智能体整体失败"

```python
try:
    spec.loader.exec_module(module)
except SyntaxError as e:
    raise GraphCompileError(
        f"Middleware syntax error in {middleware_path}: "
        f"line {e.lineno}, {e.msg}"
    ) from e
except Exception as e:
    raise GraphCompileError(
        f"Failed to load middleware {middleware_path}: {e}"
    ) from e
```

No partial loading: all middleware must be valid or build fails immediately.

---

## System Guardrail Middleware (FR-019)

Per review.md v2.2.2 P0-2, F01 must instantiate system guardrail middleware:

```python
from langagent.cross_cutting.guardrail_middleware import build_middleware

if config.guardrail_policy is not None:
    guardrail_middleware = build_middleware(policy=config.guardrail_policy)
    # Inject into graph alongside user middleware by priority
```

**Dependency Note** (plan.md Phase 1 contracts):
- `build_middleware` is a Protocol stub created by F06 in F01's first batch
- Actual implementation filled by F04 Phase 1 (third batch)
- F01 TDD tests mock this interface

**Hardcoded Exception** (architecture_modules.md v2.4.0):
- `primitives_state_graph_builder → cross_cutting_guardrail_middleware` marked with `→²` in dependency matrix
- CHK-AR-024 validates unidirectional dependency (guardrail_middleware does not import primitives)

---

## Usage Example

```python
from langagent.primitives.state_graph_builder import build
from langagent.primitives.checkpoint_adapter import create as create_checkpoint
from langagent.protocol.loaded_agent import LoadedAgent
from langagent.runtime.config import RuntimeConfig

# F06 produces LoadedAgent
loaded = LoadedAgent(
    agent_dir="/path/to/agent",
    tool_ids=["web_search", "calculator"],
    ...
)

# F07 produces RuntimeConfig
config = RuntimeConfig(
    middleware_ids=["rate_limiter", "token_counter"],
    guardrail_policy=GuardrailPolicy(...),
    ...
)

# F01 creates checkpoint (explicit parameter per review.md S-5)
checkpoint = create_checkpoint(config)

# F01 builds graph
graph = build(loaded, config, checkpoint)

# F08 invokes graph
result = graph.invoke({"messages": [HumanMessage("Hello")]}, config=...)
```

---

## Testing Contract

### Unit Tests

1. `test_build_minimal_agent_state` - 0 tools, 0 middleware, memory checkpoint
2. `test_build_with_one_tool` - 1 tool from tool_ids
3. `test_build_with_one_middleware` - 1 user middleware from agent_dir
4. `test_build_with_guardrail_middleware` - Guardrail policy not None
5. `test_build_middleware_syntax_error` - Raises `GraphCompileError` with file path
6. `test_build_middleware_priority_order` - Multiple middleware injected in ascending priority
7. `test_build_cleans_sys_modules` - Assert `langagent_dynamic_middleware_*` removed after build
8. `test_build_tool_binding_error` - Invalid tool_id raises `ToolBindingError`
9. `test_build_emits_start_tag` - Mock logger, verify start tag
10. `test_build_emits_middleware_bind_tag` - Mock logger, verify per middleware
11. `test_build_emits_ok_tag` - Mock logger, verify success tag

### Integration Tests

1. `test_build_and_invoke_graph` - Build graph, invoke with test message, assert state updated
2. `test_build_with_checkpoint_persistence` - Build with sqlite checkpoint, invoke, resume from checkpoint

---

## Dependencies

**Imports**:
```python
from langagent.protocol.loaded_agent import LoadedAgent
from langagent.runtime.config import RuntimeConfig
from langagent.primitives.langchain_types import (
    CompiledStateGraph,
    StateGraph,
    BaseCheckpointSaver,
    BaseChatModel,
)
from langagent.primitives.state_reducers import replace_with_merge, merge_dict, overwrite_or_merge
from langagent.primitives.exceptions import GraphCompileError, ToolBindingError
from langagent.primitives.middleware_spec import MiddlewareSpec
from langagent.cross_cutting.logger import emit
from langagent.cross_cutting.stage_guard import cross_cutting_stage_guard_decorator
from langagent.cross_cutting.guardrail_middleware import build_middleware

import importlib.util
import sys
from pathlib import Path
```

**No Dependencies On**:
- `langagent.runtime.main_loop` (caller, not callee)
- `langagent.cli` layers

---

## Version History

- **1.0.0** (2026-09-17): Initial contract definition
