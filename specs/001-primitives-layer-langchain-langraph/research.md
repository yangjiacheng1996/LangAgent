# F01 Primitives Layer — Research Findings

**Feature**: F01 — Primitives Layer Encapsulation (LangChain / LangGraph Interface)  
**Date**: 2026-09-17  
**Status**: Phase 0 Complete

This document consolidates research findings for 6 technical questions that informed the F01 design.

---

## Decision 1: LangChain Provider Instantiation Patterns

**Question**: What are the exact constructor signatures for 6 model providers?

**Research Findings**:

### Provider: OpenAI
- **Class**: `ChatOpenAI` (from `langchain_openai`)
- **Required params**: `model` (string, e.g., "gpt-4")
- **Optional params**: `temperature`, `max_tokens`, `timeout`, `max_retries`, `api_key`, `base_url`
- **API key env var**: `OPENAI_API_KEY`
- **Base URL support**: Yes, via `base_url` parameter
- **Notes**: Default `max_retries=6`

### Provider: Anthropic
- **Class**: `ChatAnthropic` (from `langchain_anthropic`)
- **Required params**: `model` (string, e.g., "claude-sonnet-4-6")
- **Optional params**: `temperature`, `max_tokens`, `timeout`, `max_retries`, `api_key`
- **API key env var**: `ANTHROPIC_API_KEY`
- **Base URL support**: Not documented (assume no)
- **Notes**: Supports `parallel_tool_calls=False` parameter

### Provider: Google Gemini
- **Class**: `ChatGoogleGenerativeAI` (from `langchain_google_genai`)
- **Required params**: `model` (string, e.g., "gemini-3.7-flash")
- **Optional params**: `temperature`, `max_tokens`, `timeout`, `max_retries`, `api_key`
- **API key env var**: `GOOGLE_API_KEY`
- **Base URL support**: Not documented (assume no)
- **Notes**: None found in documentation

### Provider: DeepSeek (OpenAI-compatible)
- **Class**: `ChatOpenAI` (from `langchain_openai`)
- **Required params**: `model`, `base_url`, `api_key`
- **Optional params**: Same as OpenAI
- **API key env var**: `DEEPSEEK_API_KEY` (custom)
- **Base URL support**: **Required** via `base_url` parameter
- **Notes**: Not officially documented in LangChain; use OpenAI-compatible pattern

### Provider: Zhipu (OpenAI-compatible)
- **Class**: `ChatOpenAI` (from `langchain_openai`)
- **Required params**: `model`, `base_url`, `api_key`
- **Optional params**: Same as OpenAI
- **API key env var**: `ZHIPUAI_API_KEY` (custom)
- **Base URL support**: **Required** via `base_url` parameter
- **Notes**: Not officially documented in LangChain; use OpenAI-compatible pattern

### Provider: OpenAI-Compatible (Generic)
- **Class**: `ChatOpenAI` (from `langchain_openai`)
- **Required params**: `model`, `base_url`, `api_key`
- **Optional params**: Same as OpenAI
- **API key env var**: Provider-specific (not standardized)
- **Base URL support**: **Required** via `base_url` parameter
- **Notes**: For vLLM, Together AI, and other OpenAI-compatible APIs

**Implementation Note**: For DeepSeek, Zhipu, and OpenAI-compatible providers, use `ChatOpenAI` class with custom `base_url`. API keys come from environment variables named `{PROVIDER}_API_KEY`.

**Alternatives Considered**:
- Direct provider SDKs (rejected: violates 宪法第 II/IV 条, must use LangChain abstraction)
- `init_chat_model()` helper (considered, but explicit class instantiation provides better type safety and error messages)

---

## Decision 2: LangGraph StateGraph Compilation Protocol

**Question**: How to properly inject reducers, middleware, tools into StateGraph before compilation?

**Research Findings**:

### StateGraph Constructor
```python
from langgraph.graph import StateGraph
from typing_extensions import TypedDict

class AgentState(TypedDict):
    messages: list
    todos: list

builder = StateGraph(AgentState)
```

### Custom Reducers with Annotated
```python
from typing import Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    todos: Annotated[list, replace_with_merge]  # Custom reducer
```

### Adding Nodes and Edges
```python
from langgraph.graph import START, END

builder.add_node("node_name", node_function)
builder.add_edge(START, "first_node")
builder.add_conditional_edges("node_a", routing_function, {True: "node_b", False: "node_c"})
```

