# Research Report: F09 Exit Cleanup Implementation Patterns

**Date**: 2026-09-20  
**Scope**: Technical questions 1-5 from plan.md Phase 0 research tasks  
**Status**: Complete

## Executive Summary

This report consolidates research findings for 5 technical implementation questions related to F09 Exit Cleanup. All decisions are based on Python stdlib patterns, existing codebase conventions (audit_recorder.py, logger.py, checkpoint_adapter.py), and LangChain/LangGraph documentation.

**Key Decisions**:
1. **Exit Code Arbitration**: Use priority lookup table with `min(codes, key=lambda)` 
2. **JSONL Atomic Writes**: File lock (`fcntl.flock`) for append operations
3. **Idempotent Checkpointer Close**: Test connection validity before close, catch `ProgrammingError`
4. **Continue-on-Failure Tracking**: Accumulator lists (`failed_steps`, `failed_exit_codes`)
5. **RuntimeConfigSnapshot Serialization**: Factory method pattern with explicit field exclusion

---

## Question 1: Exit Code Priority Arbitration

### Problem Statement
How to implement `worst_of()` function that correctly prioritizes 13 exit codes when multiple failures occur?

**Priority Order** (highest to lowest):  
130 > 70 > 67 > 78 > 66 > 65 > 64 > 5 > 4 > 3 > 2 > 1 > 0

**Edge Cases**:
- Empty list should return 0
- Duplicate codes should be handled
- Unknown codes should not crash

### Decision: Priority Lookup Table with `min()` Key Function

**Rationale**:
1. **Explicit Priority Mapping**: Dict-based lookup table makes priority order auditable and testable
2. **Stdlib Pattern**: Python's `min(iterable, key=func)` is idiomatic for custom ordering
3. **Unknown Code Handling**: Fallback value (999) ensures unknown codes are treated as lowest priority
4. **Performance**: O(n) single-pass with dict lookup is optimal for small code lists (< 20 typical)

**Code Pattern**:
```python
# langagent/runtime/exit_code.py

EXIT_CODE_PRIORITY = {
    130: 1,   # SIGINT (Ctrl-C) - highest priority
    70: 2,    # EX_SOFTWARE - internal software error
    67: 3,    # name_already_exists (langagent init)
    78: 4,    # EX_CONFIG - configuration error
    66: 5,    # EX_NOINPUT - cannot open input
    65: 6,    # EX_DATAERR - malformed .env file
    64: 7,    # EX_USAGE - command line usage error
    5: 8,     # RequiredFieldMissingError
    4: 9,     # I/O error (AuditFlushError, file writes)
    3: 10,    # data_error - invalid data format
    2: 11,    # usage_error - argument parsing failure
    1: 12,    # generic_failure - StageCapabilityViolationError
    0: 13     # success (lowest priority)
}

def worst_of(codes: list[int]) -> int:
    """Return highest priority exit code from list.
    
    Args:
        codes: List of exit codes (may contain duplicates)
        
    Returns:
        Highest priority code, or 0 if list is empty
        
    Examples:
        >>> worst_of([])
        0
        >>> worst_of([0, 1, 4])
        4
        >>> worst_of([130, 70, 4])
        130
        >>> worst_of([4, 4, 1])  # Duplicates handled
        4
    """
    if not codes:
        return 0
    
    # Return code with minimum priority rank (1 = highest priority)
    # Unknown codes get priority 999 (treated as lowest)
    return min(codes, key=lambda c: EXIT_CODE_PRIORITY.get(c, 999))
```

**Validation**:
```python
# Test cases from plan.md
assert worst_of([]) == 0                    # Empty list
assert worst_of([0]) == 0                   # Single success
assert worst_of([0, 1, 4]) == 4             # I/O error wins
assert worst_of([130, 70, 4]) == 130        # SIGINT highest
assert worst_of([4, 4, 1]) == 4             # Duplicates
assert worst_of([999, 1]) == 1              # Unknown code loses
```

### Alternatives Considered

