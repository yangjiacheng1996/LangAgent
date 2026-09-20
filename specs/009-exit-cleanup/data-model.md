# Data Model: Exit Cleanup & Doctor Self-Check

**Feature**: F09 Exit Cleanup & Doctor Self-Check  
**Created**: 2026-09-20  
**Related**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md)

## Overview

This document defines the data models, state machines, and validation rules for the exit_cleanup stage and doctor self-check functionality. All models are Pydantic-based for JSON serialization and type safety.

---

## Core Entities

### 1. DoctorCheckResult

**Purpose**: Represents the result of a single doctor check (model/checkpointer/skills/instructions).

**Schema** (Pydantic v2):
```python
from pydantic import BaseModel, Field
from typing import Literal

class DoctorCheckResult(BaseModel):
    """Single doctor check result."""
    check_name: str = Field(..., description="Name of check: 'model', 'checkpointer', 'skills', 'instructions'")
    status: Literal["ok", "warn", "error", "skipped"] = Field(..., description="Check status")
    detail: str = Field(..., description="Human-readable details or error message")
    
    class Config:
        frozen = True  # Immutable after creation
```

**Validation Rules**:
- `check_name` must be one of: `"model"`, `"checkpointer"`, `"skills"`, `"instructions"`
- `status` must be one of: `"ok"`, `"warn"`, `"error"`, `"skipped"`
- `detail` must be non-empty string (min length 1)
- If `status == "skipped"`, `detail` should explain why (e.g., "probe_fn not provided")
- If `status == "warn"`, `detail` should list problematic items (e.g., "Malformed skills: skill_a, skill_b")

**Lifecycle**:
1. Created by `check_model()`, `check_checkpointer()`, `check_skills()`, `check_instructions()` functions
2. Aggregated into list by `run_doctor_checks()`
3. Embedded in `DoctorReport.checks` field
4. Written to disk as part of DoctorReport JSON

**Example Instances**:
```python
# Success case
DoctorCheckResult(
    check_name="model",
    status="ok",
    detail="Connected to OpenAI gpt-4o endpoint successfully"
)

# Warning case
DoctorCheckResult(
    check_name="skills",
    status="warn",
    detail="Malformed SKILL.md frontmatter in skills: web_search, file_reader"
)

# Error case
DoctorCheckResult(
    check_name="checkpointer",
    status="error",
    detail="PostgresSaver connection timeout after 5s"
)

# Skipped case
DoctorCheckResult(
    check_name="model",
    status="skipped",
    detail="model_probe_fn not provided"
)
```

---

### 2. ExitCode Priority Table

**Purpose**: Defines the priority ranking of 13 exit codes for worst_of() arbitration.

