"""Cross-cutting metrics collector with automatic event-based collection.

F02 Phase 2: Metrics collection and aggregation for LangAgent observability.
"""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional
import threading
import json
import os
from pathlib import Path
import statistics

from langagent.cross_cutting.logger import EventBusProtocol, emit


# Internal data structures for sample storage
@dataclass
class LatencySample:
    """Internal: Single latency measurement."""
    operation: str
    latency_ms: float
    timestamp: datetime
    event_id: str


@dataclass
class TokenUsageSample:
    """Internal: Single token usage measurement."""
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    timestamp: datetime
    event_id: str


@dataclass
class ErrorSample:
    """Internal: Single error occurrence."""
    operation: str
    timestamp: datetime
    event_id: str


# Public output type
@dataclass(frozen=True)
class MetricsSnapshot:
    """Immutable time-windowed metrics summary.
    
    Per module_schemas.md#schema-metrics-snapshot - 9 fields.
    """
    window_start: datetime
    window_end: datetime
    sample_count: int
    p50_latency_ms: Optional[float]
    p95_latency_ms: Optional[float]
    p99_latency_ms: Optional[float]
    error_rate: float
    token_usage: dict[str, int]
    cost_usd: float


# Module-level state (protected by _lock)
_lock = threading.Lock()
_latency_samples: list[LatencySample] = []
_token_samples: list[TokenUsageSample] = []
_error_samples: list[ErrorSample] = []
_event_id_window: dict[str, datetime] = {}  # event_id -> timestamp
_pricing_table: dict[str, dict[str, float]] = {}
_eval_task_start_times: dict[str, datetime] = {}  # task_id -> start_time


# Constants
_DEDUP_WINDOW_MINUTES = 10
_DEFAULT_PRICING = {
    "gpt-4o": {"prompt": 0.005, "completion": 0.015},
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
    "qwen3-8b": {"prompt": 0.0, "completion": 0.0},
}


def _load_pricing_table(path: str | None) -> dict[str, dict[str, float]]:
    """Load pricing table from JSON file or use defaults.
    
    Args:
        path: Optional path to pricing table JSON file.
              If None, checks LANGAGENT_PRICING_TABLE_PATH env var.
              Falls back to ~/.local/share/langagent/pricing.json.
              If file not found, uses built-in defaults.
    
    Returns:
        Pricing table dict: {model_name: {prompt: float, completion: float}}
    """
    if path is None:
        path = os.environ.get("LANGAGENT_PRICING_TABLE_PATH")
    
    if path is None:
        path = str(Path.home() / ".local" / "share" / "langagent" / "pricing.json")
    
    try:
        with open(path, 'r') as f:
            loaded = json.load(f)
            return loaded
    except FileNotFoundError:
        return _DEFAULT_PRICING.copy()
    except Exception as e:
        emit("la.cross_cutting.metrics.emit", 
             {"message": f"Failed to load pricing table from {path}: {e}, using defaults"})
        return _DEFAULT_PRICING.copy()


def _is_duplicate_event(event_id: str, timestamp: datetime) -> bool:
    """Check if event_id exists in deduplication window.
    
    Must be called with _lock held.
    
    Args:
        event_id: Unique event identifier
        timestamp: Event timestamp
    
    Returns:
        True if event is duplicate (within 10-minute window), False otherwise
    """
    # First purge old entries to check if this event_id is still in the window
    cutoff = timestamp - timedelta(minutes=_DEDUP_WINDOW_MINUTES)
    if event_id in _event_id_window:
        # Check if the existing entry is still within the window
        if _event_id_window[event_id] >= cutoff:
            return True  # Still within window, is duplicate
        else:
            # Old entry expired, remove it and allow this event
            del _event_id_window[event_id]
    
    # Add to window
    _event_id_window[event_id] = timestamp
    return False


def _purge_old_event_ids(current_time: datetime) -> None:
    """Remove event_ids older than 10 minutes from deduplication window.
    
    Must be called with _lock held.
    
    Args:
        current_time: Current timestamp for age calculation
    """
    cutoff = current_time - timedelta(minutes=_DEDUP_WINDOW_MINUTES)
    to_remove = [eid for eid, ts in _event_id_window.items() if ts < cutoff]
    for eid in to_remove:
        del _event_id_window[eid]