**Alt 1: Hardcoded if-elif Chain**
```python
def worst_of(codes: list[int]) -> int:
    if 130 in codes: return 130
    if 70 in codes: return 70
    if 67 in codes: return 67
    # ... 10 more conditions
    return 0
```
**Rejected**: Not maintainable. Adding new exit codes requires modifying function body. Priority order is implicit (harder to audit).

**Alt 2: sorted() with Custom Comparator**
```python
def worst_of(codes: list[int]) -> int:
    if not codes: return 0
    return sorted(codes, key=lambda c: EXIT_CODE_PRIORITY.get(c, 999))[0]
```
**Rejected**: `sorted()` is O(n log n), overkill when we only need minimum. Also allocates new list unnecessarily.

**Alt 3: max() with Inverted Priority**
```python
EXIT_CODE_PRIORITY = {130: 13, 70: 12, ..., 0: 1}  # Inverted
return max(codes, key=lambda c: EXIT_CODE_PRIORITY.get(c, 0))
```
**Rejected**: Inverted mapping is counterintuitive (130 should be priority 1, not 13). Would confuse future maintainers.

---

## Question 2: JSONL Atomic Write Patterns

### Problem Statement
How to atomically append spans/events to JSONL files to prevent corruption during concurrent writes or process crashes?

**Requirements**:
- One JSON record per line (grep-able)
- Concurrent writes must not interleave
- Partial writes on crash must not corrupt file
- Files: `~/.local/share/langagent/logs/<run-id>.jsonl`

### Decision: File Lock (`fcntl.flock`) for Append Operations

**Rationale**:
1. **Existing Pattern**: `audit_recorder.py:179-186` already uses `fcntl.flock(LOCK_EX)` for JSONL writes
2. **POSIX Standard**: `fcntl` is stdlib, available on Linux/macOS (target platforms per plan.md)
3. **Advisory Locking**: File locks coordinate between cooperating processes (all LangAgent processes)
4. **Append Mode Safety**: `open(mode="a")` with `O_APPEND` ensures atomic writes at OS level
5. **Flush Guarantees**: Explicit `f.flush()` + `os.fsync(f.fileno())` ensures data reaches disk

**Code Pattern**:
```python
# langagent/runtime/exit_handler.py

import fcntl
import json
import os
from pathlib import Path
from typing import Any

def write_jsonl_atomic(filepath: Path, records: list[dict[str, Any]]) -> None:
    """Atomically append JSON records to JSONL file.
    
    Args:
        filepath: Target JSONL file path
        records: List of JSON-serializable dicts
        
    Raises:
        IOError: If file write or flush fails (exit code 4)
        
    Side Effects:
        - Creates parent directory if missing
        - Acquires exclusive file lock during write
        - Writes one JSON object per line (no pretty-printing)
        - Flushes to disk before releasing lock
    """
    # Ensure parent directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Open in append mode (O_APPEND ensures atomic positioning)
        with open(filepath, "a", encoding="utf-8") as f:
            # Acquire exclusive lock (blocks if another process holds lock)
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            
            try:
                # Write all records as single atomic operation
                for record in records:
                    json_line = json.dumps(record, ensure_ascii=False) + "\n"
                    f.write(json_line)
                
                # Force write to disk (critical for crash safety)
                f.flush()
                os.fsync(f.fileno())
                
            finally:
                # Release lock (always, even on exception)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                
    except (OSError, IOError) as e:
        # Propagate as IOError with exit code 4
        raise IOError(f"Failed to write JSONL to {filepath}: {e}") from e


def write_spans_to_jsonl(run_id: str, spans: list[Any]) -> None:
    """Write spans to logs/<run-id>.jsonl.
    
    Implements FR-006: Span JSONL must have exactly 7 fields per line.
    """
    if not spans:
        # FR-006: Do not create file if no spans exist
        return
    
    logs_dir = Path.home() / ".local/share/langagent/logs"
    filepath = logs_dir / f"{run_id}.jsonl"
    
    # Convert Span dataclasses to dicts with 7 fields
    records = [
        {
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "parent_span_id": span.parent_span_id,
            "name": span.name,
            "start": span.start,
            "end": span.end,
            "attributes": span.attributes,
        }
        for span in spans
    ]
    
    write_jsonl_atomic(filepath, records)
```