**Schema** (Enum or Dict):
```python
from enum import IntEnum

class ExitCodePriority(IntEnum):
    """Exit code priority ranking (lower value = higher priority)."""
    SIGINT = 1           # 130: User interrupt (Ctrl-C)
    EX_SOFTWARE = 2      # 70: Internal software error
    NAME_EXISTS = 3      # 67: langagent init <name> already exists
    EX_CONFIG = 4        # 78: Configuration source error
    EX_NOINPUT = 5       # 66: User input file not found
    EX_DATAERR = 6       # 65: YAML/frontmatter parse error
    EX_USAGE = 7         # 64: Semantic usage error
    CONFIG_ERROR = 8     # 5: RuntimeConfig schema validation error
    IO_ERROR = 9         # 4: Disk full, permission denied
    DATA_ERROR = 10      # 3: JSON parse error
    USAGE_ERROR = 11     # 2: argparse parse error
    GENERIC_FAILURE = 12 # 1: Uncategorized failure
    SUCCESS = 13         # 0: No error

# Reverse lookup: exit code → priority rank
EXIT_CODE_TO_PRIORITY: dict[int, int] = {
    130: 1,  # SIGINT (highest priority)
    70: 2,   # EX_SOFTWARE
    67: 3,   # NAME_EXISTS
    78: 4,   # EX_CONFIG
    66: 5,   # EX_NOINPUT
    65: 6,   # EX_DATAERR
    64: 7,   # EX_USAGE
    5: 8,    # CONFIG_ERROR
    4: 9,    # IO_ERROR
    3: 10,   # DATA_ERROR
    2: 11,   # USAGE_ERROR
    1: 12,   # GENERIC_FAILURE
    0: 13    # SUCCESS (lowest priority)
}

def worst_of(codes: list[int]) -> int:
    """Return highest-priority exit code from list.
    
    Args:
        codes: List of exit codes (may be empty, may contain duplicates)
    
    Returns:
        Highest-priority exit code, or 0 if list is empty
    
    Examples:
        >>> worst_of([0, 4, 1])
        4  # IO_ERROR (priority 9) beats GENERIC_FAILURE (priority 12)
        
        >>> worst_of([1, 130, 4])
        130  # SIGINT (priority 1) beats all others
        
        >>> worst_of([])
        0  # Empty list defaults to SUCCESS
        
        >>> worst_of([999])
        999  # Unknown codes treated as lowest priority (rank 999)
    """
    if not codes:
        return 0
    return min(codes, key=lambda c: EXIT_CODE_TO_PRIORITY.get(c, 999))
```

**Validation Rules**:
- Priority ranks must be unique (no two codes share same rank)
- All 13 codes from spec must be present
- Unknown codes default to priority 999 (lowest)
- Empty list returns 0 (success)

---

### 3. CleanupStepState

**Purpose**: Track execution status of each cleanup step for continue-on-failure strategy.

**Schema**:
```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class StepStatus(str, Enum):
    """Cleanup step execution status."""
    PENDING = "pending"        # Not yet started
    RUNNING = "running"        # Currently executing
    SUCCEEDED = "succeeded"    # Completed successfully
    FAILED = "failed"          # Raised exception
    SKIPPED = "skipped"        # Intentionally skipped (e.g., init_only mode)
    TIMED_OUT = "timed_out"    # Best-effort timeout (event_bus.flush only)

@dataclass
class CleanupStepState:
    """State of a single cleanup step."""
    step_number: int           # 1-11
    step_name: str             # e.g., "event_bus_flush", "checkpointer_close"
    status: StepStatus
    exit_code: Optional[int]   # Set if status == FAILED, None otherwise
    error_message: Optional[str]  # Exception message if FAILED, None otherwise
    duration_ms: Optional[float]  # Execution time in milliseconds
```

**State Transitions**:
```
PENDING → RUNNING → (SUCCEEDED | FAILED | TIMED_OUT)
PENDING → SKIPPED (if init_only=True)
```

**Validation Rules**:
- `step_number` must be 1-11 (corresponding to 11 cleanup steps)
- `step_name` must match canonical names:
  1. `event_bus_flush`
  2. `metrics_flush`
  3. `audit_flush`
  4. `checkpointer_close`
  5. `metrics_snapshot`
  6. `drain_spans`
  7. `drain_events`
  8. `write_reports`
  9. `emit_logs`
  10. `emit_lifecycle_init_end` (only if init_only=True)
  11. `return_exit_code`
- If `status == FAILED`, both `exit_code` and `error_message` must be set
- If `status == SUCCEEDED` or `SKIPPED`, `exit_code` and `error_message` must be None
- `duration_ms` may be None if step not yet started