def record_latency(operation: str, ms: float, event_id: str = "", timestamp: datetime | None = None) -> None:
    """Record single operation latency.
    
    Thread-safe, fire-and-forget (< 1ms). No blocking I/O.
    
    Args:
        operation: Operation type (e.g., "tool_call", "model_call")
        ms: Latency in milliseconds
        event_id: Optional unique event ID for deduplication (empty string = no dedup)
        timestamp: Optional timestamp (defaults to now)
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    with _lock:
        # Deduplicate if event_id provided
        if event_id and _is_duplicate_event(event_id, timestamp):
            return
        
        _purge_old_event_ids(timestamp)
        _latency_samples.append(LatencySample(operation, ms, timestamp, event_id))


def record_token_usage(model_name: str, prompt: int, completion: int, 
                       event_id: str = "", timestamp: datetime | None = None) -> None:
    """Record token consumption for a model.
    
    Thread-safe, fire-and-forget. No blocking I/O.
    
    Args:
        model_name: Model identifier (e.g., "gpt-4o")
        prompt: Number of prompt tokens
        completion: Number of completion tokens
        event_id: Optional unique event ID for deduplication
        timestamp: Optional timestamp (defaults to now)
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    with _lock:
        # Deduplicate if event_id provided
        if event_id and _is_duplicate_event(event_id, timestamp):
            return
        
        _purge_old_event_ids(timestamp)
        _token_samples.append(TokenUsageSample(model_name, prompt, completion, timestamp, event_id))


def record_error(operation: str, event_id: str = "", timestamp: datetime | None = None) -> None:
    """Record error occurrence.
    
    Thread-safe, fire-and-forget. No blocking I/O.
    
    Args:
        operation: Operation that failed
        event_id: Optional unique event ID for deduplication
        timestamp: Optional timestamp (defaults to now)
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    with _lock:
        # Deduplicate if event_id provided
        if event_id and _is_duplicate_event(event_id, timestamp):
            return
        
        _purge_old_event_ids(timestamp)
        _error_samples.append(ErrorSample(operation, timestamp, event_id))


def _calculate_percentiles(samples: list[float]) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Calculate p50, p95, p99 percentiles from latency samples.
    
    Args:
        samples: List of latency values in milliseconds
    
    Returns:
        Tuple of (p50, p95, p99) or (None, None, None) if no samples
    """
    if not samples:
        return (None, None, None)
    
    if len(samples) == 1:
        val = samples[0]
        return (val, val, val)
    
    # Use statistics.quantiles with method='exclusive' for NumPy compatibility
    try:
        quantiles = statistics.quantiles(samples, n=100, method='exclusive')
        p50 = quantiles[49]  # 50th percentile (index 49 in 0-99 range)
        p95 = quantiles[94]  # 95th percentile
        p99 = quantiles[98]  # 99th percentile
        return (p50, p95, p99)
    except statistics.StatisticsError:
        # Fallback for edge cases
        sorted_samples = sorted(samples)
        n = len(sorted_samples)
        p50 = sorted_samples[int(n * 0.5)]
        p95 = sorted_samples[int(n * 0.95)]
        p99 = sorted_samples[int(n * 0.99)]
        return (p50, p95, p99)


def _calculate_error_rate(window_start: datetime, window_end: datetime) -> float:
    """Calculate error rate within time window.
    
    Must be called with _lock held.
    
    Args:
        window_start: Start of time window
        window_end: End of time window
    
    Returns:
        Error rate as float between 0.0 and 1.0
    """
    error_count = sum(1 for e in _error_samples 
                     if window_start <= e.timestamp < window_end)
    
    total_ops = sum(1 for s in _latency_samples 
                   if window_start <= s.timestamp < window_end)
    total_ops += error_count
    
    if total_ops == 0:
        return 0.0
    
    return error_count / total_ops


