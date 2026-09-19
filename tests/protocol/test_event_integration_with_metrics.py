"""
Integration tests for protocol_event_bus with cross_cutting_metrics_collector.

Tests event bus integration with F02 metrics collector:
- tool_call events trigger record_latency
- model_response events trigger record_token_usage
- guardrail_block events trigger record_error
"""
import time
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from langagent.protocol.event_bus import EventBus, Event
from langagent.protocol.event_types import ALLOWED_EVENT_TYPES


def test_metrics_collector_receives_tool_call_event():
    """
    Test that publishing tool_call event triggers metrics_collector.record_latency.
    
    Verifies F03 → F02 integration for tool_call events.
    """
    # Arrange
    bus = EventBus()
    
    # Mock metrics_collector.record_latency
    with patch('langagent.cross_cutting.metrics_collector.record_latency') as mock_record:
        # Create handler that calls record_latency
        def metrics_handler(event: Event) -> None:
            if 'latency_ms' in event.payload:
                from langagent.cross_cutting import metrics_collector
                metrics_collector.record_latency(
                    operation='tool_call',
                    ms=event.payload['latency_ms'],
                    event_id=event.event_id
                )
        
        # Subscribe handler to tool_call
        token = bus.subscribe('tool_call', metrics_handler)
        
        # Act: Publish tool_call event
        event = Event(
            event_id='test-tool-call-1',
            event_type='tool_call',
            emitted_at=datetime.now(timezone.utc),
            source='test_integration',
            payload={
                'tool_name': 'bash',
                'latency_ms': 150.5
            },
            trace_id='trace-123'
        )
        bus.publish(event)
        
        # Wait for async handler to complete
        bus.flush(timeout=2.0)
        
        # Assert: record_latency was called
        mock_record.assert_called_once_with(
            operation='tool_call',
            ms=150.5,
            event_id='test-tool-call-1'
        )
        
        # Cleanup
        bus.unsubscribe(token)


def test_metrics_collector_receives_model_response_event():
    """
    Test that publishing model_response event triggers metrics_collector.record_token_usage.
    
    Verifies F03 → F02 integration for model_response events with usage_metadata.
    """
    # Arrange
    bus = EventBus()
    
    # Mock metrics_collector.record_token_usage
    with patch('langagent.cross_cutting.metrics_collector.record_token_usage') as mock_record:
        # Create handler that calls record_token_usage
        def metrics_handler(event: Event) -> None:
            usage = event.payload.get('usage_metadata')
            if usage:
                from langagent.cross_cutting import metrics_collector
                metrics_collector.record_token_usage(
                    model_name=event.payload.get('model_name', 'unknown'),
                    prompt=usage.get('input_tokens', 0),
                    completion=usage.get('output_tokens', 0),
                    event_id=event.event_id
                )
        
        # Subscribe handler to model_response
        token = bus.subscribe('model_response', metrics_handler)
        
        # Act: Publish model_response event
        event = Event(
            event_id='test-model-response-1',
            event_type='model_response',
            emitted_at=datetime.now(timezone.utc),
            source='test_integration',
            payload={
                'model_name': 'gpt-4o',
                'usage_metadata': {
                    'input_tokens': 100,
                    'output_tokens': 50
                }
            },
            trace_id='trace-456'
        )
        bus.publish(event)
        
        # Wait for async handler to complete
        bus.flush(timeout=2.0)
        
        # Assert: record_token_usage was called
        mock_record.assert_called_once_with(
            model_name='gpt-4o',
            prompt=100,
            completion=50,
            event_id='test-model-response-1'
        )
        
        # Cleanup
        bus.unsubscribe(token)


def test_metrics_collector_receives_guardrail_block_event():
    """
    Test that publishing guardrail_block event triggers metrics_collector.record_error.
    
    Verifies F03 → F02 integration for guardrail_block events.
    """
    # Arrange
    bus = EventBus()
    
    # Mock metrics_collector.record_error
    with patch('langagent.cross_cutting.metrics_collector.record_error') as mock_record:
        # Create handler that calls record_error
        def metrics_handler(event: Event) -> None:
            from langagent.cross_cutting import metrics_collector
            metrics_collector.record_error(
                operation='guardrail_block',
                event_id=event.event_id
            )
        
        # Subscribe handler to guardrail_block
        token = bus.subscribe('guardrail_block', metrics_handler)
        
        # Act: Publish guardrail_block event
        event = Event(
            event_id='test-guardrail-1',
            event_type='guardrail_block',
            emitted_at=datetime.now(timezone.utc),
            source='test_integration',
            payload={
                'rule_id': 'no_pii',
                'blocked_content': 'SSN: 123-45-6789'
            },
            trace_id='trace-789'
        )
        bus.publish(event)
        
        # Wait for async handler to complete
        bus.flush(timeout=2.0)
        
        # Assert: record_error was called
        mock_record.assert_called_once_with(
            operation='guardrail_block',
            event_id='test-guardrail-1'
        )
        
        # Cleanup
        bus.unsubscribe(token)