**Usage in cleanup()**:
```python
def cleanup(state, config, *, doctor_report=None, eval_report=None, 
            metrics_snapshot=None, init_only=False) -> int:
    # Initialize step states
    steps = [
        CleanupStepState(1, "event_bus_flush", StepStatus.PENDING, None, None, None),
        CleanupStepState(2, "metrics_flush", StepStatus.PENDING, None, None, None),
        # ... (9 more)
    ]
    
    failed_exit_codes = []
    
    # Execute steps sequentially with continue-on-failure
    for step in steps:
        if init_only and step.step_number <= 8:
            step.status = StepStatus.SKIPPED
            continue
        
        step.status = StepStatus.RUNNING
        start_time = time.perf_counter()
        
        try:
            if step.step_name == "event_bus_flush":
                event_bus.flush(timeout=5)  # May timeout (non-failure)
            elif step.step_name == "metrics_flush":
                metrics_collector.flush()
            # ... (other steps)
            
            step.status = StepStatus.SUCCEEDED
        except TimeoutError:
            step.status = StepStatus.TIMED_OUT  # Only for event_bus.flush
        except Exception as e:
            step.status = StepStatus.FAILED
            step.exit_code = map_exception_to_exit_code(e)
            step.error_message = str(e)
            failed_exit_codes.append(step.exit_code)
        finally:
            step.duration_ms = (time.perf_counter() - start_time) * 1000
    
    return worst_of(failed_exit_codes + [0])
```

---

### 4. RuntimeConfigSnapshot

**Purpose**: Serializable subset of RuntimeConfig for embedding in DoctorReport (excludes BaseChatModel instances and secrets).

**Schema** (Pydantic v2):
```python
from pydantic import BaseModel, Field

class RuntimeConfigSnapshot(BaseModel):
    """Serializable RuntimeConfig subset for DoctorReport.
    
    Excludes:
    - model (BaseChatModel instance, not JSON-serializable)
    - cli_args, env_vars, dotenv_values, builtin_defaults (may contain secrets)
    """
    schema_version: str = Field(default="v0.2.0", description="Snapshot schema version")
    model_provider: str = Field(..., description="Model provider name")
    model_name: str | None = Field(None, description="Model name (if specified)")
    model_base_url: str | None = Field(None, description="Base URL for OpenAI-compatible providers")
    checkpointer: str = Field(..., description="Checkpointer type: memory/sqlite/postgres")
    middleware_ids: list[str] = Field(default_factory=list, description="Enabled middleware IDs")
    skill_dirs: list[str] = Field(default_factory=list, description="Skill directory names")
    log_level: str = Field(default="INFO", description="Log level")
    guardrail_allow_internal_endpoints: bool = Field(default=True, description="Guardrail internal endpoint allow flag")
    
    class Config:
        frozen = True  # Immutable
    
    @classmethod
    def from_runtime_config(cls, config: "RuntimeConfig") -> "RuntimeConfigSnapshot":
        """Factory method to create snapshot from RuntimeConfig.
        
        Args:
            config: Full RuntimeConfig instance
        
        Returns:
            Serializable snapshot with secrets excluded
        """
        return cls(
            schema_version="v0.2.0",
            model_provider=config.model_provider,
            model_name=config.model_name,
            model_base_url=config.model_base_url,
            checkpointer=config.checkpointer,
            middleware_ids=list(config.middleware_ids),
            skill_dirs=list(config.skill_dirs),
            log_level=config.log_level,
            guardrail_allow_internal_endpoints=(
                config.guardrail_policy.allow_internal_endpoints
                if config.guardrail_policy is not None
                else True
            ),
        )
```

**Validation Rules**:
- `schema_version` must be "v0.2.0" (current version)
- `model_provider` must be non-empty string
- `checkpointer` must be one of: `"memory"`, `"sqlite"`, `"postgres"`
- `log_level` must be one of: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`
- `middleware_ids` and `skill_dirs` may be empty lists
- Must be JSON-serializable (no BaseChatModel, no unpicklable objects)

**Lifecycle**:
1. Created via `RuntimeConfigSnapshot.from_runtime_config(config)`
2. Embedded in `DoctorReport.runtime` field
3. Serialized to JSON as part of DoctorReport
4. Written to `~/.local/share/langagent/reports/doctor-<timestamp>.json`

---

### 5. DoctorReport

**Purpose**: Aggregated doctor check report written to disk.

**Schema** (from module_schemas.md):
```python
from pydantic import BaseModel, Field
from datetime import datetime