def _aggregate_token_usage(window_start: datetime, window_end: datetime) -> dict[str, int]:
    """Aggregate token usage by model within time window.
    
    Must be called with _lock held.
    
    Args:
        window_start: Start of time window
        window_end: End of time window
    
    Returns:
        Dict mapping model_name to total tokens
    """
    from collections import defaultdict
    
    usage: dict[str, int] = defaultdict(int)
    for sample in _token_samples:
        if window_start <= sample.timestamp < window_end:
            total_tokens = sample.prompt_tokens + sample.completion_tokens
            usage[sample.model_name] += total_tokens
    
    return dict(usage)


def _calculate_cost_usd(token_usage: dict[str, int], pricing_table: dict) -> float:
    """Calculate total cost in USD based on token usage and pricing.
    
    Args:
        token_usage: Dict mapping model_name to total tokens
        pricing_table: Pricing table from _load_pricing_table()
    
    Returns:
        Total cost in USD
    """
    total_cost = 0.0
    
    for model_name, total_tokens in token_usage.items():
        if model_name not in pricing_table:
            emit("la.cross_cutting.metrics.emit",
                 {"message": f"Unknown model '{model_name}' not in pricing table, cost set to 0"})
            continue
        
        # Note: This is simplified - we're using total tokens with average pricing
        # In reality, we'd need separate prompt/completion token tracking in token_usage
        # For now, use the average of prompt and completion pricing
        pricing = pricing_table[model_name]
        avg_price_per_1k = (pricing["prompt"] + pricing["completion"]) / 2
        total_cost += (total_tokens / 1000.0) * avg_price_per_1k
    
    return total_cost


def snapshot(window_start: datetime, window_end: datetime) -> MetricsSnapshot:
    """Generate time-windowed metrics snapshot.
    
    Thread-safe. Returns frozen dataclass.
    
    Args:
        window_start: Start of measurement window (inclusive)
        window_end: End of measurement window (exclusive)
    
    Returns:
        Immutable MetricsSnapshot with aggregated metrics
    
    Raises:
        ValueError: If window_end < window_start
    
    Example:
        >>> from datetime import datetime, timezone, timedelta
        >>> start = datetime.now(timezone.utc)
        >>> end = start + timedelta(minutes=5)
        >>> snap = snapshot(start, end)
        >>> print(f"Collected {snap.sample_count} samples, p50={snap.p50_latency_ms}ms")
    """
    if window_end < window_start:
        raise ValueError(f"window_end ({window_end}) must be >= window_start ({window_start})")
    
    with _lock:
        # Filter samples by time window
        filtered_latencies = [s for s in _latency_samples 
                             if window_start <= s.timestamp < window_end]
        
        sample_count = len(filtered_latencies)
        
        # Calculate percentiles
        latency_values = [s.latency_ms for s in filtered_latencies]
        p50, p95, p99 = _calculate_percentiles(latency_values)
        
        # Calculate error rate
        error_rate = _calculate_error_rate(window_start, window_end)
        
        # Aggregate token usage
        token_usage = _aggregate_token_usage(window_start, window_end)
        
        # Calculate cost
        cost_usd = _calculate_cost_usd(token_usage, _pricing_table)
        
        # Emit log tag
        emit("la.cross_cutting.metrics.emit", {
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "sample_count": sample_count
        })
        
        return MetricsSnapshot(
            window_start=window_start,
            window_end=window_end,
            sample_count=sample_count,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            error_rate=error_rate,
            token_usage=token_usage,
            cost_usd=cost_usd
        )


def flush() -> None:
    """Clear all accumulated metrics and deduplication window.
    
    Called by F09 exit_cleanup. Thread-safe, idempotent.
    
    Clears:
    - All latency samples
    - All token usage samples
    - All error samples
    - Event ID deduplication window
    - Eval task start times
    """
    with _lock:
        _latency_samples.clear()
        _token_samples.clear()
        _error_samples.clear()
        _event_id_window.clear()
        _eval_task_start_times.clear()


