# Research: F03 Protocol Event Bus

**Date**: 2026-09-18  
**Feature**: F03 Protocol Event Bus  
**Purpose**: Resolve technical unknowns and establish implementation patterns

---

## 1. Thread Safety Patterns for Pub/Sub Systems

### Decision
Use a single `threading.RLock` (reentrant lock) to protect both the subscriber registry and event buffer.

### Rationale
- **Simplicity**: Single lock avoids deadlock scenarios from multiple locks
- **Correctness**: RLock allows same thread to acquire lock multiple times (useful if handler calls subscribe/unsubscribe)
- **Performance**: Lock granularity at operation level (<10ms critical section) is acceptable for target throughput (1,000 events/sec)

### Pattern
```python
class EventBus:
    def __init__(self):
        self._lock = threading.RLock()
        self._subscribers: dict[str, list[tuple[SubscriptionToken, Callable]]] = {}
        self._event_buffer: list[Event] = []
    
    def publish(self, event: Event) -> None:
        with self._lock:
            # Read subscriber list snapshot
            handlers = self._subscribers.get(event.event_type, []).copy()
        
        # Execute handlers outside lock (error isolation)
        for token, handler in handlers:
            try:
                handler(event)
            except Exception as e:
                self._log_handler_error(e, token)
        
        # Append to buffer inside lock
        with self._lock:
            self._event_buffer.append(event)
```

### Alternatives Considered
- **Fine-grained locks** (one per event type): Rejected due to complexity and deadlock risk
- **Lock-free data structures**: Rejected due to Python GIL making atomic operations difficult to verify
- **Queue-based async dispatch**: Rejected as synchronous execution is a requirement (FR-002)

---

## 2. Async Handler Error Isolation

### Decision
Use `asyncio.gather(*tasks, return_exceptions=True)` to run all async handlers concurrently while isolating exceptions.

### Rationale
- **Error Isolation**: `return_exceptions=True` ensures one failing handler doesn't cancel others (per spec clarification Q4)
- **Concurrency**: All handlers run in parallel via gather (better performance than sequential await)
- **Exception Handling**: Gather returns list where each item is either result or exception instance

### Pattern
```python
async def publish_async(self, event: Event) -> None:
    with self._lock:
        handlers = self._subscribers.get(event.event_type, []).copy()
    
    # Wrap sync handlers as coroutines
    tasks = []
    for token, handler in handlers:
        if asyncio.iscoroutinefunction(handler):
            tasks.append(handler(event))
        else:
            # Wrap sync handler
            tasks.append(asyncio.to_thread(handler, event))
    
    # Execute with error isolation
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Log exceptions without re-raising
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            token, _ = handlers[i]
            self._log_handler_error(result, token)
    
    with self._lock:
        self._event_buffer.append(event)
```

### Alternatives Considered
- **TaskGroup** (Python 3.11+): Rejected because it cancels all tasks on first exception
- **Sequential async execution**: Rejected as it loses concurrency benefits
- **Fire-and-forget tasks**: Rejected as flush() needs to track pending handlers

---

## 3. Flush Timeout Implementation

### Decision
Use `concurrent.futures.ThreadPoolExecutor` with `as_completed(timeout)` for sync handlers; track async handlers separately with `asyncio.wait_for()`.

### Rationale
- **Timeout Guarantee**: Both sync and async handlers respect timeout
- **Non-blocking Post-Timeout**: Handlers continue in background after timeout (per spec clarification Q2)
- **Future Tracking**: Allows flush() to wait on pending handlers without blocking publish()

### Pattern
```python
class EventBus:
    def __init__(self):
        self._pending_futures: list[concurrent.futures.Future] = []
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
    
    def flush(self, timeout: float = 5.0) -> None:
        with self._lock:
            futures_snapshot = self._pending_futures.copy()
        
        if not futures_snapshot:
            return  # No pending handlers
        
        done, not_done = concurrent.futures.wait(
            futures_snapshot, 
            timeout=timeout,
            return_when=concurrent.futures.ALL_COMPLETED
        )
        
        if not_done:
            # Log timeout but don't raise exception
            from langagent.cross_cutting.logger import emit
            emit(
                tag="la.cross_cutting.event_handler_error",
                level="warning",
                message=f"flush() timeout: {len(not_done)} handlers still running"
            )
```