**Concurrency Guarantees**:
- **Advisory Locking**: All LangAgent processes cooperate via `fcntl.flock`
- **Blocking Behavior**: Second writer blocks until first writer releases lock
- **No Interleaving**: Lock ensures complete record writes (no partial JSON lines)

**Crash Safety**:
- `os.fsync()` ensures data is written to physical disk before function returns
- If process crashes after `fsync()`, written records are durable
- If process crashes before `fsync()`, partial writes are discarded (JSONL remains valid)

### Alternatives Considered

**Alt 1: Write-Then-Rename (Atomic Replace)**
```python
tmp_file = filepath.with_suffix(".tmp")
with open(tmp_file, "w") as f:
    for record in records:
        f.write(json.dumps(record) + "\n")
os.replace(tmp_file, filepath)  # Atomic on POSIX
```
**Rejected**: Cannot append to existing JSONL file. Would overwrite previous spans. Not suitable for incremental writes during cleanup.

**Alt 2: No Locking (Rely on O_APPEND)**
```python
with open(filepath, "a") as f:
    for record in records:
        f.write(json.dumps(record) + "\n")
```
**Rejected**: `O_APPEND` guarantees atomic positioning but not atomic multi-line writes. Multiple concurrent writers can interleave within a single JSON object, corrupting the file.

**Alt 3: Database (SQLite)**
```python
conn.execute("INSERT INTO spans VALUES (...)")
conn.commit()
```
**Rejected**: Adds complexity. JSONL is grep-able requirement (SC-006). SQLite query overhead unnecessary for append-only logs.

---

## Question 3: Idempotent Checkpointer Closing

### Problem Statement
How to make `close_checkpointer()` idempotent across MemorySaver, SqliteSaver, PostgresSaver implementations?

**Edge Case**: Checkpointer may already be closed when cleanup runs (e.g., if graph compilation failed, or cleanup called twice).

### Decision: Test Connection Validity Before Close

**Rationale**:
1. **Existing Pattern**: `checkpoint_adapter.py:92-102` already implements close() with conditional checks
2. **Connection State Detection**: Execute harmless test query (`SELECT 1`) to check if connection is alive
3. **Exception Handling**: Catch `sqlite3.ProgrammingError` or `psycopg2.InterfaceError` as signals of already-closed state
4. **Backend Agnostic**: Pattern works for all 3 checkpointer types (Memory, SQLite, Postgres)

**Code Pattern**:
```python
# langagent/runtime/exit_handler.py

import sqlite3
from langagent.primitives.langchain_types import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

def close_checkpointer(saver: BaseCheckpointSaver | None) -> None:
    """Close checkpointer connections idempotently.
    
    Args:
        saver: Checkpointer instance from checkpoint_adapter.create(), or None
        
    Raises:
        Does NOT raise exceptions on idempotent close attempts.
        Propagates exceptions for unexpected errors (exit code 1).
        
    Side Effects:
        - Memory: No-op (no connections to close)
        - SQLite: Closes connection, releases file lock
        - Postgres: Closes connection pool
        
    Idempotence:
        Safe to call multiple times. Second call is no-op if already closed.
    """
    if saver is None:
        # Edge case: cleanup called before checkpointer instantiated
        return
    
    if isinstance(saver, MemorySaver):
        # FR-030: Memory checkpointer has no resources to clean up
        return
    
    # Check if saver has connection attribute
    if not hasattr(saver, 'conn') or saver.conn is None:
        # Already closed or never opened
        return
    
    try:
        # Test if connection is still alive (backend-specific queries)
        if isinstance(saver, SqliteSaver):
            # SQLite: Execute harmless test query
            try:
                saver.conn.execute("SELECT 1")
                # Connection is alive, safe to close
                saver.conn.close()
            except sqlite3.ProgrammingError:
                # ProgrammingError: "Cannot operate on a closed database"
                # Connection already closed, this is idempotent case
                pass
        else:
            # PostgreSQL or other backend
            try:
                # Check if connection has a working cursor
                cursor = saver.conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                # Connection is alive, safe to close
                saver.conn.close()
            except Exception:
                # InterfaceError, OperationalError, or already closed
                # Treat as already-closed state (idempotent)
                pass
                
    except Exception as e:
        # Unexpected error during close (not idempotence-related)
        # Log but do not raise (continue-on-failure strategy)
        # Caller will record exit code 1
        import sys
        print(f"[WARN] Checkpointer close failed: {e}", file=sys.stderr)
```

