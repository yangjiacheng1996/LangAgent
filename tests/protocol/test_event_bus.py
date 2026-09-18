"""
Tests for Event Bus implementation.

Following TDD approach: tests written first, then implementation.
"""

import pytest
import threading
import time
from langagent.protocol.event_bus import (
    Event,
    EventBus,
    SubscriptionToken,
    UnknownEventTypeError,
    EventDrainError,
)
from langagent.protocol.event_types import ALLOWED_EVENT_TYPES


# ============================================================================
# Phase 3: User Story 1 - Event Publication and Subscription Tests
# ============================================================================

def test_publish_subscribe_basic():
    """Test basic pub/sub: publish event and verify subscriber receives it."""
    bus = EventBus()
    received_events = []
    
    def handler(event: Event) -> None:
        received_events.append(event)
    
    # Subscribe to tool_call events
    token = bus.subscribe("tool_call", handler)
    
    # Publish an event
    event = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={"tool_name": "search", "query": "test"},
        trace_id="trace-123"
    )
    bus.publish(event)
    
    # Verify handler received the event
    assert len(received_events) == 1
    assert received_events[0] == event
    assert received_events[0].event_type == "tool_call"
    assert received_events[0].payload["tool_name"] == "search"


def test_publish_no_subscribers():
    """Test publishing event with no subscribers (should not raise error)."""
    bus = EventBus()
    
    event = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={"tool_name": "search"},
    )
    
    # Should not raise any error
    bus.publish(event)


def test_subscribe_returns_token():
    """Test that subscribe() returns a valid SubscriptionToken."""
    bus = EventBus()
    
    def handler(event: Event) -> None:
        pass
    
    token = bus.subscribe("tool_call", handler)
    
    # Verify token is of correct type
    assert isinstance(token, int)
    assert token >= 0


def test_unsubscribe_idempotent():
    """Test that unsubscribe() is idempotent (can call multiple times safely)."""
    bus = EventBus()
    received_events = []
    
    def handler(event: Event) -> None:
        received_events.append(event)
    
    token = bus.subscribe("tool_call", handler)
    
    # Unsubscribe once
    bus.unsubscribe(token)
    
    # Unsubscribe again (should not raise error)
    bus.unsubscribe(token)
    
    # Publish event - handler should not receive it
    event = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={},
    )
    bus.publish(event)
    
    assert len(received_events) == 0


def test_multiple_subscribers_same_event():
    """Test multiple handlers can subscribe to the same event type."""
    bus = EventBus()
    received_1 = []
    received_2 = []
    received_3 = []
    
    def handler1(event: Event) -> None:
        received_1.append(event)
    
    def handler2(event: Event) -> None:
        received_2.append(event)
    
    def handler3(event: Event) -> None:
        received_3.append(event)
    
    # Subscribe all three handlers
    token1 = bus.subscribe("tool_call", handler1)
    token2 = bus.subscribe("tool_call", handler2)
    token3 = bus.subscribe("tool_call", handler3)
    
    # Publish event
    event = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={"test": "data"},
    )
    bus.publish(event)
    
    # Verify all handlers received the event in FIFO order
    assert len(received_1) == 1
    assert len(received_2) == 1
    assert len(received_3) == 1
    assert received_1[0] == event
    assert received_2[0] == event
    assert received_3[0] == event


def test_publish_event_type_whitelist():
    """Test that publish() raises UnknownEventTypeError for invalid event types."""
    bus = EventBus()
    
    # Create event with invalid type
    event = Event(
        event_id="test-id",
        event_type="invalid_event_type_not_in_whitelist",
        emitted_at="2026-09-18T10:00:00Z",
        source="test_module",
        payload={},
        trace_id="-"
    )
    
    # Should raise UnknownEventTypeError
    with pytest.raises(UnknownEventTypeError) as exc_info:
        bus.publish(event)
    
    assert "invalid_event_type_not_in_whitelist" in str(exc_info.value)
    assert "not in whitelist" in str(exc_info.value).lower()


# ============================================================================
# Phase 4: User Story 2 - Error Isolation Tests
# ============================================================================

def test_publish_handler_error_isolated():
    """Test that handler exceptions don't prevent other handlers from executing."""
    bus = EventBus()
    received_1 = []
    received_2 = []
    received_3 = []
    
    def handler1(event: Event) -> None:
        received_1.append(event)
    
    def handler2_raises(event: Event) -> None:
        raise ValueError("Handler 2 intentionally raises exception")
    
    def handler3(event: Event) -> None:
        received_3.append(event)
    
    # Subscribe all handlers (handler2 will raise exception)
    bus.subscribe("tool_call", handler1)
    bus.subscribe("tool_call", handler2_raises)
    bus.subscribe("tool_call", handler3)
    
    # Publish event
    event = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={},
    )
    bus.publish(event)
    
    # Verify handler1 and handler3 still received event
    assert len(received_1) == 1
    assert len(received_3) == 1
    assert received_1[0] == event
    assert received_3[0] == event