### Middleware (Runtime Context)
LangGraph uses **Runtime context** instead of traditional middleware:
```python
from langgraph.runtime import Runtime
from dataclasses import dataclass

@dataclass
class ContextSchema:
    user_id: str

def node_with_context(state: AgentState, runtime: Runtime[ContextSchema]):
    print(f"User: {runtime.context.user_id}")
    return {"result": "done"}

builder = StateGraph(AgentState, context_schema=ContextSchema)
```

**IMPORTANT FINDING**: LangGraph does NOT have an "AgentMiddleware protocol" as assumed in the spec. The spec references `AgentMiddleware` from LangChain, but LangGraph uses **Runtime context** for cross-cutting concerns. F01 implementation must adapt the MiddlewareSpec (user-defined middleware in `agent_dir/middleware/`) to LangGraph's Runtime context pattern.

### Tool Binding
Tools bind to the **model**, not the graph:
```python
from langchain.tools import tool

@tool
def multiply(a: int, b: int) -> int:
    return a * b

model_with_tools = model.bind_tools([multiply])

def llm_node(state: AgentState):
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}
```

### Compilation with Checkpoint
```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
```

**Implementation Note**: 
1. Reducers defined via `Annotated[type, reducer_func]` in TypedDict
2. Middleware pattern in spec must be translated to LangGraph Runtime context
3. Tools bind to model before passing model to graph nodes
4. Checkpoint passed to `compile(checkpointer=...)`