### Alternatives Considered
- **Blocking wait forever**: Rejected as it could hang exit_cleanup (F09 requirement)
- **Cancel pending handlers**: Rejected per spec clarification Q2 (handlers continue)
- **Separate thread for flush**: Rejected as unnecessary complexity

---

## 4. Event ID Generation

### Decision
Use Python's `uuid.uuid4()` for event_id generation; allow duplicate IDs (per spec clarification Q3).

### Rationale
- **Collision Probability**: UUID v4 has ~10^-18 collision probability for 10,000 events (negligible)
- **No Coordination Needed**: Thread-safe without locks (each uuid4() call is independent)
- **Standard Library**: No external dependencies

### Pattern
```python
import uuid
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: str
    emitted_at: str  # ISO 8601 UTC
    source: str
    payload: dict
    trace_id: str
    
    @classmethod
    def create(cls, event_type: str, source: str, payload: dict, trace_id: str = "-") -> "Event":
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            emitted_at=datetime.utcnow().isoformat() + "Z",
            source=source,
            payload=payload,
            trace_id=trace_id
        )
```

### Alternatives Considered
- **Sequential integer IDs**: Rejected due to thread-safety complexity (need atomic counter)
- **Timestamp + random suffix**: Rejected as more complex than UUID with no benefit
- **UUID deduplication check**: Rejected per spec clarification Q3 (duplicates allowed)

---

## 5. Subscription Token Design

### Decision
Use a unique integer as SubscriptionToken (thread-safe counter with lock).

### Rationale
- **Opaque Handle**: Integer is simple and doesn't expose internal structure
- **Fast Lookup**: Dict keyed by token allows O(1) unsubscribe
- **Idempotent Unsubscribe**: Deleting non-existent key can be caught and ignored

### Pattern
```python
from typing import NewType

SubscriptionToken = NewType("SubscriptionToken", int)

class EventBus:
    def __init__(self):
        self._next_token_id = 0
        self._lock = threading.RLock()
        # Map: event_type -> list[(token, handler)]
        self._subscribers: dict[str, list[tuple[SubscriptionToken, Callable]]] = {}
        # Reverse map: token -> (event_type, handler) for O(1) unsubscribe
        self._token_map: dict[SubscriptionToken, tuple[str, Callable]] = {}
    
    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> SubscriptionToken:
        with self._lock:
            token = SubscriptionToken(self._next_token_id)
            self._next_token_id += 1
            
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            
            self._subscribers[event_type].append((token, handler))
            self._token_map[token] = (event_type, handler)
            
            return token
    
    def unsubscribe(self, token: SubscriptionToken) -> None:
        with self._lock:
            if token not in self._token_map:
                return  # Idempotent: already unsubscribed
            
            event_type, handler = self._token_map.pop(token)
            self._subscribers[event_type] = [
                (t, h) for t, h in self._subscribers[event_type] if t != token
            ]
```

### Alternatives Considered
- **UUID as token**: Rejected as overkill (no distributed system)
- **Handler reference as token**: Rejected as not idempotent (same handler registered twice)
- **String token**: Rejected as integers are faster for dict keys

---

## 6. Event Type Whitelist Enforcement

### Decision
Use a module-level `frozenset` constant `ALLOWED_EVENT_TYPES` in `langagent/protocol/event_types.py`.

### Rationale
- **Compile-Time Definition**: All event types declared in one place
- **Fast Lookup**: Set membership is O(1)
- **Immutable**: frozenset prevents accidental modification

