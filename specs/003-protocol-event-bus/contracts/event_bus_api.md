# API Contract: EventBus Protocol Interface

**Module**: `langagent.protocol.event_bus`  
**Consumers**: F05/F08/F04/F09/F11 (publishers), F02 (subscriber)  
**Version**: 1.0.0  
**Date**: 2026-09-18

---

## Overview

This contract defines the public API of the EventBus class and related types exposed by the `langagent.protocol.event_bus` module. The EventBus implements the `EventBusProtocol` interface defined in F02 `cross_cutting_logger`.

---

## Public Types

### 1. Event (Immutable Data Class)

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Event:
    """Immutable record of a system occurrence."""
    event_id: str          # UUID v4 string
    event_type: str        # Must be in ALLOWED_EVENT_TYPES
    emitted_at: str        # ISO 8601 UTC timestamp
    source: str            # Module identifier (e.g., "langagent.runtime.main_loop")
    payload: dict          # JSON-serializable dict
    trace_id: str          # UUID or "-"
    
    @classmethod
    def create(
        cls, 
        event_type: str, 
        source: str, 
        payload: dict, 
        trace_id: str = "-"
    ) -> "Event":
        """Factory method generating event_id and emitted_at automatically."""
        ...
```

**Contracts**:
- `event_id`: Auto-generated UUID v4; duplicates allowed (negligible probability)
- `event_type`: Must be in whitelist; publish raises `UnknownEventTypeError` otherwise
- `emitted_at`: Auto-generated UTC timestamp in ISO 8601 format with 'Z' suffix
- `payload`: Caller MUST ensure JSON-serializability (no LangChain objects without conversion)
- `trace_id`: Use `"-"` when no trace context (not `None`)

---

### 2. SubscriptionToken (Opaque Handle)

```python
from typing import NewType

SubscriptionToken = NewType("SubscriptionToken", int)
```

**Contracts**:
- Opaque integer handle; internal value should not be inspected by callers
- Remains valid until `unsubscribe()` called
- Unsubscribing multiple times is idempotent (safe)

---

### 3. EventHandler (Callable Type)

```python
from typing import Callable, Protocol

class EventHandler(Protocol):
    def __call__(self, event: Event) -> None: ...
```

**Contracts**:
- Signature: `(Event) -> None`
- Exceptions: Caught and logged; do not propagate to publish caller
- Async: `async def handler(event: Event) -> None` supported with `publish_async()` only

---

### 4. Exceptions

```python
class UnknownEventTypeError(ValueError):
    """Raised when event_type not in ALLOWED_EVENT_TYPES."""
    pass

class EventDrainError(RuntimeError):
    """Raised when event buffer drainage fails (I/O error)."""
    pass
```

**Exit Codes**:
- `UnknownEventTypeError`: Caller maps to exit code 78 (EX_CONFIG)
- `EventDrainError`: Caller maps to exit code 4 (I/O error)

---

## Public API: EventBus Class

### Constructor

```python
class EventBus:
    def __init__(self) -> None:
        """Initialize empty event bus (singleton pattern recommended)."""
        ...
```

**Contracts**:
- Thread-safe initialization
- No configuration parameters (uses internal defaults)
- Singleton pattern enforced by caller (F01 dispatch)

---

### Method: `publish`

```python
def publish(self, event: Event) -> None:
    """Publish event to all subscribers synchronously.
    
    Args:
        event: Event instance to publish
        
    Raises:
        UnknownEventTypeError: If event.event_type not in ALLOWED_EVENT_TYPES
        
    Guarantees:
        - All subscribers invoked in FIFO registration order before return
        - Handler exceptions caught and logged (do not propagate)
        - Event appended to internal buffer for later drain
        - Thread-safe (multiple concurrent publish calls supported)
    """
    ...
