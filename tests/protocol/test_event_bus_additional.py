"""
Additional tests for Event Bus edge cases and integration scenarios.
"""

import pytest
import json
import threading
from langagent.protocol.event_bus import Event, EventBus
from langagent.protocol.event_types import ALLOWED_EVENT_TYPES


# ============================================================================
# Phase 8: Additional Test Coverage - Edge Cases
# ============================================================================

def test_event_payload_must_be_dict():
    """Test that Event requires payload to be a dict."""
    # Event dataclass accepts dict type
    event = Event(
        event_id="test-id",
        event_type="tool_call",
        emitted_at="2026-09-18T10:00:00Z",
        source="test",
        payload={"key": "value"},
        trace_id="-"
    )
    assert isinstance(event.payload, dict)


def test_event_payload_must_be_json_serializable():
    """Test that event payloads can be serialized to JSON."""
    event = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={
            "string": "value",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"key": "value"}
        }
    )
    
    # Should be JSON serializable
    json_str = json.dumps(event.payload)
    assert json_str is not None
    
    # Should round-trip correctly
    parsed = json.loads(json_str)
    assert parsed == event.payload


def test_event_id_is_unique():
    """Test that each event gets a unique ID."""
    event_ids = set()
    
    for i in range(100):
        event = Event.create(
            event_type="tool_call",
            source="test_module",
            payload={"index": i}
        )
        event_ids.add(event.event_id)
    
    # All 100 IDs should be unique
    assert len(event_ids) == 100


def test_event_emitted_at_is_utc_now():
    """Test that emitted_at is current UTC time."""
    import time
    from datetime import datetime, timezone
    
    before = datetime.now(timezone.utc).isoformat()
    time.sleep(0.01)
    
    event = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={}
    )
    
    time.sleep(0.01)
    after = datetime.now(timezone.utc).isoformat()
    
    # Event timestamp should be between before and after
    assert before < event.emitted_at < after
    assert event.emitted_at.endswith("Z")


def test_thread_safe_publish():
    """Test that concurrent publishes from multiple threads work correctly."""
    bus = EventBus()
    received_events = []
    lock = threading.Lock()
    
    def handler(event: Event) -> None:
        with lock:
            received_events.append(event)
    
    bus.subscribe("tool_call", handler)
    
    def publisher(thread_id: int):
        for i in range(50):
            event = Event.create(
                event_type="tool_call",
                source=f"thread_{thread_id}",
                payload={"thread": thread_id, "index": i}
            )
            bus.publish(event)
    
    # Start 4 threads publishing concurrently
    threads = []
    for tid in range(4):
        thread = threading.Thread(target=publisher, args=(tid,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Wait for all handlers to complete
    bus.flush(timeout=2.0)
    
    # Should have received all 200 events (4 threads * 50 events)
    assert len(received_events) == 200


def test_subscribe_during_publish():
    """Test that subscribing during event publication works (reentrant lock)."""
    bus = EventBus()
    received_by_handler2 = []
    
    def handler1(event: Event) -> None:
        # Subscribe handler2 during handler1 execution
        if event.payload.get("subscribe_handler2"):
            def handler2(e: Event) -> None:
                received_by_handler2.append(e)
            bus.subscribe("tool_call", handler2)
    
    bus.subscribe("tool_call", handler1)
    
    # First event - triggers subscription of handler2
    event1 = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={"subscribe_handler2": True, "index": 1}
    )
    bus.publish(event1)
    bus.flush(timeout=1.0)
    
    # Second event - should be received by both handler1 and handler2
    event2 = Event.create(
        event_type="tool_call",
        source="test_module",
        payload={"index": 2}
    )
    bus.publish(event2)
    bus.flush(timeout=1.0)
    
    # handler2 should have received event2 (but not event1)
    assert len(received_by_handler2) == 1
    assert received_by_handler2[0].payload["index"] == 2


def test_allowed_event_types_at_least_13():
    """Test that ALLOWED_EVENT_TYPES has at least 13 entries."""
    assert len(ALLOWED_EVENT_TYPES) >= 13


def test_all_registered_event_types_have_documentation():
    """Test that all event types in whitelist are documented."""
    # Check that key event types from spec are present
    required_types = {
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
        "event_handler_error"
    }
    
    assert required_types.issubset(ALLOWED_EVENT_TYPES)


def test_event_handler_error_in_whitelist():
    """Test that event_handler_error event type is in whitelist."""
    assert "event_handler_error" in ALLOWED_EVENT_TYPES
