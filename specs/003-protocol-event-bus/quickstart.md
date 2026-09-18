# Quickstart: F03 Protocol Event Bus Validation

**Feature**: F03 Protocol Event Bus  
**Purpose**: Runnable validation scenarios proving the feature works end-to-end  
**Date**: 2026-09-18

---

## Prerequisites

1. **Environment Setup**:
   ```bash
   cd /path/to/LangAgent
   python -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   ```

2. **Dependencies Met**:
   - F02 `cross_cutting_logger` module provides `emit()` and `EventBusProtocol`
   - Python 3.11+ installed
   - pytest and pytest-asyncio installed

3. **Feature Implemented**:
   - `langagent/protocol/event_bus.py` exists
   - `langagent/protocol/event_types.py` exists
   - Test suite under `tests/protocol/test_event_bus.py` exists

---

## Validation Scenario 1: Basic Pub/Sub

**Purpose**: Verify synchronous publish/subscribe with FIFO order

### Setup

```python
# Save as test_scenario_1.py
from langagent.protocol.event_bus import EventBus, Event

def main():
    bus = EventBus()
    results = []
    
    # Subscribe 3 handlers in order
    bus.subscribe("tool_call", lambda e: results.append("handler_1"))
    bus.subscribe("tool_call", lambda e: results.append("handler_2"))
    bus.subscribe("tool_call", lambda e: results.append("handler_3"))
    
    # Publish event
    event = Event.create(
        event_type="tool_call",
        source="test",
        payload={"tool_name": "search"}
    )
    bus.publish(event)
    
    # Verify FIFO order
    assert results == ["handler_1", "handler_2", "handler_3"], f"Expected FIFO order, got {results}"
    print("✓ Scenario 1 PASSED: FIFO order verified")

if __name__ == "__main__":
    main()
```

### Run

```bash
python test_scenario_1.py
```

### Expected Output

```
✓ Scenario 1 PASSED: FIFO order verified
```

### Success Criteria

- All 3 handlers execute in registration order
- No exceptions raised
- Process exits with code 0

---

## Validation Scenario 2: Error Isolation

**Purpose**: Verify handler exceptions don't prevent other handlers

### Setup

```python
# Save as test_scenario_2.py
from langagent.protocol.event_bus import EventBus, Event

def main():
    bus = EventBus()
    executed = []
    
    # Subscribe: faulty handler then good handler
    bus.subscribe("test", lambda e: (_ for _ in ()).throw(ValueError("Faulty!")))
    bus.subscribe("test", lambda e: executed.append("good"))
    
    # Publish
    event = Event.create(event_type="test", source="test", payload={})
    bus.publish(event)
    
    # Verify good handler executed despite faulty handler
    assert executed == ["good"], f"Expected ['good'], got {executed}"
    print("✓ Scenario 2 PASSED: Error isolation verified")

if __name__ == "__main__":
    main()
```

### Run

```bash
python test_scenario_2.py
```

### Expected Output

```
✓ Scenario 2 PASSED: Error isolation verified
```

### Success Criteria

- Good handler executes after faulty handler raises exception
- Exception logged (check logs for `la.cross_cutting.event_handler_error`)
- Process exits with code 0

---

## Validation Scenario 3: Async Handlers

**Purpose**: Verify `publish_async()` with concurrent async handlers

### Setup

```python
# Save as test_scenario_3.py
import asyncio
from langagent.protocol.event_bus import EventBus, Event

async def main():
    bus = EventBus()
    results = []
    
    # Subscribe async handlers
    async def handler_1(e):
        await asyncio.sleep(0.1)
        results.append("async_1")
    
    async def handler_2(e):
        await asyncio.sleep(0.05)
        results.append("async_2")
    
    bus.subscribe("test", handler_1)
    bus.subscribe("test", handler_2)
    
    # Publish async
    event = Event.create(event_type="test", source="test", payload={})
    await bus.publish_async(event)
    
    # Verify both executed (order may vary due to concurrency)
    assert set(results) == {"async_1", "async_2"}, f"Expected both handlers, got {results}"
    print("✓ Scenario 3 PASSED: Async handlers verified")

if __name__ == "__main__":
    asyncio.run(main())
```

