# F01 Primitives Layer — Data Model

**Feature**: F01 — Primitives Layer Encapsulation  
**Date**: 2026-09-17  
**Status**: Phase 1 Design

This document defines the entity schemas, relationships, and state transitions for the primitives layer.

---

## Entity Overview

F01 primitives layer interacts with 6 key entities:

| Entity | Ownership | Mutability | Purpose |
|--------|-----------|------------|---------|
| `RuntimeConfig` | F07 produces, F01 consumes | Immutable (frozen) | Configuration snapshot for model/checkpoint instantiation |
| `LoadedAgent` | F06 produces, F01 consumes | Immutable (frozen) | Parsed agent directory metadata |
| `BaseChatModel` | F01 produces, F10 consumes | Mutable (LangChain object) | Instantiated model interface |
| `CompiledStateGraph` | F01 produces, F08 consumes | Mutable (LangGraph object) | Executable agent graph |
| `AgentState` | F01 defines reducers, runtime mutates | Mutable (graph state) | 5-field TypedDict with custom reducers |
| `MiddlewareSpec` | F01 owns | Immutable (frozen) | Parsed middleware metadata from agent_dir |

---

## Entity Schemas

### 1. RuntimeConfig (Consumed)

**Source**: F07 `config_resolve` stage  
**Schema Version**: v1.0.0  
**Pydantic Model**: `langagent.runtime.config.RuntimeConfig`

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

class RuntimeConfig(BaseModel, frozen=True):
    """Frozen configuration snapshot. F01 consumes, never mutates."""
    
    # Model configuration (FR-001 to FR-010)
    model_provider: Literal["openai", "anthropic", "google", "deepseek", "zhipu", "openai-compatible"]
    model_name: str
    model_base_url: Optional[str] = None  # Required for deepseek/zhipu/openai-compatible
    model: Optional[BaseChatModel] = None  # None until F10 calls config.with_model()
    
    # Checkpoint configuration (FR-024 to FR-030)
    checkpointer: Literal["memory", "sqlite", "postgres"] = "memory"
    checkpoint_sqlite_path: Optional[str] = None  # Required when checkpointer="sqlite"
    checkpoint_postgres_dsn: Optional[str] = None  # Required when checkpointer="postgres"
    
    # Middleware configuration (FR-015 to FR-020)
    middleware_ids: list[str] = Field(default_factory=list)
    
    # Guardrail configuration (FR-019)
    guardrail_policy: Optional["GuardrailPolicy"] = None  # None = skip guardrail middleware
    
    def with_model(self, model: BaseChatModel) -> "RuntimeConfig":
        """Return new frozen instance with model field populated. F10 calls this."""
        return self.model_copy(update={"model": model})
```

**Fields Consumed by F01**:
- `model_provider`, `model_name`, `model_base_url` → `chat_model_factory.create()`
- `checkpointer`, `checkpoint_sqlite_path`, `checkpoint_postgres_dsn` → `checkpoint_adapter.create()`
- `middleware_ids`, `guardrail_policy` → `state_graph_builder.build()`

**Immutability Constraint (FR-009)**: F01 never calls `model_copy()` or mutates fields. Only F10 reconstructs via `with_model()`.

---

### 2. LoadedAgent (Consumed)

**Source**: F06 `dir_load` stage  
**Schema Version**: v0.2.0 (review.md v1.1.0: removed `compiled_graph` field)  
**Pydantic Model**: `langagent.protocol.loaded_agent.LoadedAgent`

```python
from pydantic import BaseModel, DirectoryPath
from pathlib import Path

class LoadedAgent(BaseModel, frozen=True):
    """Parsed agent directory metadata. F01 consumes during graph compilation."""
    
    agent_dir: DirectoryPath  # Absolute path to agent directory
    instructions: str  # Content of instructions.md
    tool_ids: list[str]  # List of tool identifiers (resolved by F05)
    skill_names: list[str]  # List of skill names (from skills/ subdirectory)
    metadata: dict[str, Any]  # Optional metadata from agent.yaml