```

**Contracts**:
- **Pre-condition**: `event.event_type in ALLOWED_EVENT_TYPES`
- **Post-condition**: All registered handlers for `event.event_type` have executed
- **Side-effects**: Event added to `_event_buffer`; handler errors logged via F02 `emit()`
- **Performance**: <10ms for 3 subscribers (per Success Criteria SC-001)
- **Concurrency**: Thread-safe; multiple threads can call concurrently

---

### Method: `publish_async`

```python
async def publish_async(self, event: Event) -> None:
    """Publish event to all subscribers asynchronously.
    
    Args:
        event: Event instance to publish
        
    Raises:
        UnknownEventTypeError: If event.event_type not in ALLOWED_EVENT_TYPES
        
    Guarantees:
        - All async handlers awaited via asyncio.gather(return_exceptions=True)
        - Sync handlers wrapped as coroutines and executed
        - Handler exceptions caught and logged (do not propagate)
        - Event appended to internal buffer for later drain
    """
    ...
```

**Contracts**:
- **Pre-condition**: `event.event_type in ALLOWED_EVENT_TYPES`
- **Post-condition**: All async handlers completed (or raised exception)
- **Error Isolation**: One handler exception does not cancel others (return_exceptions=True)
- **Concurrency**: Handlers run in parallel via `asyncio.gather`

---

### Method: `subscribe`

```python
def subscribe(
    self, 
    event_type: str, 
    handler: Callable[[Event], None]
) -> SubscriptionToken:
    """Register handler for event type.
    
    Args:
        event_type: Event type string (need not be in whitelist yet)
        handler: Callable accepting Event and returning None
        
    Returns:
        SubscriptionToken for later unsubscription
        
    Guarantees:
        - Handler added to end of subscriber list (FIFO order)
        - Same handler can be registered multiple times (each gets unique token)
        - Thread-safe
    """
    ...
```

**Contracts**:
- **Pre-condition**: None (event_type need not be in whitelist; subscribe succeeds but no events received)
- **Post-condition**: Handler appended to `_subscribers[event_type]` list
- **Idempotency**: Not idempotent (calling twice with same handler creates 2 subscriptions)
- **Concurrency**: Can be called during `publish()` without deadlock (RLock)

---

### Method: `unsubscribe`

```python
def unsubscribe(self, token: SubscriptionToken) -> None:
    """Remove handler associated with token.
    
    Args:
        token: Token returned by subscribe()
        
    Guarantees:
        - Handler removed from subscriber list
        - Idempotent (multiple unsubscribe calls with same token are no-op)
        - Thread-safe
    """
    ...
```

**Contracts**:
- **Pre-condition**: None (invalid token is no-op)
- **Post-condition**: Handler no longer invoked on subsequent publishes
- **Idempotency**: Yes (multiple calls safe)
- **Concurrency**: Can be called during `publish()` without deadlock

---

### Method: `flush`

```python
def flush(self, timeout: float = 5.0) -> None:
    """Wait for all pending event handlers to complete.
    
    Args:
        timeout: Maximum seconds to wait (default 5.0)
        
    Guarantees:
        - Blocks until all pending handlers complete OR timeout expires
        - Handlers exceeding timeout continue in background (not cancelled)
        - Timeout emits 'la.cross_cutting.event_handler_error' log (no exception)
        - Returns immediately if no pending handlers
    """
    ...
```

**Contracts**:
- **Pre-condition**: None
- **Post-condition**: All handlers submitted before flush() have completed OR timeout expired
- **Error Handling**: Timeout is not an error (logged but doesn't raise exception)
- **Performance**: Blocks for up to `timeout` seconds

---

### Method: `drain_events`

```python
def drain_events(self) -> list[Event]:
    """Extract all accumulated events and clear buffer.
    
    Returns:
        List of Event instances (may be empty)
        
    Raises:
        EventDrainError: If buffer read/clear operation fails
        
    Guarantees:
        - Returns snapshot of all events published since last drain
        - Buffer cleared atomically (thread-safe)
        - Second call returns empty list (no re-drain)
        - On failure, buffer NOT cleared (caller can retry)
    """
    ...