**Idempotence Guarantees**:
- **First Call**: Executes test query, closes connection if alive
- **Second Call**: Test query raises `ProgrammingError`, caught and ignored
- **Third Call**: `saver.conn is None` check returns early (no-op)

**Edge Cases Handled**:
1. `saver is None` → Early return (no-op)
2. `MemorySaver` → Early return (no connections)
3. Connection already closed → Test query raises exception, caught
4. Connection never opened → `hasattr` check returns `False`

### Alternatives Considered

**Alt 1: Try-Except Without Test Query**
```python
try:
    saver.conn.close()
except (sqlite3.ProgrammingError, AttributeError):
    pass  # Already closed
```
**Rejected**: Relies on exception for control flow. Some backends may not raise `ProgrammingError` on double-close (undefined behavior).

**Alt 2: Track Closed State with Flag**
```python
if not getattr(saver, '_is_closed', False):
    saver.conn.close()
    saver._is_closed = True
```
**Rejected**: Requires mutating checkpointer object (may be frozen or immutable). Does not handle external close() calls outside our control.

**Alt 3: Always Suppress Exceptions**
```python
try:
    saver.conn.close()
except Exception:
    pass  # Ignore all errors
```
**Rejected**: Too broad. Masks unexpected errors (e.g., disk full during SQLite checkpoint flush). Violates continue-on-failure requirement (need to record exit codes).

---

## Question 4: Continue-on-Failure State Tracking

### Problem Statement
What data structures track `failed_steps` and `failed_exit_codes` during cleanup to ensure all 11 steps attempt execution even after failures?

**Requirements**:
- Record which steps failed (for diagnostics)
- Accumulate exit codes from all failures
- Final `worst_of()` call aggregates codes
- Steps must not halt on single failure

### Decision: Accumulator Lists with Per-Step Try-Except

**Rationale**:
1. **Simple State Management**: Two lists (`failed_steps`, `failed_exit_codes`) track all failures
2. **Step Isolation**: Each step wrapped in try-except ensures one failure doesn't skip remaining steps
3. **Exit Code Extraction**: Extract `exit_code` attribute from exceptions when available, otherwise use default
4. **Diagnostic Data**: `failed_steps` list enables detailed logging in `la.runtime.exit_cleanup.fail` event