def test_error_count_increments_on_handler_exception():
    """Test that internal error counter increments when handler raises exception."""
    bus = EventBus()
    
    def handler_raises(event: Event) -> None:
        raise RuntimeError("Test error")
    
    bus.subscribe("tool_call", handler_raises)
    
    # Publish event
    event = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={},
    )
    
    # Error count should be 0 initially
    assert bus._error_count == 0
    
    bus.publish(event)
    
    # Wait for async executor to complete
    bus.flush(timeout=1.0)
    
    # Error count should increment
    assert bus._error_count == 1
    
    # Publish again
    bus.publish(event)
    bus.flush(timeout=1.0)
    assert bus._error_count == 2


def test_handler_exception_logged_via_f02_emit(monkeypatch):
    """Test that handler exceptions are logged via F02 emit()."""
    # Track emit calls
    emit_calls = []
    
    def mock_emit(tag: str, payload: dict) -> None:
        emit_calls.append({"tag": tag, "payload": payload})
    
    # Mock the emit function at the cross_cutting.logger level
    monkeypatch.setattr("langagent.cross_cutting.logger.emit", mock_emit)
    
    # Create bus after monkeypatch is set up
    bus = EventBus()
    
    def handler_raises(event: Event) -> None:
        raise ValueError("Test exception message")
    
    token = bus.subscribe("tool_call", handler_raises)
    
    event = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={},
    )
    bus.publish(event)
    
    # Wait for async executor to complete
    bus.flush(timeout=1.0)
    
    # Verify emit was called with correct parameters
    assert len(emit_calls) == 1
    call = emit_calls[0]
    
    assert call["tag"] == "la.cross_cutting.event_handler_error"
    assert "ValueError" in call["payload"]["message"]
    assert "Test exception message" in call["payload"]["message"]


# ============================================================================
# Phase 5: User Story 3 - Async Handler Support Tests
# ============================================================================

@pytest.mark.asyncio
async def test_publish_async_handler():
    """Test async handlers work with publish_async()."""
    bus = EventBus()
    received_events = []
    
    async def async_handler(event: Event) -> None:
        await asyncio.sleep(0.01)  # Simulate async work
        received_events.append(event)
    
    bus.subscribe("tool_call", async_handler)
    
    event = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={},
    )
    
    await bus.publish_async(event)
    
    assert len(received_events) == 1
    assert received_events[0] == event


@pytest.mark.asyncio
async def test_publish_async_handler_exception_isolated():
    """Test async handler exceptions are isolated."""
    bus = EventBus()
    received_1 = []
    received_2 = []
    
    async def handler1(event: Event) -> None:
        received_1.append(event)
    
    async def handler2_raises(event: Event) -> None:
        raise ValueError("Async handler error")
    
    async def handler3(event: Event) -> None:
        await asyncio.sleep(0.01)
        received_2.append(event)
    
    bus.subscribe("tool_call", handler1)
    bus.subscribe("tool_call", handler2_raises)
    bus.subscribe("tool_call", handler3)
    
    event = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={},
    )
    
    await bus.publish_async(event)
    
    # Both handler1 and handler3 should still execute
    assert len(received_1) == 1
    assert len(received_2) == 1


@pytest.mark.asyncio
async def test_publish_async_with_sync_handler():
    """Test publish_async() can handle sync handlers (wrapped with asyncio.to_thread)."""
    bus = EventBus()
    received_events = []
    
    def sync_handler(event: Event) -> None:
        received_events.append(event)
    
    bus.subscribe("tool_call", sync_handler)
    
    event = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={},
    )
    
    await bus.publish_async(event)
    
    assert len(received_events) == 1
    assert received_events[0] == event


@pytest.mark.asyncio
async def test_publish_async_multiple_handlers_concurrent():
    """Test multiple async handlers run concurrently."""
    bus = EventBus()
    execution_order = []
    
    async def handler1(event: Event) -> None:
        execution_order.append("handler1_start")
        await asyncio.sleep(0.05)
        execution_order.append("handler1_end")
    
    async def handler2(event: Event) -> None:
        execution_order.append("handler2_start")
        await asyncio.sleep(0.02)
        execution_order.append("handler2_end")
    
    bus.subscribe("tool_call", handler1)
    bus.subscribe("tool_call", handler2)
    
    event = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={},
    )
    
    await bus.publish_async(event)
    
    # handler2 should finish before handler1 (concurrent execution)
    assert "handler2_end" in execution_order
    assert "handler1_end" in execution_order
    # Both should start before either finishes (concurrent)
    handler2_end_idx = execution_order.index("handler2_end")
    handler1_start_idx = execution_order.index("handler1_start")
    assert handler1_start_idx < handler2_end_idx


# ============================================================================
# Phase 6: User Story 4 - Graceful Shutdown Tests
# ============================================================================

def test_flush_waits_for_pending_sync_handlers():
    """Test flush() blocks until pending sync handlers complete."""
    bus = EventBus()
    execution_complete = []
    
    def slow_handler(event: Event) -> None:
        time.sleep(0.1)
        execution_complete.append(True)
    
    bus.subscribe("tool_call", slow_handler)
    
    event = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={},
    )
    
    bus.publish(event)
    
    # Flush should wait for handler to complete
    bus.flush(timeout=1.0)
    
    assert len(execution_complete) == 1