### Run

```bash
python test_scenario_3.py
```

### Expected Output

```
✓ Scenario 3 PASSED: Async handlers verified
```

### Success Criteria

- Both async handlers complete
- Handlers run concurrently (not sequentially)
- Process exits with code 0

---

## Validation Scenario 4: Flush Timeout

**Purpose**: Verify `flush()` waits for handlers and handles timeout

### Setup

```python
# Save as test_scenario_4.py
import time
from langagent.protocol.event_bus import EventBus, Event

def main():
    bus = EventBus()
    completed = []
    
    # Slow handler (3 seconds)
    def slow_handler(e):
        time.sleep(3)
        completed.append("slow")
    
    bus.subscribe("test", slow_handler)
    
    # Publish in background (simulating pending handler)
    import threading
    event = Event.create(event_type="test", source="test", payload={})
    thread = threading.Thread(target=lambda: bus.publish(event))
    thread.start()
    
    time.sleep(0.1)  # Let publish start
    
    # Flush with timeout > handler duration
    bus.flush(timeout=5.0)
    
    # Verify handler completed
    assert completed == ["slow"], f"Expected handler to complete, got {completed}"
    print("✓ Scenario 4 PASSED: Flush waited for handler")
    
    thread.join()

if __name__ == "__main__":
    main()
```

### Run

```bash
python test_scenario_4.py
```

### Expected Output

```
✓ Scenario 4 PASSED: Flush waited for handler
```

### Success Criteria

- `flush()` blocks until slow handler completes
- Handler execution finishes before flush returns
- Process exits with code 0

---

## Validation Scenario 5: Drain Events

**Purpose**: Verify `drain_events()` returns accumulated events and clears buffer

### Setup

```python
# Save as test_scenario_5.py
from langagent.protocol.event_bus import EventBus, Event

def main():
    bus = EventBus()
    
    # Publish 5 events (no subscribers)
    for i in range(5):
        event = Event.create(
            event_type="tool_call",
            source="test",
            payload={"index": i}
        )
        bus.publish(event)
    
    # Drain
    events_1 = bus.drain_events()
    assert len(events_1) == 5, f"Expected 5 events, got {len(events_1)}"
    
    # Publish 3 more
    for i in range(3):
        event = Event.create(event_type="tool_call", source="test", payload={"index": i+5})
        bus.publish(event)
    
    # Drain again
    events_2 = bus.drain_events()
    assert len(events_2) == 3, f"Expected 3 events, got {len(events_2)}"
    
    # Third drain should be empty
    events_3 = bus.drain_events()
    assert len(events_3) == 0, f"Expected 0 events, got {len(events_3)}"
    
    print("✓ Scenario 5 PASSED: Drain and buffer clear verified")

if __name__ == "__main__":
    main()
```

### Run

```bash
python test_scenario_5.py
```

### Expected Output

```
✓ Scenario 5 PASSED: Drain and buffer clear verified
```

### Success Criteria

- First drain returns 5 events
- Second drain returns 3 events (not 8)
- Third drain returns empty list
- Process exits with code 0

---

## Validation Scenario 6: Event Type Whitelist

**Purpose**: Verify unregistered event types are rejected

### Setup

```python
# Save as test_scenario_6.py
from langagent.protocol.event_bus import EventBus, Event, UnknownEventTypeError

def main():
    bus = EventBus()
    
    # Attempt to publish unregistered event type
    event = Event.create(
        event_type="unregistered_type",
        source="test",
        payload={}
    )
    
    try:
        bus.publish(event)
        assert False, "Expected UnknownEventTypeError"
    except UnknownEventTypeError as e:
        assert "unregistered_type" in str(e)
        assert "not in whitelist" in str(e)
        print("✓ Scenario 6 PASSED: Whitelist enforcement verified")

if __name__ == "__main__":
    main()
```

### Run

```bash
python test_scenario_6.py
```

### Expected Output

```
✓ Scenario 6 PASSED: Whitelist enforcement verified
```

### Success Criteria