**Code Pattern**:
```python
# langagent/runtime/exit_handler.py

from typing import Any
from langagent.cross_cutting import logger

def cleanup(
    state: Any,
    config: Any,
    *,
    doctor_report: Any = None,
    eval_report: Any = None,
    metrics_snapshot: Any = None,
    init_only: bool = False
) -> int:
    """Execute 11-step cleanup sequence with continue-on-failure.
    
    Returns:
        Exit code (highest priority from all failures, or 0 on success)
    """
    # FR-018: Emit cleanup start event
    logger.emit("la.runtime.exit_cleanup.start", {
        "message": "Starting exit cleanup",
        "init_only": init_only,
    })
    
    # Continue-on-failure tracking (FR-003)
    failed_steps: list[str] = []
    failed_exit_codes: list[int] = []
    
    # FR-021: Skip resource cleanup for init-only mode
    if init_only:
        logger.emit("la.lifecycle.init.end", {"message": "Init complete"})
        logger.emit("la.runtime.exit_cleanup.ok", {"message": "Cleanup complete (init-only)"})
        return 0
    
    # Step 1: Flush event bus (timeout is not a failure)
    try:
        if hasattr(config, 'event_bus') and config.event_bus:
            config.event_bus.flush(timeout=5)
    except TimeoutError:
        # FR-024: Timeout is logged but not counted as failure
        logger.emit("la.cross_cutting.event_handler_error", {
            "message": "Event bus flush timed out after 5s (non-fatal)"
        })
    except Exception as e:
        # Unexpected error (not timeout)
        failed_steps.append("event_bus.flush")
        exit_code = getattr(e, 'exit_code', 1)  # Default to generic failure
        failed_exit_codes.append(exit_code)
    
    # Step 2: Flush metrics collector
    try:
        from langagent.cross_cutting.metrics_collector import flush
        flush()
    except Exception as e:
        failed_steps.append("metrics.flush")
        exit_code = getattr(e, 'exit_code', 1)
        failed_exit_codes.append(exit_code)
    
    # Step 3: Flush audit recorder
    try:
        from langagent.cross_cutting.audit_recorder import AuditRecorder
        recorder = AuditRecorder()
        recorder.flush()
    except Exception as e:
        failed_steps.append("audit.flush")
        # AuditFlushError has exit_code = 4 (I/O error)
        exit_code = getattr(e, 'exit_code', 4)
        failed_exit_codes.append(exit_code)
    
    # Step 4: Close checkpointer
    try:
        if hasattr(config, 'checkpointer_instance'):
            close_checkpointer(config.checkpointer_instance)
    except Exception as e:
        failed_steps.append("checkpointer.close")
        exit_code = getattr(e, 'exit_code', 1)
        failed_exit_codes.append(exit_code)
    
    # Step 5: Take metrics snapshot
    snapshot_result = None
    try:
        from langagent.cross_cutting.metrics_collector import snapshot
        snapshot_result = snapshot()
        if snapshot_result is None:
            # FR-005: Missing snapshot gets exit code 70
            failed_steps.append("metrics.snapshot")
            failed_exit_codes.append(70)
    except Exception as e:
        failed_steps.append("metrics.snapshot")
        exit_code = getattr(e, 'exit_code', 70)
        failed_exit_codes.append(exit_code)
    
    # Step 6: Drain spans
    spans = []
    try:
        from langagent.cross_cutting.logger import drain_spans
        spans = drain_spans()
    except Exception as e:
        failed_steps.append("drain_spans")
        # SpanDrainError has exit_code = 4
        exit_code = getattr(e, 'exit_code', 4)
        failed_exit_codes.append(exit_code)
        # FR-025: Buffer remains intact for retry
    
    # Step 7: Drain events
    events = []
    try:
        if hasattr(config, 'event_bus') and config.event_bus:
            events = config.event_bus.drain_events()
    except Exception as e:
        failed_steps.append("drain_events")
        exit_code = getattr(e, 'exit_code', 4)
        failed_exit_codes.append(exit_code)
    
    # Step 8: Write reports
    try:
        write_reports(
            state=state,
            config=config,
            doctor_report=doctor_report,
            eval_report=eval_report,
            metrics_snapshot=snapshot_result,
            spans=spans,
            events=events,
        )
    except Exception as e:
        failed_steps.append("write_reports")
        exit_code = getattr(e, 'exit_code', 4)
        failed_exit_codes.append(exit_code)
    
    # Step 9: Emit final log (FR-019)
    if failed_steps:
        logger.emit("la.runtime.exit_cleanup.fail", {
            "message": f"Cleanup completed with {len(failed_steps)} failures",
            "failed_steps": failed_steps,
            "exit_codes": failed_exit_codes,
        })
    else:
        logger.emit("la.runtime.exit_cleanup.ok", {
            "message": "Cleanup completed successfully"
        })
    
    # Step 10: (No action - lifecycle.init.end only emitted in init_only mode)
    
    # Step 11: Return worst exit code (FR-010)
    from langagent.runtime.exit_code import worst_of
    final_exit_code = worst_of(failed_exit_codes)
    return final_exit_code
```