class DoctorReport(BaseModel):
    """langagent doctor self-check report."""
    report_id: str = Field(..., description="Unique report ID (UUID)")
    generated_at: datetime = Field(..., description="Report generation timestamp")
    checks: list[DoctorCheckResult] = Field(..., description="4 check results")
    overall: str = Field(..., description="Overall status: ok/warn/error")
    agent_dir: str = Field(..., description="Path to checked agent directory")
    runtime: RuntimeConfigSnapshot = Field(..., description="Runtime config snapshot")
    
    class Config:
        frozen = True
```

**Validation Rules**:
- `checks` must contain exactly 4 elements (model, checkpointer, skills, instructions)
- `overall` must be one of: `"ok"`, `"warn"`, `"error"`
- `overall` aggregation logic:
  - If any check has `status == "error"` → `overall = "error"`
  - Else if any check has `status == "warn"` → `overall = "warn"`
  - Else → `overall = "ok"`
  - `status == "skipped"` is ignored in aggregation
- `report_id` must be unique UUID v4
- `generated_at` must be UTC timestamp

**File Path**: `~/.local/share/langagent/reports/doctor-<timestamp>.json`
- `<timestamp>` format: ISO 8601 with seconds precision (e.g., `2026-09-20T14:30:22`)
- If file exists, atomically overwrite (per clarification session 2026-09-20)

---

### 6. EvalReport

**Purpose**: Aggregated eval task report written to disk.

**Schema** (from module_schemas.md):
```python
from pydantic import BaseModel, Field
from datetime import datetime

class EvalReport(BaseModel):
    """langagent eval evaluation report."""
    report_id: str = Field(..., description="Unique report ID (UUID)")
    generated_at: datetime = Field(..., description="Report generation timestamp")
    agent_dir: str = Field(..., description="Path to evaluated agent directory")
    task_results: list[dict] = Field(..., description="Per-task results (task_id, passed, actual, expected)")
    pass_rate: float = Field(..., ge=0.0, le=1.0, description="Pass rate (0.0-1.0)")
    p50_latency_ms: float = Field(..., ge=0.0, description="P50 latency in milliseconds")
    p95_latency_ms: float = Field(..., ge=0.0, description="P95 latency in milliseconds")
    token_usage: dict[str, int] = Field(..., description="Token usage by model")
    cost_usd: float = Field(..., ge=0.0, description="Estimated cost in USD")
    
    class Config:
        frozen = True
```

**Validation Rules**:
- `pass_rate` must be in range [0.0, 1.0]
- `p50_latency_ms` <= `p95_latency_ms` (percentile ordering)
- `token_usage` keys are model names, values are total token counts
- `cost_usd` calculated using per-model token pricing
- `task_results` length determines sample size for percentiles

**File Path**: `~/.local/share/langagent/reports/<agent-dir>-<timestamp>.json`
- `<agent-dir>` is basename of agent directory (e.g., `my-agent` from `/path/to/my-agent`)
- `<timestamp>` format same as DoctorReport

---

### 7. MetricsSnapshot

**Purpose**: Point-in-time snapshot of accumulated metrics from metrics_collector.

**Schema** (consumed from F02, not defined by F09):
```python
# Consumed interface (F02 provides this)
class MetricsSnapshot:
    """Metrics collector snapshot (F02 schema)."""
    token_usage: dict[str, int]       # Model → total tokens
    latency_ms: list[float]           # Per-turn latencies
    cost_usd: float                   # Estimated cost
    turn_count: int                   # Number of ReAct turns
    # ... (other fields defined by F02)