def test_flush_timeout_emits_event_handler_error_log(monkeypatch):
    """Test flush() logs warning when timeout occurs."""
    # Track emit calls
    emit_calls = []
    
    def mock_emit(tag: str, payload: dict) -> None:
        emit_calls.append({"tag": tag, "payload": payload})
    
    # Mock the emit function at the cross_cutting.logger level
    monkeypatch.setattr("langagent.cross_cutting.logger.emit", mock_emit)
    
    # Create bus after monkeypatch is set up
    bus = EventBus()
    
    def very_slow_handler(event: Event) -> None:
        time.sleep(5.0)  # Longer than timeout
    
    bus.subscribe("tool_call", very_slow_handler)
    
    event = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={},
    )
    
    bus.publish(event)
    
    # Flush with short timeout
    bus.flush(timeout=0.1)
    
    # Should have logged timeout warning
    assert len(emit_calls) > 0
    timeout_calls = [call for call in emit_calls 
                     if "timeout" in call["payload"].get("message", "").lower()]
    assert len(timeout_calls) > 0


def test_flush_no_pending_returns_immediately():
    """Test flush() returns immediately when no pending handlers."""
    bus = EventBus()
    
    start_time = time.time()
    bus.flush(timeout=1.0)
    elapsed = time.time() - start_time
    
    # Should return almost immediately (< 0.1 seconds)
    assert elapsed < 0.1


# ============================================================================
# Phase 7: User Story 5 - Event Drainage Tests
# ============================================================================

def test_drain_events_returns_accumulated():
    """Test drain_events() returns all accumulated events."""
    bus = EventBus()
    
    # Publish 5 events
    events = []
    for i in range(5):
        event = Event.create(
            event_type="tool_call",
            source="test_module",
            payload={"index": i},
        )
        events.append(event)
        bus.publish(event)
    
    # Drain events
    drained = bus.drain_events()
    
    assert len(drained) == 5
    for i, event in enumerate(drained):
        assert event.payload["index"] == i


def test_drain_events_clears_buffer():
    """Test drain_events() clears the buffer after draining."""
    bus = EventBus()
    
    # Publish 3 events
    for i in range(3):
        event = Event.create(
            event_type="tool_call",
            source="test_module",
            payload={"index": i},
        )
        bus.publish(event)
    
    # First drain
    drained1 = bus.drain_events()
    assert len(drained1) == 3
    
    # Second drain should return empty list
    drained2 = bus.drain_events()
    assert len(drained2) == 0


def test_drain_events_empty_when_no_pending():
    """Test drain_events() returns empty list when no events published."""
    bus = EventBus()
    
    drained = bus.drain_events()
    
    assert drained == []
    assert len(drained) == 0


def test_drain_events_thread_safe():
    """Test drain_events() is thread-safe (concurrent publish and drain)."""
    bus = EventBus()
    
    def publisher():
        for i in range(100):
            event = Event.create(
                event_type="tool_call",
                source="test_module",
                payload={"index": i},
            )
            bus.publish(event)
            time.sleep(0.001)
    
    # Start publisher thread
    thread = threading.Thread(target=publisher)
    thread.start()
    
    # Drain multiple times while publishing
    total_drained = 0
    for _ in range(10):
        time.sleep(0.01)
        drained = bus.drain_events()
        total_drained += len(drained)
    
    thread.join()
    
    # Drain any remaining
    final_drain = bus.drain_events()
    total_drained += len(final_drain)
    
    # Should have drained all 100 events
    assert total_drained == 100


def test_drain_events_with_pending_handlers_returns_after_flush():
    """Test drain_events() works correctly after flush()."""
    bus = EventBus()
    
    def handler(event: Event) -> None:
        time.sleep(0.05)
    
    bus.subscribe("tool_call", handler)
    
    event = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={},
    )
    
    bus.publish(event)
    bus.flush(timeout=1.0)
    
    # Drain after flush
    drained = bus.drain_events()
    
    assert len(drained) == 1
    assert drained[0] == event


def test_drain_events_raises_event_drain_error_on_failure(monkeypatch):
    """Test drain_events() raises EventDrainError on internal failure."""
    bus = EventBus()
    
    # Publish one event first
    event = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={},
    )
    bus.publish(event)
    
    # Mock the _lock to raise exception during context manager
    class FailingLock:
        def __enter__(self):
            raise RuntimeError("Simulated lock failure")
        
        def __exit__(self, *args):
            pass
    
    monkeypatch.setattr(bus, "_lock", FailingLock())
    
    # Should raise EventDrainError
    with pytest.raises(EventDrainError) as exc_info:
        bus.drain_events()
    
    assert "Failed to drain event buffer" in str(exc_info.value)


# ============================================================================
# Additional imports needed for async tests
# ============================================================================
import asyncio