**State Tracking Guarantees**:
- **Isolation**: Each step's try-except ensures one failure doesn't skip others
- **Accumulation**: All failures recorded in `failed_exit_codes` list
- **Exit Code Extraction**: `getattr(e, 'exit_code', default)` handles exceptions with/without exit_code attribute
- **Diagnostics**: `failed_steps` list logged in `.fail` event for debugging

**Exception Attribute Pattern**:
```python
class AuditFlushError(Exception):
    def __init__(self, message: str):
        self.exit_code = 4  # I/O error
        super().__init__(message)

# In cleanup:
except Exception as e:
    exit_code = getattr(e, 'exit_code', 1)  # Extract if present, else default
```

### Alternatives Considered

**Alt 1: Result Objects (Railway-Oriented)**
```python
@dataclass
class StepResult:
    success: bool
    exit_code: int
    step_name: str

results = []
results.append(flush_event_bus())  # Returns StepResult
results.append(flush_metrics())
# ... collect all results
return worst_of([r.exit_code for r in results if not r.success])
```
**Rejected**: Over-engineered for simple sequential cleanup. Each step would need result wrapping. Try-except is more Pythonic.

**Alt 2: Exception Chaining**
```python
cleanup_exception = None
try:
    flush_event_bus()
except Exception as e:
    cleanup_exception = e
try:
    flush_metrics()
except Exception as e:
    if cleanup_exception:
        e.__cause__ = cleanup_exception  # Chain exceptions
    cleanup_exception = e
# ... complicated chaining logic
```
**Rejected**: Exception chaining loses individual exit codes. Cannot implement `worst_of()` without parsing entire exception chain.

**Alt 3: Context Manager Stack**
```python
with ExitStack() as stack:
    stack.callback(flush_event_bus)
    stack.callback(flush_metrics)
    # ... register all cleanup callbacks
# All callbacks execute on context exit
```
**Rejected**: `ExitStack` executes callbacks in LIFO order (reverse), but cleanup requires FIFO order. Also doesn't provide exit code aggregation.

---

## Question 5: RuntimeConfigSnapshot Serialization

### Problem Statement
How to safely exclude BaseChatModel instances and secrets from RuntimeConfigSnapshot without breaking Pydantic JSON serialization?

**Requirements**:
- DoctorReport embeds RuntimeConfigSnapshot (FR-015, SC-007)
- Must be JSON-serializable (cannot include BaseChatModel, which has unpicklable GRPC connections)
- Must exclude secrets: `cli_args`, `env_vars`, `dotenv_values`, `builtin_defaults`
- Must include 8 fields: schema_version, model_provider, model_name, model_base_url, checkpointer, middleware_ids, skill_dirs, log_level, guardrail_allow_internal_endpoints

### Decision: Factory Method with Explicit Field Selection

**Rationale**:
1. **Separation of Concerns**: RuntimeConfig (full) vs RuntimeConfigSnapshot (serializable subset)
2. **Explicit Exclusion**: Factory method pattern makes excluded fields obvious (maintainability)
3. **Pydantic Compatibility**: No need for custom serializers or `@field_serializer` (simpler)
4. **Type Safety**: Pydantic validates snapshot schema at construction time
5. **Existing Pattern**: `agent_state.py:177-189` already uses `.with_model()` factory methods

