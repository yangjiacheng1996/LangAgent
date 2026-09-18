"""Tests for F02 Phase 2: Metrics Collector.

TDD approach: Tests written first (Red), then implementation (Green), then refactor.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch
import threading
import time

from langagent.cross_cutting.metrics_collector import (
    MetricsSnapshot,
    LatencySample,
    TokenUsageSample,
    ErrorSample,
    record_latency,
    record_token_usage,
    record_error,
    snapshot,
    flush,
    initialize,
    _calculate_percentiles,
    _calculate_error_rate,
    _aggregate_token_usage,
    _calculate_cost_usd,
    _is_duplicate_event,
    _purge_old_event_ids,
    _load_pricing_table,
)


@pytest.fixture(autouse=True)
def reset_metrics():
    """Clear all metrics before each test."""
    flush()
    yield
    flush()


# Phase 2: Foundational Tests
def test_snapshot_returns_frozen_dataclass():
    """T009: MetricsSnapshot must be immutable."""
    start = datetime.now(timezone.utc)
    end = start + timedelta(seconds=1)
    
    snap = snapshot(start, end)
    
    # Verify frozen dataclass
    assert hasattr(snap, '__dataclass_fields__')
    with pytest.raises(AttributeError):
        snap.sample_count = 999  # Should fail - frozen dataclass


def test_dataclass_field_types_and_defaults():
    """T011: Verify dataclass field types match spec."""
    start = datetime.now(timezone.utc)
    end = start + timedelta(seconds=1)
    
    snap = snapshot(start, end)
    
    # Verify field types
    assert isinstance(snap.window_start, datetime)
    assert isinstance(snap.window_end, datetime)
    assert isinstance(snap.sample_count, int)
    assert snap.p50_latency_ms is None or isinstance(snap.p50_latency_ms, float)
    assert snap.p95_latency_ms is None or isinstance(snap.p95_latency_ms, float)
    assert snap.p99_latency_ms is None or isinstance(snap.p99_latency_ms, float)
    assert isinstance(snap.error_rate, float)
    assert isinstance(snap.token_usage, dict)
    assert isinstance(snap.cost_usd, float)


# Phase 3: User Story 5 - Event Bus Integration Tests
def test_subscribe_to_event_bus():
    """T012: Verify model_response event → record_token_usage() auto-called."""
    mock_bus = Mock()
    mock_bus.subscribe = Mock()
    
    initialize(mock_bus)
    
    # Verify subscriptions
    assert mock_bus.subscribe.call_count == 4
    # Extract just the event types (first argument of each call)
    event_types = [call[0][0] for call in mock_bus.subscribe.call_args_list]
    assert "tool_call" in event_types
    assert "model_response" in event_types


def test_subscribe_to_event_bus_tool_call():
    """T013: Verify tool_call event → record_latency() auto-called."""
    mock_bus = Mock()
    subscribers = {}
    
    def mock_subscribe(event_type, callback):
        subscribers[event_type] = callback
        return f"sub_{event_type}"
    
    mock_bus.subscribe = mock_subscribe
    initialize(mock_bus)
    
    # Simulate tool_call event
    tool_call_handler = subscribers["tool_call"]
    tool_call_handler({
        "event_id": "test-uuid-123",
        "operation": "web_search",
        "latency_ms": 250.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Verify latency recorded
    start = datetime.now(timezone.utc) - timedelta(seconds=1)
    end = datetime.now(timezone.utc) + timedelta(seconds=1)
    snap = snapshot(start, end)
    assert snap.sample_count == 1


def test_malformed_event_missing_latency():
    """T014: Event without latency_ms → log warning, skip, no crash."""
    mock_bus = Mock()
    subscribers = {}
    
    def mock_subscribe(event_type, callback):
        subscribers[event_type] = callback
        return f"sub_{event_type}"
    
    mock_bus.subscribe = mock_subscribe
    initialize(mock_bus)
    
    # Simulate malformed event
    tool_call_handler = subscribers["tool_call"]
    tool_call_handler({
        "event_id": "test-uuid-456",
        "operation": "web_search"
        # Missing latency_ms
    })
    
    # Should not crash, no samples recorded
    start = datetime.now(timezone.utc) - timedelta(seconds=1)
    end = datetime.now(timezone.utc) + timedelta(seconds=1)
    snap = snapshot(start, end)
    assert snap.sample_count == 0


def test_malformed_event_missing_event_id():
    """T015: Event without event_id → log warning, skip, no crash."""
    mock_bus = Mock()
    subscribers = {}
    
    def mock_subscribe(event_type, callback):
        subscribers[event_type] = callback
        return f"sub_{event_type}"
    
    mock_bus.subscribe = mock_subscribe
    initialize(mock_bus)
    
    # Simulate event missing event_id
    tool_call_handler = subscribers["tool_call"]
    tool_call_handler({
        "operation": "web_search",
        "latency_ms": 250.0
        # Missing event_id
    })
    
    # Should not crash, no samples recorded
    start = datetime.now(timezone.utc) - timedelta(seconds=1)
    end = datetime.now(timezone.utc) + timedelta(seconds=1)
    snap = snapshot(start, end)
    assert snap.sample_count == 0


# Phase 4: User Story 1 - Automatic Collection Tests
def test_record_latency_increments_sample_count():
    """T026: 100 calls → snapshot().sample_count == 100."""
    start = datetime.now(timezone.utc)
    
    for i in range(100):
        record_latency("test_op", 10.0 + i, event_id=f"evt-{i}")
    
    end = datetime.now(timezone.utc)
    snap = snapshot(start, end)
    
    assert snap.sample_count == 100


def test_snapshot_token_usage_by_model():
    """T027: Verify per-model token aggregation."""
    start = datetime.now(timezone.utc)
    
    record_token_usage("gpt-4o", 1000, 500, event_id="evt-1")
    record_token_usage("gpt-4o", 500, 250, event_id="evt-2")
    record_token_usage("gpt-4o-mini", 2000, 1000, event_id="evt-3")
    
    end = datetime.now(timezone.utc)
    snap = snapshot(start, end)
    
    assert snap.token_usage["gpt-4o"] == 1500 + 750  # 2250 total
    assert snap.token_usage["gpt-4o-mini"] == 3000


def test_snapshot_error_rate():
    """T028: 5 errors in 100 ops → error_rate == 0.05."""
    start = datetime.now(timezone.utc)
    
    # Record 95 successful operations
    for i in range(95):
        record_latency("test_op", 10.0, event_id=f"success-{i}")
    
    # Record 5 errors
    for i in range(5):
        record_error("test_op", event_id=f"error-{i}")
    
    end = datetime.now(timezone.utc)
    snap = snapshot(start, end)
    
    assert abs(snap.error_rate - 0.05) < 0.001


def test_event_deduplication_within_window():
    """T029: Same event_id twice within 10 min → only first recorded."""
    start = datetime.now(timezone.utc)
    
    record_latency("test_op", 10.0, event_id="duplicate-id")
    record_latency("test_op", 20.0, event_id="duplicate-id")  # Should be ignored
    
    end = datetime.now(timezone.utc)
    snap = snapshot(start, end)
    
    assert snap.sample_count == 1


def test_event_deduplication_window_expiry():
    """T030: event_id older than 10 min can be reused."""
    old_time = datetime.now(timezone.utc) - timedelta(minutes=11)
    current_time = datetime.now(timezone.utc)
    
    # Record old event
    record_latency("test_op", 10.0, event_id="reused-id", timestamp=old_time)
    
    # Record new event with same ID (should be allowed after 10 min)
    # The second call should trigger purge and allow reuse
    record_latency("test_op", 20.0, event_id="reused-id", timestamp=current_time)
    
    # Check all samples (both old and new windows)
    start = old_time - timedelta(seconds=1)
    end = current_time + timedelta(seconds=1)
    snap = snapshot(start, end)
    
    # Should have 2 samples total (old one + new one after purge allowed reuse)
    assert snap.sample_count == 2


def test_flush_clears_data():
    """T041b: Verify flush() clears all data."""
    start = datetime.now(timezone.utc)
    
    record_latency("test_op", 10.0, event_id="evt-1")
    record_token_usage("gpt-4o", 1000, 500, event_id="evt-2")
    record_error("test_op", event_id="evt-3")
    
    flush()
    
    end = datetime.now(timezone.utc)
    snap = snapshot(start, end)
    
    assert snap.sample_count == 0
    assert snap.token_usage == {}
    assert snap.error_rate == 0.0


# Phase 5: User Story 4 - Percentile Reporting Tests
def test_snapshot_p50_latency():
    """T043: Verify p50 ≈ 60ms for uniform 10-110ms distribution."""
    start = datetime.now(timezone.utc)
    
    for i in range(101):
        record_latency("test_op", 10.0 + i, event_id=f"evt-{i}")
    
    end = datetime.now(timezone.utc)
    snap = snapshot(start, end)
    
    assert snap.p50_latency_ms is not None
    assert abs(snap.p50_latency_ms - 60.0) < 5.0  # Within 5ms tolerance


def test_snapshot_p95_latency():
    """T044: Verify p95 ≈ 105ms for same distribution."""
    start = datetime.now(timezone.utc)
    
    for i in range(101):
        record_latency("test_op", 10.0 + i, event_id=f"evt-{i}")
    
    end = datetime.now(timezone.utc)
    snap = snapshot(start, end)
    
    assert snap.p95_latency_ms is not None
    assert abs(snap.p95_latency_ms - 105.0) < 5.0


def test_snapshot_p99_latency():
    """T045: Verify p99 ≈ 109ms for same distribution."""
    start = datetime.now(timezone.utc)
    
    for i in range(101):
        record_latency("test_op", 10.0 + i, event_id=f"evt-{i}")
    
    end = datetime.now(timezone.utc)
    snap = snapshot(start, end)
    
    assert snap.p99_latency_ms is not None
    assert abs(snap.p99_latency_ms - 109.0) < 5.0


def test_empty_snapshot_returns_none_percentiles():
    """T046: No samples → p50/p95/p99 all None."""
    start = datetime.now(timezone.utc)
    end = start + timedelta(seconds=1)
    
    snap = snapshot(start, end)
    
    assert snap.p50_latency_ms is None
    assert snap.p95_latency_ms is None
    assert snap.p99_latency_ms is None


# Phase 6: User Story 2 - Time-Window Snapshots Tests
def test_snapshot_window_filter():
    """T051: Verify samples outside window excluded."""
    base_time = datetime.now(timezone.utc)
    
    # Record at different times
    record_latency("test_op", 10.0, event_id="evt-1", 
                   timestamp=base_time - timedelta(seconds=10))
    record_latency("test_op", 20.0, event_id="evt-2", 
                   timestamp=base_time)
    record_latency("test_op", 30.0, event_id="evt-3", 
                   timestamp=base_time + timedelta(seconds=10))
    
    # Query middle window only
    window_start = base_time - timedelta(seconds=1)
    window_end = base_time + timedelta(seconds=1)
    snap = snapshot(window_start, window_end)
    
    assert snap.sample_count == 1  # Only middle sample


def test_non_overlapping_window_snapshots():
    """T052: Metrics over 60s split into [0:30] and [30:60]."""
    base_time = datetime.now(timezone.utc)
    
    # Record samples over 60 seconds
    for i in range(60):
        record_latency("test_op", 10.0, event_id=f"evt-{i}",
                      timestamp=base_time + timedelta(seconds=i))
    
    # Query first 30 seconds
    snap1 = snapshot(base_time, base_time + timedelta(seconds=30))
    
    # Query next 30 seconds
    snap2 = snapshot(base_time + timedelta(seconds=30), 
                    base_time + timedelta(seconds=60))
    
    assert snap1.sample_count == 30
    assert snap2.sample_count == 30


# Phase 7: User Story 3 - Cost Estimation Tests
def test_snapshot_cost_usd(tmp_path):
    """T056: Verify cost calculation with mock pricing table."""
    pricing_file = tmp_path / "pricing.json"
    pricing_file.write_text('{"gpt-4o": {"prompt": 0.005, "completion": 0.015}}')
    
    mock_bus = Mock()
    mock_bus.subscribe = Mock()
    initialize(mock_bus, pricing_table_path=str(pricing_file))
    
    start = datetime.now(timezone.utc)
    
    # 1000 prompt + 500 completion = 1500 total tokens
    record_token_usage("gpt-4o", 1000, 500, event_id="evt-1")
    
    end = datetime.now(timezone.utc)
    snap = snapshot(start, end)
    
    # Cost = (1500 / 1000) * avg(0.005, 0.015) = 1.5 * 0.01 = 0.015
    assert abs(snap.cost_usd - 0.015) < 0.001


def test_pricing_table_from_json_file(tmp_path):
    """T057: Load pricing from JSON file at specified path."""
    pricing_file = tmp_path / "test_pricing.json"
    pricing_file.write_text('{"test-model": {"prompt": 0.001, "completion": 0.002}}')
    
    pricing = _load_pricing_table(str(pricing_file))
    
    assert "test-model" in pricing
    assert pricing["test-model"]["prompt"] == 0.001


def test_pricing_table_default_fallback():
    """T058: When path not specified, use built-in default prices."""
    pricing = _load_pricing_table("/nonexistent/path.json")
    
    # Should fall back to defaults
    assert "gpt-4o" in pricing
    assert "gpt-4o-mini" in pricing


def test_unknown_model_logs_warning():
    """T059: Unknown model → logs warning, contributes 0 to cost."""
    start = datetime.now(timezone.utc)
    
    record_token_usage("unknown-model-xyz", 1000, 500, event_id="evt-1")
    
    end = datetime.now(timezone.utc)
    snap = snapshot(start, end)
    
    # Should still record token usage
    assert snap.token_usage["unknown-model-xyz"] == 1500
    # Cost should be 0.0 (warning logged)
    assert snap.cost_usd == 0.0


# Phase 8: Polish & Cross-Cutting Tests
def test_thread_safe_concurrent_recording():
    """T066: 10 threads × 1000 records = 10000 total, no data corruption."""
    start = datetime.now(timezone.utc)
    
    def worker(thread_id):
        for i in range(1000):
            record_latency("concurrent_op", 50.0, event_id=f"t{thread_id}-{i}")
    
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    end = datetime.now(timezone.utc)
    snap = snapshot(start, end)
    
    assert snap.sample_count == 10000


def test_snapshot_concurrent_calls():
    """T067: Verify consistent view with concurrent snapshot() calls."""
    start = datetime.now(timezone.utc)
    
    for i in range(100):
        record_latency("test_op", 10.0, event_id=f"evt-{i}")
    
    end = datetime.now(timezone.utc)
    
    results = []
    def snapshot_worker():
        s = snapshot(start, end)
        results.append(s.sample_count)
    
    threads = [threading.Thread(target=snapshot_worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # All should see the same count
    assert all(count == 100 for count in results)


def test_flush_during_event_processing():
    """T068: Verify no data loss when flush() during concurrent recording."""
    def recorder():
        for i in range(100):
            record_latency("test_op", 10.0, event_id=f"flush-test-{i}")
            time.sleep(0.001)
    
    recorder_thread = threading.Thread(target=recorder)
    recorder_thread.start()
    
    time.sleep(0.05)  # Let some records accumulate
    flush()  # Flush during recording
    
    recorder_thread.join()
    
    # No crash, operation completes successfully


def test_window_validation():
    """Verify ValueError when window_end < window_start."""
    start = datetime.now(timezone.utc)
    end = start - timedelta(seconds=1)
    
    with pytest.raises(ValueError, match="window_end.*must be.*window_start"):
        snapshot(start, end)


def test_record_latency_performance():
    """T074: Verify record_latency() completes in < 1ms."""
    iterations = 1000
    
    start_time = time.perf_counter()
    for i in range(iterations):
        record_latency("perf_test", 10.0, event_id=f"perf-{i}")
    end_time = time.perf_counter()
    
    avg_time_ms = ((end_time - start_time) / iterations) * 1000
    assert avg_time_ms < 1.0, f"Average time {avg_time_ms}ms exceeds 1ms threshold"


def test_snapshot_performance_10k_samples():
    """T075: Verify snapshot() with 10K samples completes in < 100ms."""
    start = datetime.now(timezone.utc)
    
    for i in range(10000):
        record_latency("perf_test", 10.0 + (i % 100), event_id=f"perf-{i}")
    
    end = datetime.now(timezone.utc)
    
    snapshot_start = time.perf_counter()
    snap = snapshot(start, end)
    snapshot_end = time.perf_counter()
    
    snapshot_time_ms = (snapshot_end - snapshot_start) * 1000
    assert snapshot_time_ms < 100.0, f"Snapshot time {snapshot_time_ms}ms exceeds 100ms threshold"
    assert snap.sample_count == 10000


def test_no_hardcoded_paths():
    """T076: Verify no hard-coded paths, pricing table path configurable."""
    # Test env var override
    with patch.dict('os.environ', {'LANGAGENT_PRICING_TABLE_PATH': '/custom/path.json'}):
        with patch('builtins.open', side_effect=FileNotFoundError):
            pricing = _load_pricing_table(None)
            # Should fall back to defaults when custom path not found
            assert "gpt-4o" in pricing


def test_metrics_snapshot_immutability():
    """T079: Verify MetricsSnapshot is frozen dataclass."""
    start = datetime.now(timezone.utc)
    end = start + timedelta(seconds=1)
    
    snap = snapshot(start, end)
    
    # Attempt to modify should fail
    with pytest.raises(AttributeError):
        snap.sample_count = 999
    
    with pytest.raises(AttributeError):
        snap.cost_usd = 123.45


def test_integration_event_bus_full_flow(tmp_path):
    """T080: Mock event bus, publish 100 events, verify metrics collected."""
    pricing_file = tmp_path / "pricing.json"
    pricing_file.write_text('{"gpt-4o": {"prompt": 0.005, "completion": 0.015}}')
    
    mock_bus = Mock()
    subscribers = {}
    
    def mock_subscribe(event_type, callback):
        subscribers[event_type] = callback
        return f"sub_{event_type}"
    
    mock_bus.subscribe = mock_subscribe
    initialize(mock_bus, pricing_table_path=str(pricing_file))
    
    start = datetime.now(timezone.utc)
    
    # Publish 50 tool_call events
    for i in range(50):
        subscribers["tool_call"]({
            "event_id": f"tool-{i}",
            "operation": "web_search",
            "latency_ms": 100.0 + i,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    # Publish 50 model_response events
    for i in range(50):
        subscribers["model_response"]({
            "event_id": f"model-{i}",
            "model_name": "gpt-4o",
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    end = datetime.now(timezone.utc)
    snap = snapshot(start, end)
    
    assert snap.sample_count == 50  # Only latency samples count
    assert snap.token_usage["gpt-4o"] == 50 * 150  # 7500 total tokens
    assert snap.cost_usd > 0  # Should have calculated cost


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
