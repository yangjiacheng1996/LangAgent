"""Tests for EventBusProtocol interface (User Story 5).

TDD approach: All tests written FIRST and must FAIL before implementation.
"""
import pytest
from typing import Any, Callable

from langagent.cross_cutting.logger import EventBusProtocol


# ===== User Story 5: EventBusProtocol Interface =====


def test_event_bus_protocol_has_publish_method():
    """Test EventBusProtocol has publish method signature."""
    # Create a mock implementation
    class MockEventBus:
        def publish(self, event_type: str, payload: dict[str, Any]) -> None:
            pass
        
        def subscribe(self, event_type: str, callback: Callable[[dict[str, Any]], None]) -> str:
            return "sub_id"
        
        def unsubscribe(self, subscription_id: str) -> None:
            pass
        
        def flush(self) -> None:
            pass
    
    mock = MockEventBus()
    
    # Verify it implements the protocol
    assert isinstance(mock, EventBusProtocol)
    
    # Verify publish method exists and has correct signature
    assert hasattr(mock, "publish")
    assert callable(mock.publish)


def test_event_bus_protocol_has_subscribe_method():
    """Test EventBusProtocol has subscribe method returning str."""
    class MockEventBus:
        def publish(self, event_type: str, payload: dict[str, Any]) -> None:
            pass
        
        def subscribe(self, event_type: str, callback: Callable[[dict[str, Any]], None]) -> str:
            return "subscription_123"
        
        def unsubscribe(self, subscription_id: str) -> None:
            pass
        
        def flush(self) -> None:
            pass
    
    mock = MockEventBus()
    
    # Verify it implements the protocol
    assert isinstance(mock, EventBusProtocol)
    
    # Verify subscribe returns str
    def dummy_callback(payload: dict[str, Any]) -> None:
        pass
    
    sub_id = mock.subscribe("test.event", dummy_callback)
    assert isinstance(sub_id, str)


def test_event_bus_protocol_has_unsubscribe_method():
    """Test EventBusProtocol has unsubscribe method."""
    class MockEventBus:
        def publish(self, event_type: str, payload: dict[str, Any]) -> None:
            pass
        
        def subscribe(self, event_type: str, callback: Callable[[dict[str, Any]], None]) -> str:
            return "sub_id"
        
        def unsubscribe(self, subscription_id: str) -> None:
            pass
        
        def flush(self) -> None:
            pass
    
    mock = MockEventBus()
    
    # Verify it implements the protocol
    assert isinstance(mock, EventBusProtocol)
    
    # Verify unsubscribe method exists
    assert hasattr(mock, "unsubscribe")
    assert callable(mock.unsubscribe)


def test_event_bus_protocol_has_flush_method():
    """Test EventBusProtocol has flush method."""
    class MockEventBus:
        def publish(self, event_type: str, payload: dict[str, Any]) -> None:
            pass
        
        def subscribe(self, event_type: str, callback: Callable[[dict[str, Any]], None]) -> str:
            return "sub_id"
        
        def unsubscribe(self, subscription_id: str) -> None:
            pass
        
        def flush(self) -> None:
            pass
    
    mock = MockEventBus()
    
    # Verify it implements the protocol
    assert isinstance(mock, EventBusProtocol)
    
    # Verify flush method exists
    assert hasattr(mock, "flush")
    assert callable(mock.flush)


def test_event_bus_protocol_runtime_checkable():
    """Test EventBusProtocol is runtime_checkable."""
    # A class without all methods should NOT satisfy the protocol
    class IncompleteEventBus:
        def publish(self, event_type: str, payload: dict[str, Any]) -> None:
            pass
    
    incomplete = IncompleteEventBus()
    
    # This should fail at runtime check
    assert not isinstance(incomplete, EventBusProtocol)
    
    # A complete implementation should pass
    class CompleteEventBus:
        def publish(self, event_type: str, payload: dict[str, Any]) -> None:
            pass
        
        def subscribe(self, event_type: str, callback: Callable[[dict[str, Any]], None]) -> str:
            return "sub_id"
        
        def unsubscribe(self, subscription_id: str) -> None:
            pass
        
        def flush(self) -> None:
            pass
    
    complete = CompleteEventBus()
    assert isinstance(complete, EventBusProtocol)