- `UnknownEventTypeError` raised for unregistered type
- Error message includes event type and "not in whitelist"
- Process exits with code 0

---

## Validation Scenario 7: Thread Safety

**Purpose**: Verify concurrent publish from multiple threads

### Setup

```python
# Save as test_scenario_7.py
import threading
from langagent.protocol.event_bus import EventBus, Event

def main():
    bus = EventBus()
    barrier = threading.Barrier(10)
    
    def worker(thread_id):
        barrier.wait()  # Synchronize start
        for i in range(100):
            event = Event.create(
                event_type="tool_call",
                source=f"thread_{thread_id}",
                payload={"iter": i}
            )
            bus.publish(event)
    
    # Spawn 10 threads
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Drain and verify count
    events = bus.drain_events()
    assert len(events) == 1000, f"Expected 1000 events, got {len(events)}"
    
    print("✓ Scenario 7 PASSED: Thread safety verified (1000 events)")

if __name__ == "__main__":
    main()
```

### Run

```bash
python test_scenario_7.py
```

### Expected Output

```
✓ Scenario 7 PASSED: Thread safety verified (1000 events)
```

### Success Criteria

- All 1,000 events published without loss
- No race conditions or corruption
- Process exits with code 0

---

## Running Full Test Suite

Instead of individual scenarios, run the full pytest suite:

```bash
pytest tests/protocol/test_event_bus.py -v
pytest tests/protocol/test_event_integration_with_metrics.py -v
```

### Expected Output

```
tests/protocol/test_event_bus.py::test_publish_subscribe_basic PASSED
tests/protocol/test_event_bus.py::test_publish_no_subscribers PASSED
tests/protocol/test_event_bus.py::test_subscribe_returns_token PASSED
...
tests/protocol/test_event_bus.py::test_drain_events_returns_accumulated PASSED
tests/protocol/test_event_bus.py::test_drain_events_clears_buffer PASSED

======================== 27 passed in 2.34s ========================
```

### Success Criteria

- All tests pass (≥24 core tests + ≥3 integration tests)
- No failures or errors
- pytest exit code 0

---

## Troubleshooting

### Issue: Import Error for `langagent.protocol.event_bus`

**Symptom**: `ModuleNotFoundError: No module named 'langagent.protocol'`

**Solution**: 
1. Ensure you ran `pip install -e ".[dev]"` from repo root
2. Verify `langagent/protocol/__init__.py` exists
3. Check Python path includes repo root

### Issue: `UnknownEventTypeError` for valid event type

**Symptom**: `UnknownEventTypeError: Event type 'tool_call' not in whitelist`

**Solution**:
1. Verify `langagent/protocol/event_types.py` defines `ALLOWED_EVENT_TYPES`
2. Check that "tool_call" is in the frozenset
3. Ensure EventBus imports from `event_types`

### Issue: Async tests fail with `RuntimeError: no running event loop`

**Symptom**: `RuntimeError` when calling `await bus.publish_async()`

**Solution**:
1. Ensure test function is `async def test_...`
2. Use `@pytest.mark.asyncio` decorator
3. Verify `pytest-asyncio` is installed

### Issue: Flush doesn't wait for handlers

**Symptom**: `flush()` returns immediately despite slow handlers

**Solution**:
1. Check that handlers are tracked in `_pending_futures`
2. Verify `concurrent.futures.wait()` is called with correct timeout
3. Ensure handlers are submitted to executor before flush

---

## Next Steps

After validation passes:

1. **Integration with F09**: Test `flush()` + `drain_events()` in F09 exit_cleanup
2. **Integration with F02**: Test `emit()` logging for `event_handler_error`
3. **Performance Profiling**: Measure latency and throughput under load
4. **Stress Testing**: 10,000+ events, 100+ subscribers, extended runtime

---

## References

- **Spec**: [spec.md](./spec.md)
- **Data Model**: [data-model.md](./data-model.md)
- **API Contract**: [contracts/event_bus_api.md](./contracts/event_bus_api.md)
- **Research Decisions**: [research.md](./research.md)
- **Task Breakdown**: [tasks.md](./tasks.md) (created by `/speckit.tasks`)
