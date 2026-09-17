# Contract: checkpoint_adapter

**Module**: `langagent.primitives.checkpoint_adapter`  
**Owner**: F01 Primitives Layer  
**Version**: 1.0.0

---

## Overview

The `checkpoint_adapter` module provides factory and cleanup functions for LangGraph checkpoint backends. It supports 3 checkpointer types (memory, sqlite, postgres) and handles backend-specific concerns like SQLite corruption repair and PostgreSQL network retry logic.

---

## Public Interface

### `create(config: RuntimeConfig) -> BaseCheckpointSaver`

Instantiate a checkpointer based on `config.checkpointer`.

**Supported Types** (FR-024):
- `memory`: In-memory checkpoint (no persistence, lost on process exit)
- `sqlite`: SQLite file-based checkpoint (local persistence)
- `postgres`: PostgreSQL checkpoint (networked persistence)

**Parameters**:
- `config: RuntimeConfig` - Frozen configuration snapshot containing:
  - `checkpointer: str` - One of 3 supported values
  - `checkpoint_sqlite_path: str | None` - Required when checkpointer="sqlite"
  - `checkpoint_postgres_dsn: str | None` - Required when checkpointer="postgres"

**Returns**:
- `BaseCheckpointSaver` - Instantiated checkpointer ready for graph compilation

**Raises**:
- `CheckpointTypeUnsupportedError` (exit code 78) - `checkpointer` not in 3 supported values (FR-028)
- `GraphCompileError` (exit code 70) - SQLite corruption repair failed OR postgres connection failed after retries

**Side Effects**:
- **SQLite** (clarification Q2):
  - Executes `PRAGMA integrity_check` to detect corruption (FR-026)
  - Attempts dump/restore repair if corruption detected (research.md Decision 5)
  - No backup file creation per clarification Q2
  - Raises `GraphCompileError` if repair fails
- **Postgres** (clarification Q5):
  - Implements 3-retry mechanism with 1s intervals for network interruptions (FR-027)
  - Retries on `OperationalError`, `InterfaceError`, `ConnectionError`, `OSError`
  - Raises `GraphCompileError` only after all retries exhausted (research.md Decision 4)
- **Memory**:
  - No side effects, pure instantiation

---

### `close(saver: BaseCheckpointSaver) -> None`

Close checkpointer connections and release resources.

**Parameters**:
- `saver: BaseCheckpointSaver` - Checkpointer instance from `create()`

**Returns**:
- `None`

**Raises**:
- Propagates exceptions from underlying checkpoint backend (no silent swallowing)

**Side Effects** (FR-029):
- **Memory**: No-op (FR-030)
- **SQLite**: Release file lock, close connection
- **Postgres**: Close connection pool

**Usage Note**: F09 `runtime_exit_handler` calls this during cleanup phase (stage 6 of workflow.md).

---

## Implementation Details

### Memory Checkpointer (FR-025)

```python
from langgraph.checkpoint.memory import MemorySaver

def create_memory(config: RuntimeConfig) -> MemorySaver:
    return MemorySaver()

def close_memory(saver: MemorySaver) -> None:
    pass  # No-op
```

---

### SQLite Checkpointer (FR-026, clarification Q2)

```python
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
import os

def create_sqlite(config: RuntimeConfig) -> SqliteSaver:
    db_path = config.checkpoint_sqlite_path
    
    # Step 1: Check integrity (research.md Decision 5)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA integrity_check")
    results = cursor.fetchall()
    
    if len(results) == 1 and results[0][0] == "ok":
        conn.close()
        return SqliteSaver.from_conn_string(db_path)
    
    # Step 2: Corruption detected - attempt repair
    issues = [row[0] for row in results]
    emit("la.runtime.checkpoint.sqlite_corruption_detected", {
        "db_path": db_path,
        "issue_count": len(issues),
        "first_issue": issues[0]
    })
    
    # Step 3: Dump and restore (PRAGMA does NOT repair, only detects)
    backup_path = f"{db_path}.recovery"
    try:
        sql_dump = list(conn.iterdump())
        new_conn = sqlite3.connect(backup_path)
        new_conn.executescript('\n'.join(sql_dump))
        new_conn.close()
        conn.close()
        
        os.replace(backup_path, db_path)
        
        emit("la.runtime.checkpoint.sqlite_repair_success", {
            "db_path": db_path,
            "dump_lines": len(sql_dump)
        })
        
        return SqliteSaver.from_conn_string(db_path)
    
    except Exception as e:
        # Clean up failed backup (no backup file per clarification Q2)
        if os.path.exists(backup_path):
            os.remove(backup_path)
        
        emit("la.runtime.checkpoint.sqlite_repair_fail", {
            "db_path": db_path,
            "error": str(e)
        })
        
        raise GraphCompileError(
            f"SQLite checkpoint database corruption detected and cannot be repaired. "
            f"Found {len(issues)} integrity violations. First issue: {issues[0]}"
        ) from e

def close_sqlite(saver: SqliteSaver) -> None:
    saver.conn.close()
```