```

**Zero-Valued Fallback** (when metrics_collector.snapshot() fails):
```python
MetricsSnapshot(
    token_usage={},
    latency_ms=[],
    cost_usd=0.0,
    turn_count=0
)
```

**Validation Rules**:
- If `metrics_collector.snapshot()` raises exception or returns None → use zero-valued instance
- Zero-valued instance must have all required fields set to empty/0 values
- Write zero-valued instance to disk (do not skip report writing)
- Record exit code 70 (EX_SOFTWARE) in `failed_exit_codes` list

---

### 8. Span & Event

**Purpose**: Trace/log records written to JSONL files.

**Schema** (consumed from F02/F03):
```python
# Span (7 fields per Constitution Article XII §3)
class Span:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    start: float  # Unix timestamp
    end: float    # Unix timestamp
    attributes: dict[str, Any]

# Event (F03 schema)
class Event:
    event_id: str
    event_type: str
    timestamp: float
    payload: dict[str, Any]
```

**JSONL Format**:
- One record per line (no pretty-printing)
- File path: `~/.local/share/langagent/logs/<run-id>.jsonl`
- If `drain_spans()` or `drain_events()` returns empty list → do not create file (per clarification session 2026-09-20)
- Atomic append using file lock (fcntl.flock) + fsync

---

## State Machines

### Cleanup Execution State Machine

```
┌─────────┐
│ PENDING │ (steps 1-11 initialized)
└────┬────┘
     │
     ├──[init_only=True AND step ≤ 8]──→ SKIPPED
     │
     └──[else]──→ RUNNING
                    │
                    ├──[success]──→ SUCCEEDED
                    │
                    ├──[exception]──→ FAILED
                    │                  │
                    │                  └──→ record exit_code, continue to next step
                    │
                    └──[event_bus.flush timeout]──→ TIMED_OUT (not a failure)
```

### Doctor Check Status Aggregation

```
4 DoctorCheckResult instances
    │
    ├─── Any status == "error" ──→ overall = "error"
    │
    ├─── Else, any status == "warn" ──→ overall = "warn"
    │
    └─── Else (all "ok" or "skipped") ──→ overall = "ok"
```

### Report Routing Priority

```
cleanup(state, config, *, doctor_report, eval_report, metrics_snapshot, init_only)
    │
    ├─── eval_report provided ──→ write EvalReport (highest priority)
    │
    ├─── else, doctor_report provided ──→ write DoctorReport
    │
    └─── else ──→ write MetricsSnapshot only (default for langagent run)
```

---

## Relationships

```
RuntimeExitHandler
    │
    ├──calls──→ run_doctor_checks()
    │               │
    │               ├──creates──→ DoctorCheckResult (×4)
    │               │
    │               └──returns──→ list[DoctorCheckResult]
    │
    ├──calls──→ cleanup()
    │               │
    │               ├──tracks──→ CleanupStepState (×11)
    │               │
    │               ├──aggregates──→ failed_exit_codes: list[int]
    │               │
    │               └──calls──→ worst_of(failed_exit_codes)
    │
    └──calls──→ write_reports()
                    │
                    ├──routes to──→ DoctorReport
                    │                   │
                    │                   ├──embeds──→ RuntimeConfigSnapshot
                    │                   │
                    │                   └──embeds──→ list[DoctorCheckResult]
                    │
                    ├──routes to──→ EvalReport
                    │
                    └──routes to──→ MetricsSnapshot (zero-valued if snapshot() failed)
```

---

## Implementation Checklist

- [ ] Define `DoctorCheckResult` Pydantic model with 4 status values
- [ ] Define `EXIT_CODE_TO_PRIORITY` dict with 13 codes
- [ ] Implement `worst_of(codes)` function with empty list edge case
- [ ] Define `CleanupStepState` dataclass with 6 state transitions
- [ ] Define `RuntimeConfigSnapshot` Pydantic model with `from_runtime_config()` factory
- [ ] Implement overall status aggregation logic in `run_doctor_checks()`
- [ ] Implement report routing logic in `write_reports()` (eval > doctor > metrics_snapshot)
- [ ] Implement zero-valued MetricsSnapshot fallback when `snapshot()` fails
- [ ] Write unit tests for all state transitions and validation rules
- [ ] Verify JSON serializability of all Pydantic models (no BaseChatModel leakage)