```

**Contracts**:
- **Pre-condition**: None (safe to call multiple times)
- **Post-condition**: `_event_buffer` is empty; returned list contains all events since last drain
- **Atomicity**: Read + clear is atomic (protected by lock)
- **Error Recovery**: On `EventDrainError`, buffer preserved (caller responsibility to retry)
- **Typical Usage**: F09 calls `flush()` then `drain_events()` before persisting to JSONL

---

## EventBusProtocol Compliance

The EventBus class implements the `EventBusProtocol` interface defined in `langagent.cross_cutting.logger`:

```python
from typing import Protocol

class EventBusProtocol(Protocol):
    def publish(self, event: Event) -> None: ...
    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> Callable[[], None]: ...
    def unsubscribe(self, token: Callable[[], None]) -> None: ...
    def flush(self, timeout: float = 5.0) -> None: ...
```

**Note**: F03 extends this protocol with `publish_async()` and `drain_events()` methods.

---

## Usage Examples

### Example 1: Basic Pub/Sub

```python
from langagent.protocol.event_bus import EventBus, Event

bus = EventBus()

# Subscribe
def on_tool_call(event: Event) -> None:
    print(f"Tool called: {event.payload['tool_name']}")

token = bus.subscribe("tool_call", on_tool_call)

# Publish
event = Event.create(
    event_type="tool_call",
    source="runtime.main_loop",
    payload={"tool_name": "search", "args": {"query": "test"}},
)
bus.publish(event)  # Prints: Tool called: search

# Unsubscribe
bus.unsubscribe(token)
```

---

### Example 2: Async Handler

```python
import asyncio

async def async_handler(event: Event) -> None:
    await asyncio.sleep(0.1)  # Simulate I/O
    print(f"Async: {event.event_type}")

bus.subscribe("model_response", async_handler)

# Must use publish_async for async handlers
event = Event.create(event_type="model_response", source="F08", payload={})
await bus.publish_async(event)
```

---

### Example 3: Error Isolation

```python
def faulty_handler(event: Event) -> None:
    raise ValueError("Oops!")

def good_handler(event: Event) -> None:
    print("Good handler executed")

bus.subscribe("test", faulty_handler)
bus.subscribe("test", good_handler)

event = Event.create(event_type="test", source="test", payload={})
bus.publish(event)
# Output: Good handler executed
# (faulty_handler exception logged but doesn't propagate)
```

---

### Example 4: Flush and Drain (F09 Usage)

```python
# F09 exit_cleanup usage pattern
bus.flush(timeout=5.0)  # Wait for pending handlers
events = bus.drain_events()  # Extract all events

# Write to JSONL (F09 responsibility)
import json
with open("logs/run-123.jsonl", "w") as f:
    for event in events:
        f.write(json.dumps(event.__dict__) + "\n")
```

---

## Breaking Changes Policy

This is version 1.0.0 of the contract. Breaking changes (signature changes, removed methods, changed semantics) will require a major version bump and migration guide.

Non-breaking changes (new methods, new optional parameters with defaults) allowed in minor versions.

---

## Deprecation

None. All methods are stable for v1.0.

---

## Testing Contract

Clients can rely on the following test guarantees:

1. **FIFO Order**: Subscribers invoked in registration order (test: subscribe 3 handlers, verify execution order)
2. **Error Isolation**: Handler exception does not prevent other handlers (test: faulty + good handler)
3. **Thread Safety**: 10 threads publishing 100 events each = 1,000 events in buffer (test: concurrent publish)
4. **Flush Timeout**: Handlers continue after timeout (test: slow handler + flush + verify handler completes)
5. **Drain Atomicity**: No events lost between drain calls (test: publish 5 + drain + publish 3 + drain)

---

## Support

**Owned by**: F03 (protocol layer)  
**Documentation**: See `/specs/003-protocol-event-bus/`  
**Issues**: Report via GitHub issues with label `protocol:event_bus`