**Alternatives Considered**:
- Direct LangChain middleware hooks (incompatible with LangGraph execution model)
- Post-processing middleware (rejected: violates LangGraph's atomic state updates)

---

## Decision 3: Middleware Loading Best Practices

**Question**: How to use `importlib.util.spec_from_file_location` without sys.path pollution?

**Research Findings**:

### Correct Pattern
```python
import importlib.util
import sys
from pathlib import Path

def load_middleware_module(middleware_path: Path, middleware_name: str):
    # Step 1: Unique namespace
    unique_name = f"langagent_dynamic_middleware_{middleware_name}"
    
    # Step 2: Create spec
    spec = importlib.util.spec_from_file_location(unique_name, str(middleware_path))
    
    # Step 3: Create module
    module = importlib.util.module_from_spec(spec)
    
    # Step 4: Register BEFORE execution (critical for circular imports)
    sys.modules[unique_name] = module
    
    # Step 5: Execute module code
    spec.loader.exec_module(module)
    
    return module

def unload_middleware_module(middleware_name: str):
    unique_name = f"langagent_dynamic_middleware_{middleware_name}"
    sys.modules.pop(unique_name, None)
```

### Context Manager Pattern (Recommended)
```python
from contextlib import contextmanager

@contextmanager
def middleware_context(middleware_path: Path, middleware_name: str):
    module = load_middleware_module(middleware_path, middleware_name)
    try:
        yield module
    finally:
        unload_middleware_module(middleware_name)
```

**Why sys.path.insert() is Forbidden**:
1. Global pollution: affects ALL imports process-wide
2. Shadowing risks: can override stdlib or installed packages
3. Irreversible caching: `sys.modules` cache persists even after removal
4. Race conditions: non-deterministic in multi-threaded environments
5. Violates isolation: different middleware shouldn't affect each other

**Implementation Note**: Use context manager pattern for automatic cleanup. Register in `sys.modules` BEFORE `exec_module()` to support circular imports.

**Alternatives Considered**:
- `exec()` with namespace dict (rejected: doesn't support relative imports)
- `sys.path.append()` + cleanup (rejected: still pollutes global state during execution)

---

## Decision 4: Checkpoint Retry Mechanisms

**Question**: How to implement 3-retry with 1s intervals for PostgresSaver network interruptions?

**Research Findings**:

### Network Exception Detection
```python
from psycopg2 import OperationalError, InterfaceError

POSTGRES_NETWORK_EXCEPTIONS = (
    OperationalError,   # Connection lost, timeout, server unreachable
    InterfaceError,     # Protocol errors, malformed responses
    ConnectionError,    # Socket-level connection issues
    OSError,            # Broken pipe, connection reset
)
```

### Manual Implementation (Recommended)
```python
import time
from langagent.cross_cutting.logger import emit

def postgres_with_retry(operation_name: str, operation_func, *args, **kwargs):
    max_attempts = 3
    retry_interval = 1.0  # seconds
    
    for attempt in range(1, max_attempts + 1):
        try:
            emit("la.runtime.checkpoint.attempt", {
                "operation": operation_name,
                "attempt": attempt,
                "max_attempts": max_attempts
            })
            
            result = operation_func(*args, **kwargs)
            
            if attempt > 1:
                emit("la.runtime.checkpoint.retry_success", {
                    "operation": operation_name,
                    "succeeded_on_attempt": attempt
                })
            
            return result
            
        except POSTGRES_NETWORK_EXCEPTIONS as e:
            if attempt < max_attempts:
                emit("la.runtime.checkpoint.retry_attempt", {
                    "operation": operation_name,
                    "attempt": attempt,
                    "error": str(e),
                    "retry_in": retry_interval
                })
                time.sleep(retry_interval)
            else:
                emit("la.runtime.checkpoint.retry_exhausted", {
                    "operation": operation_name,
                    "total_attempts": max_attempts,
                    "final_error": str(e)
                })
                raise GraphCompileError(
                    f"PostgreSQL checkpoint operation '{operation_name}' failed "
                    f"after {max_attempts} attempts: {e}"
                ) from e
```

**Why Manual Implementation**:
- Provides thread ID context in all logs
- Fine-grained control per operation type
- Easy testing and debugging
- No external dependencies (tenacity/retrying)
- Simple to extend with circuit breaker patterns later

**When to Give Up**:
- Max attempts reached (3)
- Non-retryable exception (authentication, permissions, syntax errors)
- Permanent failure indicators in error messages

**Implementation Note**: Fixed 1s interval chosen over exponential backoff because network interruptions are typically transient (<2s). Checkpoints need fast recovery, not gradual backoff.

**Alternatives Considered**:
- Decorator pattern (rejected: less flexible for varied retry logic)
- `tenacity` library (rejected: adds dependency, overkill for simple retry)
- Exponential backoff (rejected: overkill for transient network issues)

---

## Decision 5: SQLite Integrity Check

**Question**: How to execute `PRAGMA integrity_check` and handle repair failures?

**Research Findings**:

### **CRITICAL FINDING**: PRAGMA integrity_check DOES NOT REPAIR

`PRAGMA integrity_check` is a **read-only diagnostic tool**. It detects corruption but never modifies the database.

### Return Values
```python
import sqlite3

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("PRAGMA integrity_check")
results = cursor.fetchall()

# Success: [("ok",)]
# Failure: [("database disk image is malformed",), ("page 5 is never used",), ...]
```

### Actual Repair Strategy: Dump and Restore
```python
def repair_sqlite_database(db_path: str) -> None:
    """Attempt to repair SQLite database by dumping and restoring."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Step 1: Check integrity
    cursor.execute("PRAGMA integrity_check")
    results = cursor.fetchall()
    
    if len(results) == 1 and results[0][0] == "ok":
        return  # Database is healthy
    
    # Step 2: Extract issues
    issues = [row[0] for row in results]
    emit("la.runtime.checkpoint.sqlite_corruption_detected", {
        "db_path": db_path,
        "issue_count": len(issues),
        "first_issue": issues[0]
    })
    
    # Step 3: Attempt dump/restore repair
    backup_path = f"{db_path}.recovery"
    try:
        sql_dump = list(conn.iterdump())
        
        new_conn = sqlite3.connect(backup_path)
        new_conn.executescript('\n'.join(sql_dump))
        new_conn.close()
        conn.close()
        
        # Replace original with repaired version
        import os
        os.replace(backup_path, db_path)
        
        emit("la.runtime.checkpoint.sqlite_repair_success", {
            "db_path": db_path,
            "dump_lines": len(sql_dump)
        })
        return
        
    except Exception as e:
        emit("la.runtime.checkpoint.sqlite_repair_fail", {
            "db_path": db_path,
            "error": str(e)
        })
        
        # Clean up failed backup
        if os.path.exists(backup_path):
            os.remove(backup_path)
        
        # Repair failed - raise GraphCompileError (no backup file per clarification Q2)
        raise GraphCompileError(
            f"SQLite checkpoint database corruption detected and cannot be repaired. "
            f"Found {len(issues)} integrity violations. First issue: {issues[0]}"
        ) from e
```

**Exceptions During Check**:
- `sqlite3.DatabaseError`: File not a database, disk I/O error
- `sqlite3.OperationalError`: Database locked, can't open file
- `sqlite3.Error`: Generic SQLite errors

**Implementation Note**: "Repair" means dump → restore, not in-place fix. No backup files created per clarification Q2. User must handle data loss from corruption.

**Alternatives Considered**:
- `REINDEX` (only fixes index corruption, not data corruption)
- Manual schema repair (dangerous, unreliable)
- Skip integrity check (rejected: silent data corruption is worse than visible failure)

---

## Decision 6: Reducer Type Conversion

**Question**: What type conversions are safe for todos/files/context/scratchpad fields?

**Research Findings**:

### Common LLM Output Mistakes
1. String instead of list: `"todo: fix bug"` instead of `[{"description": "fix bug"}]`
2. Dict instead of list: `{"description": "fix bug"}` instead of `[{"description": "fix bug"}]`
3. Incomplete JSON: `[{"desc": "fix bug"` (missing closing brackets)
4. Wrong nesting: `["string1", "string2"]` instead of `[{"desc": "string1"}, ...]`

### Type Conversion Decision Table

| Input Type | Expected Type | Conversion Strategy | Fallback |
|------------|---------------|---------------------|----------|
| `str` | `list[dict]` (todos) | Parse JSON → validate/convert → wrap single dict | Return `current` |
| `dict` | `list[dict]` (todos) | Wrap in list: `[dict]` | Return `current` |
| `None` | `list[dict]` (todos) | Return `current or []` | Empty list `[]` |
| `list[str]` | `list[dict]` (todos) | Convert each: `{"description": str}` | Return `current` |
| `str` | `dict[str, dict]` (files) | Parse JSON → validate nested structure | Return `current` |
| `list` | `dict[str, dict]` (files) | Extract keys from `path`/`name`/`id` fields | Return `current` |
| `str` | `dict[str, Any]` (context) | Parse JSON → validate | Return `current` |
| `list` | `dict[str, Any]` (context) | Index-keyed dict: `{"0": item, "1": item}` | Return `current` |
| Partial JSON | Any | Repair: add brackets, fix quotes, remove trailing commas | Return `current` |

### JSON Repair Utility
```python
import re

def _repair_incomplete_json(json_str: str) -> str:
    """Attempt to repair incomplete/malformed JSON."""
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

### When to Give Up
1. After 1 conversion attempt fails (fail fast, no retry)
2. Input type completely unexpected (int, bool, bytes)
3. JSON repair fails after bracket/brace matching
4. Sanitization drops all items (e.g., `list[int]` for todos)

### Logging Strategy
```python
# Log BEFORE attempting conversion
emit("la.runtime.graph_compose.reducer_conversion_attempt", {
    "field": "todos",
    "input_type": "str",
    "strategy": "json_parse"
})

# Log when conversion fails
emit("la.runtime.graph_compose.reducer_conversion_fail", {
    "field": "todos",
    "input_type": "str",
    "expected_type": "list[dict]",
    "error": str(e)
})

# Log when dropping invalid items
emit("la.runtime.graph_compose.reducer_sanitization", {
    "field": "files",
    "dropped_key": "invalid_entry",
    "reason": "unsupported_nested_type"
})
```

**Implementation Note**: Emit logs to help debug LLM output issues. All reducers comply with FR-040: never raise exceptions, degrade gracefully to `current` state.

**Alternatives Considered**:
- Strict type checking without conversion (rejected: breaks with "智力低下" LLMs per clarification Q4)
- Silent conversion without logging (rejected: makes debugging impossible)
- Retry multiple conversion strategies (rejected: adds complexity, diminishing returns)

---

## Phase 0 Summary

All 6 research questions resolved. Key design constraints identified:

1. **LangGraph middleware misconception**: Spec assumes `AgentMiddleware` protocol exists in LangGraph; actual pattern is Runtime context
2. **SQLite repair limitation**: PRAGMA only detects, repair requires dump/restore
3. **Reducer defensive coding**: Must handle LLM output mistakes with type conversion
4. **Network retry simplicity**: Fixed 1s intervals sufficient for transient interruptions
5. **Importlib isolation**: Context manager pattern + sys.modules cleanup prevents pollution
6. **Provider mapping**: DeepSeek/Zhipu use OpenAI-compatible pattern with custom base_url

**Next Phase**: Generate data-model.md, contracts/, and quickstart.md based on these findings.
