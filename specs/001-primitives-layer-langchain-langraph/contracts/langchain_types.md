# Contract: langchain_types

**Module**: `langagent.primitives.langchain_types`  
**Owner**: F01 Primitives Layer  
**Version**: 1.0.0

---

## Overview

The `langchain_types` module re-exports all LangChain and LangGraph types used by other LangAgent layers. This enforces the architectural boundary that **only the primitives layer may import langchain/langgraph packages directly** (宪法第 II 条, architecture_modules.md dependency matrix).

Runtime, cross_cutting, protocol, and CLI layers MUST import LangChain/LangGraph types through this re-export module (FR-033).

---

## Re-Export List (FR-031)

### LangChain Core Messages

```python
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
    add_messages,  # Reducer function for messages field
)
```

**Usage**: `AgentState.messages` field with `add_messages` reducer.

---

### LangChain Models

```python
from langchain_core.language_models import BaseChatModel
```

**Usage**: Type annotation for model instances produced by `chat_model_factory.create()`.

---

### LangChain Tools

```python
from langchain_core.tools import (
    BaseTool,
    tool,  # Decorator for defining tools
)
```

**Usage**: F05 tool_registry for tool definitions.

---

### LangGraph Graph Primitives

```python
from langgraph.graph import (
    StateGraph,
    CompiledStateGraph,
    START,
    END,
)
```

**Usage**: F01 `state_graph_builder` compiles `StateGraph` into `CompiledStateGraph`.

---

### LangGraph Checkpointing

```python
from langgraph.checkpoint import BaseCheckpointSaver
```

**Usage**: F01 `checkpoint_adapter` produces instances of this interface.

---

### LangGraph Control Flow

```python
from langgraph.prebuilt.chat_agent_executor import interrupt
```

**Usage**: F08 main loop HITL (human-in-the-loop) interrupt points.

---

### LangGraph Runtime (research.md Decision 2)

```python
from langgraph.runtime import Runtime
```

**Usage**: LangGraph uses Runtime context instead of traditional AgentMiddleware. F01 translates `MiddlewareSpec` to Runtime context pattern.

**Important Note**: The spec originally assumed LangChain `AgentMiddleware` protocol existed in LangGraph. Research (Decision 2) found this is incorrect. LangGraph uses `Runtime` context for cross-cutting concerns.

---

## Full Re-Export Module

```python
"""
Re-export all LangChain/LangGraph types.

ARCHITECTURAL BOUNDARY ENFORCEMENT:
Only langagent.primitives may import langchain/langgraph directly.
Other layers (runtime/cross_cutting/protocol/cli) MUST import through this module.

See: 宪法第 II 条, architecture_modules.md dependency matrix, FR-033
"""

# Messages
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
    add_messages,
)

# Models
from langchain_core.language_models import BaseChatModel

# Tools
from langchain_core.tools import BaseTool, tool

# Graph
from langgraph.graph import StateGraph, CompiledStateGraph, START, END

# Checkpointing
from langgraph.checkpoint import BaseCheckpointSaver

# Control flow
from langgraph.prebuilt.chat_agent_executor import interrupt

# Runtime context
from langgraph.runtime import Runtime

__all__ = [
    # Messages
    "BaseMessage",
    "HumanMessage",
    "AIMessage",
    "SystemMessage",
    "ToolMessage",
    "add_messages",
    # Models
    "BaseChatModel",
    # Tools
    "BaseTool",
    "tool",
    # Graph
    "StateGraph",
    "CompiledStateGraph",
    "START",
    "END",
    # Checkpointing
    "BaseCheckpointSaver",
    # Control flow
    "interrupt",
    # Runtime
    "Runtime",
]
```

---

## Usage Example

### Correct Usage (via primitives re-export)

```python
# langagent/runtime/agent_state.py
from langagent.primitives.langchain_types import BaseMessage, add_messages
from typing import TypedDict, Annotated

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
```

```python
# langagent/protocol/tool_definition.py
from langagent.primitives.langchain_types import BaseTool, tool

@tool
def calculator(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
```

### Incorrect Usage (direct import, violates FR-033)

```python
# ❌ VIOLATION: langagent/runtime/agent_state.py
from langchain_core.messages import BaseMessage, add_messages  # ❌ Direct import

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
```

**Static Analysis Check** (SC-005): `grep -r "from langchain" langagent/runtime/ langagent/cross_cutting/ langagent/protocol/ langagent/cli/` must return NO matches.

---

## Testing Contract

### Unit Tests

1. `test_import_messages` - Import all message types, verify identity with LangChain originals
2. `test_import_models` - Import BaseChatModel, verify identity
3. `test_import_tools` - Import BaseTool and @tool decorator, verify identity
4. `test_import_graph` - Import StateGraph/CompiledStateGraph, verify identity
5. `test_import_checkpoint` - Import BaseCheckpointSaver, verify identity
6. `test_import_interrupt` - Import interrupt function, verify identity
7. `test_import_runtime` - Import Runtime, verify identity

### Static Analysis Tests

1. `test_no_direct_langchain_imports_runtime` - Grep runtime layer, assert 0 matches
2. `test_no_direct_langchain_imports_cross_cutting` - Grep cross_cutting layer (except logger which may need internal imports), assert 0 matches
3. `test_no_direct_langchain_imports_protocol` - Grep protocol layer, assert 0 matches
4. `test_no_direct_langchain_imports_cli` - Grep CLI layer, assert 0 matches

**Success Criterion** (SC-005): 100% of primitives layer imports of LangChain/LangGraph types go through re-export module.

---

## Dependencies

**Imports**:
```python
# Direct imports from langchain/langgraph (ONLY allowed in primitives layer)
from langchain_core.messages import ...
from langchain_core.language_models import ...
from langchain_core.tools import ...
from langgraph.graph import ...
from langgraph.checkpoint import ...
from langgraph.prebuilt.chat_agent_executor import ...
from langgraph.runtime import ...
```

**No Dependencies On**:
- Any `langagent.*` modules (this is a leaf re-export module)

---

## Version History

- **1.0.0** (2026-09-17): Initial contract definition