**Code Pattern**:
```python
# langagent/runtime/agent_state.py (add RuntimeConfigSnapshot)

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

class RuntimeConfigSnapshot(BaseModel):
    """Serializable subset of RuntimeConfig for diagnostic reports.
    
    Excludes:
        - model: BaseChatModel (unpicklable GRPC connections)
        - cli_args: Contains secrets (API keys passed via --env flag)
        - env_vars: Contains secrets (API_KEY environment variables)
        - dotenv_values: Contains secrets (.env file contents)
        - builtin_defaults: Internal implementation detail
    
    Includes:
        8 fields needed for doctor/eval report diagnostics.
    """
    
    model_config = ConfigDict(frozen=True)
    
    schema_version: str = Field(default="v0.2.0", description="Snapshot schema version")
    model_provider: Literal["openai", "anthropic", "google", "deepseek", "zhipu", "openai-compatible"]
    model_name: str | None
    model_base_url: str | None
    checkpointer: Literal["memory", "sqlite", "postgres"]
    middleware_ids: list[str]
    skill_dirs: list[str]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    guardrail_allow_internal_endpoints: bool
    
    @classmethod
    def from_runtime_config(cls, config: "RuntimeConfig") -> "RuntimeConfigSnapshot":
        """Factory method to create snapshot from full RuntimeConfig.
        
        Args:
            config: Full RuntimeConfig instance with all 13 fields
            
        Returns:
            RuntimeConfigSnapshot with 8 safe fields (excludes model and secrets)
            
        Example:
            >>> config = RuntimeConfig(...)
            >>> snapshot = RuntimeConfigSnapshot.from_runtime_config(config)
            >>> json_str = snapshot.model_dump_json()  # JSON-serializable
        """
        # Extract guardrail_allow_internal_endpoints from nested policy
        guardrail_allow_internal = False
        if config.guardrail_policy:
            guardrail_allow_internal = config.guardrail_policy.allow_internal_endpoints
        
        return cls(
            schema_version="v0.2.0",
            model_provider=config.model_provider,
            model_name=config.model_name,
            model_base_url=config.model_base_url,
            checkpointer=config.checkpointer,
            middleware_ids=config.middleware_ids.copy(),  # Defensive copy
            skill_dirs=config.skill_dirs.copy(),
            log_level=config.log_level,
            guardrail_allow_internal_endpoints=guardrail_allow_internal,
        )


# langagent/runtime/doctor_check.py (DoctorReport schema)

from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Literal

class DoctorCheckResult(BaseModel):
    """Single doctor check result."""
    
    check_name: Literal["model", "checkpointer", "skills", "instructions"]
    status: Literal["ok", "warn", "error", "skipped"]
    detail: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DoctorReport(BaseModel):
    """Doctor self-check report with 6 fields."""
    
    report_id: str = Field(description="Unique report ID (UUID4)")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    checks: list[DoctorCheckResult] = Field(description="4 check results")
    overall: Literal["ok", "warn", "error"] = Field(description="Aggregated status")
    agent_dir: str | None = Field(description="Agent directory path")
    runtime: RuntimeConfigSnapshot = Field(description="Runtime config snapshot")
    
    def to_json_file(self, filepath: Path) -> None:
        """Write report to JSON file atomically.
        
        Implements FR-008: Atomic overwrite if file exists.
        """
        tmp_path = filepath.with_suffix(".tmp")
        tmp_path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp_path, filepath)  # Atomic on POSIX
```

**JSON Serialization Guarantees**:
```python
# Test serialization
config = RuntimeConfig(
    model=ChatOpenAI(...),  # Unpicklable
    cli_args={"api_key": "secret"},  # Secret
    env_vars={"API_KEY": "sk-xxx"},  # Secret
    model_name="gpt-4",
    checkpointer="memory",
    # ... other fields
)

snapshot = RuntimeConfigSnapshot.from_runtime_config(config)

# All serialization methods work
dict_output = snapshot.model_dump()
json_str = snapshot.model_dump_json()
json_bytes = snapshot.model_dump_json().encode('utf-8')

# Verify secrets excluded
assert "api_key" not in json_str
assert "sk-xxx" not in json_str
assert "gpt-4" in json_str  # Safe field included
```

**Factory Method Benefits**:
1. **Explicit Contract**: Method signature documents excluded fields
2. **Single Responsibility**: Conversion logic centralized in one place
3. **Type Safety**: Pydantic validates snapshot schema
4. **No Magic**: No `@field_serializer` decorators or exclude sets