**Critical Finding** (research.md Decision 5): `PRAGMA integrity_check` is read-only. It detects corruption but does NOT repair. Actual repair requires dump/restore.

---

### PostgreSQL Checkpointer (FR-027, clarification Q5)

```python
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg2 import OperationalError, InterfaceError
import time

POSTGRES_NETWORK_EXCEPTIONS = (
    OperationalError,   # Connection lost, timeout, server unreachable
    InterfaceError,     # Protocol errors
    ConnectionError,    # Socket-level issues
    OSError,            # Broken pipe, connection reset
)

def create_postgres(config: RuntimeConfig) -> PostgresSaver:
    dsn = config.checkpoint_postgres_dsn
    
    # Retry logic (research.md Decision 4)
    max_attempts = 3
    retry_interval = 1.0  # seconds
    
    for attempt in range(1, max_attempts + 1):
        try:
            emit("la.runtime.checkpoint.attempt", {
                "operation": "postgres_connect",
                "attempt": attempt,
                "max_attempts": max_attempts
            })
            
            saver = PostgresSaver.from_conn_string(dsn)
            
            if attempt > 1:
                emit("la.runtime.checkpoint.retry_success", {
                    "operation": "postgres_connect",
                    "succeeded_on_attempt": attempt
                })
            
            return saver
        
        except POSTGRES_NETWORK_EXCEPTIONS as e:
            if attempt < max_attempts:
                emit("la.runtime.checkpoint.retry_attempt", {
                    "operation": "postgres_connect",
                    "attempt": attempt,
                    "error": str(e),
                    "retry_in": retry_interval
                })
                time.sleep(retry_interval)
            else:
                emit("la.runtime.checkpoint.retry_exhausted", {
                    "operation": "postgres_connect",
                    "total_attempts": max_attempts,
                    "final_error": str(e)
                })
                raise GraphCompileError(
                    f"PostgreSQL checkpoint connection failed after {max_attempts} attempts: {e}"
                ) from e

def close_postgres(saver: PostgresSaver) -> None:
    saver.conn.close()
```

**Retry Strategy** (clarification Q5): Fixed 1s intervals (not exponential backoff) because network interruptions are typically transient (<2s). Checkpoints need fast recovery.

---

## Usage Example

```python
from langagent.primitives.checkpoint_adapter import create, close
from langagent.runtime.config import RuntimeConfig

# Memory checkpointer
config = RuntimeConfig(checkpointer="memory", ...)
checkpoint = create(config)
# ... use checkpoint in graph compilation ...
close(checkpoint)  # No-op for memory

# SQLite checkpointer
config = RuntimeConfig(
    checkpointer="sqlite",
    checkpoint_sqlite_path="/tmp/agent_state.db",
    ...
)
checkpoint = create(config)  # Auto-repairs corruption if detected
# ... use checkpoint ...
close(checkpoint)  # Releases file lock

# Postgres checkpointer
config = RuntimeConfig(
    checkpointer="postgres",
    checkpoint_postgres_dsn="postgresql://user:pass@localhost/langagent",
    ...
)
checkpoint = create(config)  # Retries 3 times on network error
# ... use checkpoint ...
close(checkpoint)  # Closes connection pool
```

---

## Testing Contract

### Unit Tests

1. `test_create_memory` - Returns `MemorySaver` instance
2. `test_create_sqlite_healthy_db` - SQLite with intact database
3. `test_create_sqlite_corrupted_db` - SQLite with corrupted db, successful repair
4. `test_create_sqlite_unrepairable_db` - SQLite corruption, repair fails, raises `GraphCompileError`
5. `test_create_postgres_success` - Postgres with valid DSN
6. `test_create_postgres_retry_success` - Postgres network failure, succeeds on retry 2
7. `test_create_postgres_retry_exhausted` - Postgres network failure, all retries exhausted, raises `GraphCompileError`
8. `test_create_unsupported_checkpointer` - Raises `CheckpointTypeUnsupportedError`
9. `test_close_memory_no_op` - Memory close completes without error
10. `test_close_sqlite_releases_lock` - SQLite close releases file lock (verify via file descriptor count)
11. `test_close_postgres_closes_pool` - Postgres close closes connection

### Integration Tests

1. `test_checkpoint_roundtrip_sqlite` - Create sqlite checkpoint, persist state, close, reopen, verify state
2. `test_checkpoint_roundtrip_postgres` - Same for postgres (skip if no postgres available)

---

## Dependencies

**Imports**:
```python
from langagent.runtime.config import RuntimeConfig
from langagent.primitives.langchain_types import BaseCheckpointSaver
from langagent.primitives.exceptions import CheckpointTypeUnsupportedError, GraphCompileError
from langagent.cross_cutting.logger import emit

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresSaver

import sqlite3
import os
import time
from psycopg2 import OperationalError, InterfaceError
```

---

## Version History

- **1.0.0** (2026-09-17): Initial contract definition