```

**Fields Consumed by F01**:
- `agent_dir` → `state_graph_builder.build()` uses to locate `middleware/*.py` files
- `tool_ids` → `state_graph_builder.build()` binds tools to graph
- `skill_names`, `metadata` → Not used by F01 (consumed by F08 main loop)

---

### 3. BaseChatModel (Produced)

**Source**: F01 `chat_model_factory.create()` produces  
**Type**: LangChain abstract base class  
**Module**: `langchain_core.language_models.BaseChatModel`

```python
# Type annotation (F01 re-exports via primitives.langchain_types)
from langchain_core.language_models import BaseChatModel

# Factory signature (FR-010)
def create(config: RuntimeConfig) -> BaseChatModel:
    """Return instantiated model. Does NOT modify config."""
    ...
```

**Concrete Implementations**:
- `langchain_openai.ChatOpenAI` (for openai, openai-compatible, deepseek, zhipu)
- `langchain_anthropic.ChatAnthropic` (for anthropic)
- `langchain_google_genai.ChatGoogleGenerativeAI` (for google)

**State Transitions**:
1. F01 instantiates → BaseChatModel instance
2. F10 calls `config.with_model(model)` → RuntimeConfig with populated `model` field
3. F08 passes to graph nodes → Model invoked during agent loop

---

### 4. CompiledStateGraph (Produced)

**Source**: F01 `state_graph_builder.build()` produces  
**Type**: LangGraph compiled graph  
**Module**: `langgraph.graph.CompiledStateGraph`

```python
from langgraph.graph import CompiledStateGraph

# Builder signature (FR-023)
def build(
    loaded_agent: LoadedAgent,
    config: RuntimeConfig,
    checkpoint: BaseCheckpointSaver
) -> CompiledStateGraph:
    """Compile graph with tools, middleware, checkpointer."""
    ...
```

**Internal Structure** (opaque to F01 consumers):
- Nodes: `model_call`, `tools_execute`, `should_continue`
- Edges: Conditional routing based on tool calls
- State: AgentState TypedDict with 5 fields + reducers
- Checkpointer: Passed to `compile(checkpointer=...)`

**State Transitions**:
1. F01 compiles → CompiledStateGraph instance
2. F10 stores in dispatch context
3. F08 invokes `graph.invoke(input, config)` → Agent execution

---

### 5. AgentState (Structure Defined by F01)

**Source**: F01 defines schema + reducers, runtime mutates during graph execution  
**Type**: TypedDict with Annotated reducers  
**Module**: `langagent.runtime.agent_state.AgentState`

```python
from typing import TypedDict, Annotated, Any
from langchain_core.messages import BaseMessage
from langagent.primitives.state_reducers import replace_with_merge, merge_dict, overwrite_or_merge
from langagent.primitives.langchain_types import add_messages

class AgentState(TypedDict):
    """5-field state with custom reducers. FR-011 to FR-013."""
    
    # Field 1: Message history (LangGraph built-in reducer)
    messages: Annotated[list[BaseMessage], add_messages]
    
    # Field 2: Planning/task list (custom reducer, shared with scratchpad)
    todos: Annotated[list[dict[str, Any]], replace_with_merge]
    
    # Field 3: Virtual filesystem state (custom reducer)
    files: Annotated[dict[str, dict[str, Any]], merge_dict]
    
    # Field 4: Short-term context metadata (custom reducer with mode parameter)
    context: Annotated[dict[str, Any], overwrite_or_merge]
    
    # Field 5: Intermediate reasoning (custom reducer, shared with todos)
    scratchpad: Annotated[list[dict[str, Any]], replace_with_merge]
```

**Reducer Semantics** (FR-034 to FR-040):
- `add_messages`: LangGraph built-in, appends new messages to list
- `replace_with_merge`: Merge list[dict] by id/timestamp, used by todos/scratchpad
- `merge_dict`: Merge dict by key, update values override current
- `overwrite_or_merge`: Mode-controlled merger for context field

**State Transitions**:
1. Graph initialization → Empty AgentState (all fields = default values)
2. Node execution → Reducer merges `update` into `current` state
3. Checkpoint save → State persisted to checkpoint backend
4. Resume → State restored from checkpoint

---

### 6. MiddlewareSpec (Owned by F01)

**Source**: F01 parses from `agent_dir/middleware/<name>.py` MIDDLEWARE_SPEC constant  
**Schema Version**: v1.0.0  
**Pydantic Model**: `langagent.primitives.middleware_spec.MiddlewareSpec`

```python
from pydantic import BaseModel, Field, field_validator

class MiddlewareSpec(BaseModel, frozen=True):
    """Parsed middleware metadata. F01 owns this schema (not F05)."""
    
    id: str  # Unique identifier (filename without .py)
    priority: int = Field(ge=0, le=1000)  # Lower = earlier execution
    hook_points: list[str]  # LangGraph Runtime context hooks
    
    @field_validator("hook_points")
    @classmethod
    def validate_hook_points(cls, v: list[str]) -> list[str]:
        """FR-018: Validate hook_points against LangGraph protocol."""
        # NOTE: Research finding (Decision 2) shows LangGraph uses Runtime context,
        # not traditional middleware hooks. Valid values TBD during implementation.
        allowed = ["on_node_start", "on_node_end", "on_edge_traverse", "on_state_update"]
        invalid = [h for h in v if h not in allowed]
        if invalid:
            raise ValueError(f"Invalid hook_points: {invalid}. Allowed: {allowed}")
        return v
```

**Parsing Location**: `agent_dir/middleware/<name>.py`

```python
# Example middleware file: agent_dir/middleware/rate_limiter.py
MIDDLEWARE_SPEC = {
    "id": "rate_limiter",
    "priority": 100,
    "hook_points": ["on_node_start"]
}

def rate_limit_middleware(state, runtime):
    """Middleware function implementing rate limiting."""
    ...
```

**State Transitions**:
1. F01 `state_graph_builder.build()` → Import middleware/*.py via importlib
2. Parse MIDDLEWARE_SPEC constant → MiddlewareSpec instance
3. Validate hook_points (FR-018)
4. Translate to LangGraph Runtime context pattern (research Decision 2)
5. Inject into graph by priority order (ascending)
6. Clean up sys.modules (FR-016)

---

## Exception Types (Owned by F01)

All exceptions defined in `langagent.primitives.exceptions`:

```python
class ProviderUnsupportedError(Exception):
    """FR-005: model_provider not in 6 supported values."""
    exit_code = 78

class AuthFailedError(Exception):
    """FR-006: Required API key env var missing."""
    exit_code = 78

class EndpointUnreachableError(Exception):
    """FR-007: model_base_url cannot be reached (strict enforcement)."""
    exit_code = 70

class RequiredFieldMissingError(Exception):
    """FR-008: model_base_url is None for providers requiring it."""
    exit_code = 5

class GraphCompileError(Exception):
    """FR-021: LangGraph compilation failed OR SQLite corruption repair failed."""
    exit_code = 70

class ToolBindingError(Exception):
    """FR-022: Tool binding to model failed."""
    exit_code = 70

class CheckpointTypeUnsupportedError(Exception):
    """FR-028: checkpointer not in 3 supported values."""
    exit_code = 78
```

**Exit Code Mapping** (from workflow.md):
- 5: Required configuration field missing
- 70: Runtime operation failed (graph compile, endpoint unreachable, tool binding)
- 78: Unsupported option (provider, checkpointer type)

---

## Reducer Function Signatures

Defined in `langagent.primitives.state_reducers`:

### replace_with_merge

```python
def replace_with_merge(
    current: list[dict[str, Any]] | None,
    update: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Reducer for AgentState.todos and AgentState.scratchpad.
    
    Merge strategy (FR-037):
    - If update is None: return current or []
    - If update is proper list[dict]: return update
    - If update is str/dict/list[str]: attempt type conversion (research Decision 6)
    - On conversion failure: log error, return current or []
    
    Type conversion (clarification Q4):
    - str → parse JSON → list[dict] or wrap as [{"description": str}]
    - dict → wrap as [dict]
    - list[str] → convert each to {"description": str}
    
    Pure function (FR-035): No side effects, no global state mutation.
    No exceptions (FR-040): Degrade gracefully.
    """
```

### merge_dict

```python
def merge_dict(
    current: dict[str, dict[str, Any]] | None,
    update: dict[str, dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    """Reducer for AgentState.files.
    
    Merge strategy (FR-038):
    - Merge by key, update values override current values
    - If update is None: return current or {}
    - If update is proper dict[str, dict]: merge and return
    - If update is str: parse JSON (research Decision 6)
    - If update is list: extract keyed structure (path/name/id fields)
    
    Pure function (FR-035): Returns new dict, doesn't mutate inputs.
    No exceptions (FR-040): Log conversion errors, degrade gracefully.
    """
```

### overwrite_or_merge

```python
def overwrite_or_merge(
    current: dict[str, Any] | None,
    update: dict[str, Any] | None,
    *,
    mode: Literal['overwrite', 'merge_with_prior'] = 'merge_with_prior',
) -> dict[str, Any]:
    """Reducer for AgentState.context.
    
    Merge strategy (FR-039):
    - mode='overwrite': return dict(update), discard current
    - mode='merge_with_prior': return {**current, **update}
    - If update is None: return current or {}
    - If update is str: parse JSON (research Decision 6)
    - If update is list: convert to index-keyed dict {"0": item, "1": item}
    
    Mode parameter: Injected via LangGraph Annotated[dict, overwrite_or_merge]
    Pure function (FR-035): No side effects.
    No exceptions (FR-040): Degrade gracefully.
    """
```

---

## Relationships

```
RuntimeConfig (F07)
    ├─→ chat_model_factory.create() ──→ BaseChatModel (F01 produces)
    │                                       │
    │                                       └─→ RuntimeConfig.with_model() (F10)
    │
    ├─→ checkpoint_adapter.create() ──→ BaseCheckpointSaver
    │                                       │
    └─→ state_graph_builder.build() ────────┴──→ CompiledStateGraph (F01 produces)
                                                       │
LoadedAgent (F06)                                      │
    ├─→ agent_dir/middleware/*.py ──→ MiddlewareSpec  │
    ├─→ tool_ids ─────────────────────────────────────┤
    └─→ passed to build() ────────────────────────────┘
                                                       │
                                                       └─→ F08 invokes graph

AgentState (structure)
    ├─→ messages: add_messages (LangGraph built-in)
    ├─→ todos: replace_with_merge (F01 owns)
    ├─→ files: merge_dict (F01 owns)
    ├─→ context: overwrite_or_merge (F01 owns)
    └─→ scratchpad: replace_with_merge (F01 owns, shared with todos)
```

---

## Validation Rules

### RuntimeConfig Validation (F07 responsibility, F01 assumes valid)
- `model_provider` in ["openai", "anthropic", "google", "deepseek", "zhipu", "openai-compatible"]
- `model_base_url` required when provider in ["openai-compatible", "deepseek", "zhipu"]
- `model_base_url` must NOT contain "localhost", "127.0.0.1", internal IP literals (FR-004)
- `checkpointer` in ["memory", "sqlite", "postgres"]
- `checkpoint_sqlite_path` required when checkpointer="sqlite"
- `checkpoint_postgres_dsn` required when checkpointer="postgres"

### MiddlewareSpec Validation (F01 responsibility)
- `id` must match filename (e.g., `rate_limiter.py` → id="rate_limiter")
- `priority` in range [0, 1000]
- `hook_points` must be valid LangGraph Runtime context hooks (FR-018)
- No duplicate IDs across agent_dir/middleware/*.py files

### AgentState Reducer Validation (F01 responsibility)
- All reducers must be pure functions (FR-035)
- All reducers must return new objects, not mutate inputs (FR-036)
- All reducers must handle None inputs gracefully (FR-037)
- All reducers must NOT raise exceptions (FR-040)

---

## State Lifecycle

### Model Instantiation Lifecycle
1. F07 produces RuntimeConfig (frozen, model=None)
2. F10 calls `chat_model_factory.create(config)` → BaseChatModel
3. F10 calls `config.with_model(model)` → New frozen RuntimeConfig (model populated)
4. F10 passes new config to graph invocation

### Graph Compilation Lifecycle
1. F06 produces LoadedAgent (frozen)
2. F10 calls `checkpoint_adapter.create(config)` → BaseCheckpointSaver
3. F10 calls `state_graph_builder.build(loaded, config, checkpoint)` → CompiledStateGraph
4. F10 stores graph in dispatch context
5. F08 invokes `graph.invoke(input, config)` → Agent execution

### State Update Lifecycle (during graph execution)
1. Node returns update dict: `{"todos": [{"desc": "fix bug"}]}`
2. LangGraph calls reducer: `replace_with_merge(current_state["todos"], update["todos"])`
3. Reducer attempts type conversion if needed (research Decision 6)
4. Reducer returns merged state (or current on failure)
5. LangGraph updates AgentState
6. Checkpointer persists updated state

---

## Performance Characteristics

| Entity | Instantiation Cost | Memory Footprint | Notes |
|--------|-------------------|------------------|-------|
| RuntimeConfig | <1ms | ~1 KB | Frozen Pydantic model |
| LoadedAgent | <10ms | ~10 KB | Parsed agent metadata |
| BaseChatModel | <5s | ~50 MB | Includes endpoint probe (FR-007) |
| CompiledStateGraph | <500ms | ~5 MB | LangGraph compilation overhead |
| AgentState | <1ms | ~100 KB | TypedDict, grows with messages |
| MiddlewareSpec | <1ms | ~1 KB | Per middleware file |

**Bottlenecks**:
- Model instantiation: Endpoint probe adds 1-3s latency (strict requirement, no bypass)
- Graph compilation: Middleware loading via importlib adds 50ms per file
- Postgres checkpoint: Network round-trip adds 100-500ms (mitigated by 3-retry mechanism)

---

This data model serves as the foundation for Phase 1 contract definitions and Phase 2 implementation tasks.