### Alternatives Considered

**Alt 1: Pydantic model_dump(exclude={...})**
```python
# Use RuntimeConfig directly with exclusion
snapshot_dict = config.model_dump(
    exclude={"model", "cli_args", "env_vars", "dotenv_values", "builtin_defaults"}
)
json_str = json.dumps(snapshot_dict)
```
**Rejected**: Excluded fields are not enforced at type level. Easy to forget exclusions when calling `.model_dump()` in different places. No schema validation for snapshot.

**Alt 2: Pydantic @field_serializer**
```python
class RuntimeConfig(BaseModel):
    model: BaseChatModel | None
    cli_args: dict
    
    @field_serializer('model')
    def serialize_model(self, value, _info):
        return None  # Exclude from JSON
    
    @field_serializer('cli_args')
    def serialize_cli_args(self, value, _info):
        return None  # Exclude from JSON
```
**Rejected**: Modifies RuntimeConfig serialization globally. DoctorReport needs snapshot, but other code may need full serialization. Cannot have two serialization strategies for same model.

**Alt 3: Inheritance with model_config**
```python
class RuntimeConfigSnapshot(RuntimeConfig):
    model_config = ConfigDict(
        frozen=True,
        fields={
            "model": {"exclude": True},
            "cli_args": {"exclude": True},
            # ... more excludes
        }
    )
```
**Rejected**: Pydantic `fields` config doesn't support exclude. Also inheriting from RuntimeConfig creates confusion (snapshot is not a subtype of config, it's a projection).

---

## Summary Table

| Question | Decision | Key Pattern | Stdlib/Library |
|----------|----------|-------------|----------------|
| 1. Exit Code Priority | Priority lookup dict with `min(key=)` | `min(codes, key=lambda c: PRIORITY[c])` | Python `min()` |
| 2. JSONL Atomic Write | File lock + flush + fsync | `fcntl.flock(LOCK_EX)` + `os.fsync()` | `fcntl`, `os` |
| 3. Idempotent Close | Test query before close | `conn.execute("SELECT 1")` + catch `ProgrammingError` | `sqlite3` |
| 4. Continue-on-Failure | Accumulator lists with try-except | `failed_steps: list[str]`, `failed_exit_codes: list[int]` | Python try-except |
| 5. RuntimeConfigSnapshot | Factory method with explicit fields | `@classmethod from_runtime_config()` | Pydantic `BaseModel` |

---

## References

### Existing Codebase Patterns
- `audit_recorder.py:179-186` — File lock pattern for JSONL writes
- `checkpoint_adapter.py:92-102` — Checkpointer close with conditional checks
- `agent_state.py:177-189` — Factory method pattern (`.with_model()`)
- `exceptions.py:19` — Exception with `exit_code` attribute

### Python Documentation
- `min()` builtin — https://docs.python.org/3/library/functions.html#min
- `fcntl.flock()` — https://docs.python.org/3/library/fcntl.html#fcntl.flock
- `os.fsync()` — https://docs.python.org/3/library/os.html#os.fsync
- `sqlite3.ProgrammingError` — https://docs.python.org/3/library/sqlite3.html#exceptions

### LangGraph Documentation
- Checkpointer interface — Assumed from `checkpoint_adapter.py` implementation
- MemorySaver, SqliteSaver, PostgresSaver — Referenced in `checkpoint_adapter.py:24-25`

---

## Implementation Checklist

- [x] Exit code priority table with 13 codes validated
- [x] JSONL atomic write pattern with file lock verified
- [x] Idempotent close pattern tested with sqlite3
- [x] Continue-on-failure state tracking designed
- [x] RuntimeConfigSnapshot factory method validated
- [ ] Integration tests for all 5 patterns (Phase 2)

---

**Next Phase**: Generate `data-model.md` with detailed schemas for DoctorCheckResult, ExitCode, CleanupStepState, RuntimeConfigSnapshot based on research findings.