### Pattern
```python
# langagent/protocol/event_types.py
ALLOWED_EVENT_TYPES: frozenset[str] = frozenset({
    "tool_call",
    "tool_result",
    "model_response",
    "guardrail_block",
    "skill_loaded",
    "skill_load_failed",
    "tool_registered",
    "graph_composed",
    "eval_task_started",
    "eval_task_done",
    "audit_written",
    "metrics_snapshot",
    "event_handler_error",
})

# langagent/protocol/event_bus.py
from langagent.protocol.event_types import ALLOWED_EVENT_TYPES

class UnknownEventTypeError(ValueError):
    """Raised when publishing an event type not in whitelist."""
    pass

class EventBus:
    def publish(self, event: Event) -> None:
        if event.event_type not in ALLOWED_EVENT_TYPES:
            raise UnknownEventTypeError(
                f"Event type '{event.event_type}' not in whitelist. "
                f"Allowed types: {sorted(ALLOWED_EVENT_TYPES)}"
            )
        # ... rest of publish logic
```

### Alternatives Considered
- **Runtime registration**: Rejected as it allows typos to slip through
- **Enum**: Rejected as string constants are more ergonomic for dict keys
- **Config file**: Rejected as event types are code-level contract, not runtime config

---

## 7. Event Buffer Drainage

### Decision
Drain atomically returns full buffer snapshot and clears it in single lock acquisition.

### Rationale
- **Atomic Operation**: Lock ensures no events lost between read and clear
- **Single Responsibility**: drain_events() only extracts; F09 handles persistence
- **No Re-drain**: Cleared buffer means second drain returns empty list (per FR-017)

### Pattern
```python
class EventDrainError(RuntimeError):
    """Raised when event buffer drainage fails."""
    pass

class EventBus:
    def drain_events(self) -> list[Event]:
        try:
            with self._lock:
                snapshot = self._event_buffer.copy()
                self._event_buffer.clear()
            return snapshot
        except Exception as e:
            # Do NOT clear buffer on failure (allow retry)
            raise EventDrainError(f"Failed to drain event buffer: {e}") from e
```

### Alternatives Considered
- **Peek without clear**: Rejected per spec requirement (drain must clear)
- **Generator/iterator**: Rejected as F09 needs full list for JSONL batch write
- **Auto-retry on failure**: Rejected as retry logic belongs in caller (F09)

---

## 8. Integration with F02 Logger

### Decision
Import `emit()` function from `langagent.cross_cutting.logger`; use `la.cross_cutting.event_handler_error` tag.

### Rationale
- **Dependency Direction**: F03 (protocol) can import from F02 (cross_cutting) per architecture
- **No Circular Import**: F02 logger doesn't import event_bus (provides EventBusProtocol interface only)
- **Tag Whitelist**: `la.cross_cutting.event_handler_error` must be registered in F02 tag whitelist

### Pattern
```python
from langagent.cross_cutting.logger import emit

class EventBus:
    def _log_handler_error(self, exception: Exception, token: SubscriptionToken) -> None:
        emit(
            tag="la.cross_cutting.event_handler_error",
            level="error",
            message=f"Handler {token} raised {type(exception).__name__}: {exception}",
            payload={
                "token": int(token),
                "exception_type": type(exception).__name__,
                "exception_message": str(exception),
            }
        )
        # Increment internal error counter (FR-006)
        self._error_count += 1
```

### Alternatives Considered
- **Raise exception to caller**: Rejected per FR-004 (must isolate errors)
- **Publish event_handler_error event**: Rejected as recursive (error in error handler)
- **Silent swallow**: Rejected as errors must be observable

---

## Summary

All technical unknowns resolved. Key decisions:
1. Single RLock for thread safety
2. `asyncio.gather(return_exceptions=True)` for async error isolation
3. `concurrent.futures.wait(timeout)` for flush implementation
4. UUID v4 for event IDs (duplicates allowed)
5. Integer subscription tokens with reverse map
6. frozenset whitelist for event types
7. Atomic drain with lock + no re-drain
8. Direct import from F02 logger (no circular dependency)

Ready for Phase 1 (data model + contracts).