# Event handlers
def _on_tool_call_event(event: dict) -> None:
    """Handle tool_call event from event bus."""
    try:
        event_id = event.get("event_id", "")
        if not event_id:
            emit("la.cross_cutting.metrics.emit",
                 {"message": "tool_call event missing event_id, skipping"})
            return
        
        if "latency_ms" not in event:
            emit("la.cross_cutting.metrics.emit",
                 {"message": f"tool_call event {event_id} missing latency_ms, skipping"})
            return
        
        operation = event.get("operation", "tool_call")
        latency_ms = event["latency_ms"]
        
        # Parse timestamp if provided
        timestamp = None
        if "timestamp" in event:
            timestamp = datetime.fromisoformat(event["timestamp"])
        
        record_latency(operation, latency_ms, event_id=event_id, timestamp=timestamp)
    except Exception as e:
        emit("la.cross_cutting.metrics.emit",
             {"message": f"Failed to process tool_call event: {e}"})


def _on_model_response_event(event: dict) -> None:
    """Handle model_response event from event bus."""
    try:
        event_id = event.get("event_id", "")
        if not event_id:
            emit("la.cross_cutting.metrics.emit",
                 {"message": "model_response event missing event_id, skipping"})
            return
        
        if "model_name" not in event or "prompt_tokens" not in event or "completion_tokens" not in event:
            emit("la.cross_cutting.metrics.emit",
                 {"message": f"model_response event {event_id} missing required fields, skipping"})
            return
        
        model_name = event["model_name"]
        prompt_tokens = event["prompt_tokens"]
        completion_tokens = event["completion_tokens"]
        
        # Parse timestamp if provided
        timestamp = None
        if "timestamp" in event:
            timestamp = datetime.fromisoformat(event["timestamp"])
        
        record_token_usage(model_name, prompt_tokens, completion_tokens, 
                          event_id=event_id, timestamp=timestamp)
    except Exception as e:
        emit("la.cross_cutting.metrics.emit",
             {"message": f"Failed to process model_response event: {e}"})


def _on_eval_task_event(event: dict) -> None:
    """Handle eval_task_started and eval_task_done events."""
    try:
        event_type = event.get("event_type", "")
        task_id = event.get("task_id", "")
        event_id = event.get("event_id", "")
        
        if not event_id:
            emit("la.cross_cutting.metrics.emit",
                 {"message": f"{event_type} event missing event_id, skipping"})
            return
        
        # Parse timestamp
        timestamp = None
        if "timestamp" in event:
            timestamp = datetime.fromisoformat(event["timestamp"])
        else:
            timestamp = datetime.now(timezone.utc)
        
        with _lock:
            if event_type == "eval_task_started":
                _eval_task_start_times[task_id] = timestamp
            elif event_type == "eval_task_done":
                if task_id in _eval_task_start_times:
                    start_time = _eval_task_start_times[task_id]
                    latency_ms = (timestamp - start_time).total_seconds() * 1000
                    del _eval_task_start_times[task_id]
                    
                    # Record outside of lock context
                    record_latency("eval_task", latency_ms, event_id=event_id, timestamp=timestamp)
    except Exception as e:
        emit("la.cross_cutting.metrics.emit",
             {"message": f"Failed to process eval_task event: {e}"})


def initialize(event_bus: EventBusProtocol, pricing_table_path: str | None = None) -> None:
    """Initialize metrics collector and subscribe to event bus.
    
    Args:
        event_bus: F03 event bus instance (implements EventBusProtocol)
        pricing_table_path: Optional path to pricing table JSON file
                           (defaults to env var or ~/.local/share/langagent/pricing.json)
    
    Example:
        >>> from langagent.protocol.event_bus import EventBus
        >>> event_bus = EventBus()
        >>> initialize(event_bus, pricing_table_path="/etc/langagent/pricing.json")
    """
    global _pricing_table
    
    # Load pricing table
    _pricing_table = _load_pricing_table(pricing_table_path)
    
    # Subscribe to event bus
    event_bus.subscribe("tool_call", _on_tool_call_event)
    event_bus.subscribe("model_response", _on_model_response_event)
    event_bus.subscribe("eval_task_started", lambda e: _on_eval_task_event({**e, "event_type": "eval_task_started"}))
    event_bus.subscribe("eval_task_done", lambda e: _on_eval_task_event({**e, "event_type": "eval_task_done"}))
