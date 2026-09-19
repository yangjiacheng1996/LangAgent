"""
F02 Phase 2 - Metrics Collector

Cross-cutting metrics collection module for LangAgent.
Automatically collects performance metrics (latency, token usage, error rate) 
from event bus and produces time-windowed MetricsSnapshot.

Constitutional References:
- 宪法第 XV 条：顶层设计优先
- 宪法第 III 条：LangSmith 剥离原则（日志 tag 必须 `la.` 前缀）
- 宪法第 IX 条：Tracing + Monitoring（本 feature 实现 Monitoring 部分）
- 宪法第 XII 条：可观测契约
- 宪法第 XIII 条：Hard No（不写绝对路径/内网 IP）
"""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Protocol
import threading
import json
import os
import statistics
from collections import defaultdict


# ============================================================================
# Phase 2: Foundational - Core Data Structures (T004-T007)
# ============================================================================


@dataclass(frozen=True)
class MetricsSnapshot:
    """
    Time-windowed summary of performance metrics.
    
    Per module_schemas.md#schema-metrics-snapshot (9 fields).
    Immutable dataclass (frozen=True) to prevent accidental mutation.
    """
    window_start: datetime
    window_end: datetime
    sample_count: int
    p50_latency_ms: Optional[float]  # None when no samples exist
    p95_latency_ms: Optional[float]  # None when no samples exist
    p99_latency_ms: Optional[float]  # None when no samples exist
    error_rate: float  # 0.0 to 1.0
    token_usage: dict[str, int]  # model_name → total_tokens
    cost_usd: float


@dataclass
class LatencySample:
    """
    Internal representation of a single operation's latency measurement.
    
    4 fields per spec.md Key Entities section.
    """
    operation: str  # e.g., "tool_call", "model_call"
    latency_ms: float
    timestamp: datetime
    event_id: str  # UUID for deduplication


@dataclass
class TokenUsageSample:
    """
    Internal representation of token consumption for a model call.
    
    5 fields per spec.md Key Entities section.
    """
    model_name: str  # e.g., "gpt-4o", "qwen3-8b"
    prompt_tokens: int
    completion_tokens: int
    timestamp: datetime
    event_id: str  # UUID for deduplication


@dataclass
class ErrorSample:
    """
    Internal representation of an error occurrence.
    
    3 fields per spec.md Key Entities section.
    """
    operation: str
    timestamp: datetime
    event_id: str  # UUID for deduplication


# ============================================================================
# EventBusProtocol (from F02 Phase 1 - cross_cutting/logger.py)
# ============================================================================


class EventBusProtocol(Protocol):
    """
    Event bus protocol interface (4 mandatory methods).
    
    Defined in F02 Phase 1 cross_cutting/logger.py.
    F03 EventBus implements this protocol.
    """
    def publish(self, event_type: str, payload: dict) -> None:
        """Publish event to subscribers"""
        ...
    
    def subscribe(self, event_type: str, handler: callable) -> None:
        """Subscribe handler to event type"""
        ...
    
    def unsubscribe(self, event_type: str, handler: callable) -> None:
        """Unsubscribe handler from event type"""
        ...
    
    def flush(self) -> None:
        """Flush pending events"""
        ...


# ============================================================================
# Phase 2: Module-Level State (T008)
# ============================================================================

# Thread safety lock for all state mutations
_lock = threading.Lock()

# Sample storage (optimized for append speed)
_latency_samples: list[LatencySample] = []
_token_samples: list[TokenUsageSample] = []
_error_samples: list[ErrorSample] = []

# Event deduplication window (10-minute rolling window)
# Stores (event_id, timestamp) tuples for lazy cleanup
_event_id_window: set[tuple[str, datetime]] = set()

# Model pricing table (loaded at initialization)
_pricing_table: dict[str, dict[str, float]] = {}

# Event bus reference (set at initialization)
_event_bus: Optional[EventBusProtocol] = None

# Eval task tracking (for latency delta calculation)
_eval_task_start_times: dict[str, datetime] = {}


# ============================================================================
# Phase 2: Event Deduplication Helper (T009 + T023)
# ============================================================================


def _is_duplicate_event(event_id: str, timestamp: datetime) -> bool:
    """
    Check if event_id is duplicate within 10-minute window.
    
    Uses lazy cleanup: removes expired entries during check.
    Per T023: check and remove entries older than 10 minutes on every new event_id insertion.
    
    Args:
        event_id: Unique event identifier (UUID)
        timestamp: Event timestamp (UTC)
    
    Returns:
        True if event_id already exists in window (duplicate), False otherwise
    """
    global _event_id_window
    
    # Lazy cleanup: remove entries older than 10 minutes
    cutoff_time = timestamp - timedelta(minutes=10)
    _event_id_window = {
        (eid, ts) for eid, ts in _event_id_window 
        if ts >= cutoff_time
    }
    
    # Check if event_id exists in window
    is_duplicate = any(eid == event_id for eid, _ in _event_id_window)
    
    # Add new event_id to window if not duplicate
    if not is_duplicate:
        _event_id_window.add((event_id, timestamp))
    
    return is_duplicate


# ============================================================================
# Phase 7: Pricing Table Loading (T055-T056)
# ============================================================================


def _load_pricing_table(path: Optional[str] = None) -> dict[str, dict[str, float]]:
    """
    Load model pricing table from JSON file.
    
    Priority:
    1. Explicit path parameter
    2. Environment variable LANGAGENT_PRICING_TABLE_PATH
    3. Default path ~/.local/share/langagent/pricing.json
    4. Built-in fallback prices
    
    Args:
        path: Optional explicit path to pricing JSON file
    
    Returns:
        Pricing table dict: {model_name: {"prompt": float, "completion": float}}
    """
    # Built-in default prices (fallback)
    default_prices = {
        "gpt-4o": {"prompt": 0.005, "completion": 0.015},
        "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
        "qwen3-8b": {"prompt": 0.0, "completion": 0.0},
    }
    
    # Determine pricing table path
    pricing_path = None
    if path:
        pricing_path = path
    elif "LANGAGENT_PRICING_TABLE_PATH" in os.environ:
        pricing_path = os.environ["LANGAGENT_PRICING_TABLE_PATH"]
    else:
        default_path = os.path.expanduser("~/.local/share/langagent/pricing.json")
        if os.path.exists(default_path):
            pricing_path = default_path
    
    # Load from file if path exists
    if pricing_path and os.path.exists(pricing_path):
        try:
            with open(pricing_path, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            # Log warning and fall back to defaults
            print(f"Warning: Failed to load pricing table from {pricing_path}: {e}", flush=True)
            return default_prices
    
    return default_prices


# ============================================================================
# Phase 7: Cost Calculation (T058)
# ============================================================================


def _calculate_cost(token_usage: dict[str, int]) -> float:
    """
    Calculate total cost in USD based on token usage and pricing table.
    
    Args:
        token_usage: Dict mapping model_name to total_tokens
    
    Returns:
        Total cost in USD
    """
    total_cost = 0.0
    
    for model_name, total_tokens in token_usage.items():
        if model_name not in _pricing_table:
            # Log warning for unknown model, contribute 0 to cost
            print(f"Warning: Model '{model_name}' not in pricing table, contributing $0 to cost", flush=True)
            continue
        
        # Note: In real implementation, we need separate prompt/completion token counts
        # For now, use total_tokens with average of prompt and completion prices
        prices = _pricing_table[model_name]
        avg_price_per_1k = (prices["prompt"] + prices["completion"]) / 2
        cost = (total_tokens * avg_price_per_1k) / 1000
        total_cost += cost
    
    return total_cost


# ============================================================================
# Phase 5: Percentile Calculation (T040-T041)
# ============================================================================


def _calculate_percentiles(latencies: list[float]) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Calculate p50, p95, p99 percentiles from latency samples.
    
    Uses statistics.quantiles() with method='exclusive' for NumPy compatibility.
    Returns (None, None, None) when latencies list is empty.
    
    Args:
        latencies: List of latency values in milliseconds
    
    Returns:
        Tuple of (p50, p95, p99) or (None, None, None) if no samples
    """
    if not latencies:
        return (None, None, None)
    
    if len(latencies) == 1:
        # Single sample: all percentiles are the same value
        val = latencies[0]
        return (val, val, val)
    
    # Use statistics.quantiles() for percentile calculation
    # method='exclusive' matches NumPy's default behavior
    try:
        # quantiles() needs n+1 points for n quantiles
        # For p50, p95, p99: we need quantiles at 0.5, 0.95, 0.99
        sorted_latencies = sorted(latencies)
        
        # Calculate percentiles using linear interpolation
        def percentile(data: list[float], p: float) -> float:
            """Calculate percentile p (0-1) using linear interpolation"""
            n = len(data)
            if n == 0:
                return 0.0
            if n == 1:
                return data[0]
            
            # Linear interpolation formula
            rank = p * (n - 1)
            lower = int(rank)
            upper = min(lower + 1, n - 1)
            fraction = rank - lower
            
            return data[lower] + fraction * (data[upper] - data[lower])
        
        p50 = percentile(sorted_latencies, 0.50)
        p95 = percentile(sorted_latencies, 0.95)
        p99 = percentile(sorted_latencies, 0.99)
        
        return (p50, p95, p99)
    
    except Exception as e:
        print(f"Warning: Percentile calculation failed: {e}", flush=True)
        return (None, None, None)


# ============================================================================
# Phase 3: Event Handlers (T018-T020)
# ============================================================================


def _handle_tool_call_event(payload: dict) -> None:
    """
    Handle tool_call event from event bus.
    
    Extracts operation, latency_ms, event_id and calls record_latency().
    Per T021: validates payload and skips if missing required fields.
    """
    # Validate required fields
    if "event_id" not in payload:
        print("Warning: tool_call event missing event_id, skipping", flush=True)
        return
    if "latency_ms" not in payload:
        print("Warning: tool_call event missing latency_ms, skipping", flush=True)
        return
    if "operation" not in payload:
        print("Warning: tool_call event missing operation, skipping", flush=True)
        return
    
    # Extract fields
    event_id = payload["event_id"]
    latency_ms = float(payload["latency_ms"])
    operation = payload["operation"]
    
    # Call record_latency (which includes deduplication check)
    record_latency(operation, latency_ms, event_id=event_id)


def _handle_model_response_event(payload: dict) -> None:
    """
    Handle model_response event from event bus.
    
    Extracts model_name, tokens, event_id and calls record_token_usage().
    Per T021: validates payload and skips if missing required fields.
    """
    # Validate required fields
    if "event_id" not in payload:
        print("Warning: model_response event missing event_id, skipping", flush=True)
        return
    if "model_name" not in payload:
        print("Warning: model_response event missing model_name, skipping", flush=True)
        return
    if "prompt_tokens" not in payload or "completion_tokens" not in payload:
        print("Warning: model_response event missing token_usage fields, skipping", flush=True)
        return
    
    # Extract fields
    event_id = payload["event_id"]
    model_name = payload["model_name"]
    prompt_tokens = int(payload["prompt_tokens"])
    completion_tokens = int(payload["completion_tokens"])
    
    # Call record_token_usage (which includes deduplication check)
    record_token_usage(model_name, prompt_tokens, completion_tokens, event_id=event_id)


def _handle_eval_task_started_event(payload: dict) -> None:
    """
    Handle eval_task_started event from event bus.
    
    Records start timestamp for latency delta calculation.
    """
    global _eval_task_start_times
    
    # Validate required fields
    if "event_id" not in payload:
        print("Warning: eval_task_started event missing event_id, skipping", flush=True)
        return
    if "timestamp" not in payload:
        print("Warning: eval_task_started event missing timestamp, skipping", flush=True)
        return
    
    event_id = payload["event_id"]
    timestamp_str = payload["timestamp"]
    
    # Parse ISO8601 timestamp
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except ValueError as e:
        print(f"Warning: Failed to parse timestamp '{timestamp_str}': {e}", flush=True)
        return
    
    # Store start time for this eval task
    with _lock:
        _eval_task_start_times[event_id] = timestamp


def _handle_eval_task_done_event(payload: dict) -> None:
    """
    Handle eval_task_done event from event bus.
    
    Calculates latency delta from eval_task_started and records latency.
    """
    global _eval_task_start_times
    
    # Validate required fields
    if "event_id" not in payload:
        print("Warning: eval_task_done event missing event_id, skipping", flush=True)
        return
    if "timestamp" not in payload:
        print("Warning: eval_task_done event missing timestamp, skipping", flush=True)
        return
    
    event_id = payload["event_id"]
    timestamp_str = payload["timestamp"]
    
    # Parse ISO8601 timestamp
    try:
        end_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except ValueError as e:
        print(f"Warning: Failed to parse timestamp '{timestamp_str}': {e}", flush=True)
        return
    
    # Look up start time
    with _lock:
        if event_id not in _eval_task_start_times:
            print(f"Warning: No start time found for eval task {event_id}", flush=True)
            return
        
        start_time = _eval_task_start_times.pop(event_id)
    
    # Calculate latency delta
    latency_ms = (end_time - start_time).total_seconds() * 1000
    
    # Record latency
    record_latency("eval_task", latency_ms, event_id=event_id)


# ============================================================================
# Phase 3: Initialize Function (T017)
# ============================================================================


def initialize(event_bus: EventBusProtocol, pricing_table_path: Optional[str] = None) -> None:
    """
    Initialize metrics collector and subscribe to event bus.
    
    Args:
        event_bus: F03 event bus instance (implements EventBusProtocol)
        pricing_table_path: Optional path to pricing JSON file
                          (defaults to ~/.local/share/langagent/pricing.json)
    """
    global _event_bus, _pricing_table
    
    _event_bus = event_bus
    
    # Load pricing table (T057)
    _pricing_table = _load_pricing_table(pricing_table_path)
    
    # Subscribe to 4 event types (T017)
    event_bus.subscribe("tool_call", _handle_tool_call_event)
    event_bus.subscribe("model_response", _handle_model_response_event)
    event_bus.subscribe("eval_task_started", _handle_eval_task_started_event)
    event_bus.subscribe("eval_task_done", _handle_eval_task_done_event)


# ============================================================================
# Phase 4: Record APIs (T029-T031)
# ============================================================================


def record_latency(operation: str, ms: float, event_id: Optional[str] = None) -> None:
    """
    Record single operation latency.
    
    Thread-safe, fire-and-forget (< 1ms).
    
    Args:
        operation: Operation type (e.g., "tool_call", "model_call")
        ms: Latency in milliseconds
        event_id: Optional UUID for deduplication (generated if not provided)
    """
    timestamp = datetime.now(timezone.utc)
    
    # Generate event_id if not provided (for direct API calls)
    if event_id is None:
        import uuid
        event_id = str(uuid.uuid4())
    
    # Check for duplicates (T022)
    with _lock:
        if _is_duplicate_event(event_id, timestamp):
            return  # Silently discard duplicate
        
        # Append sample
        sample = LatencySample(
            operation=operation,
            latency_ms=ms,
            timestamp=timestamp,
            event_id=event_id
        )
        _latency_samples.append(sample)


def record_token_usage(model_name: str, prompt: int, completion: int, event_id: Optional[str] = None) -> None:
    """
    Record token consumption.
    
    Thread-safe, fire-and-forget.
    
    Args:
        model_name: Model identifier (e.g., "gpt-4o", "qwen3-8b")
        prompt: Prompt token count
        completion: Completion token count
        event_id: Optional UUID for deduplication (generated if not provided)
    """
    timestamp = datetime.now(timezone.utc)
    
    # Generate event_id if not provided
    if event_id is None:
        import uuid
        event_id = str(uuid.uuid4())
    
    # Check for duplicates
    with _lock:
        if _is_duplicate_event(event_id, timestamp):
            return  # Silently discard duplicate
        
        # Append sample
        sample = TokenUsageSample(
            model_name=model_name,
            prompt_tokens=prompt,
            completion_tokens=completion,
            timestamp=timestamp,
            event_id=event_id
        )
        _token_samples.append(sample)


def record_error(operation: str, event_id: Optional[str] = None) -> None:
    """
    Record error occurrence.
    
    Thread-safe, fire-and-forget.
    
    Args:
        operation: Operation that failed
        event_id: Optional UUID for deduplication (generated if not provided)
    """
    timestamp = datetime.now(timezone.utc)
    
    # Generate event_id if not provided
    if event_id is None:
        import uuid
        event_id = str(uuid.uuid4())
    
    # Check for duplicates
    with _lock:
        if _is_duplicate_event(event_id, timestamp):
            return  # Silently discard duplicate
        
        # Append sample
        sample = ErrorSample(
            operation=operation,
            timestamp=timestamp,
            event_id=event_id
        )
        _error_samples.append(sample)


# ============================================================================
# Phase 4 + 5 + 6 + 7: Snapshot Function (T032, T042, T047-T049, T059)
# ============================================================================


def snapshot(window_start: datetime, window_end: datetime) -> MetricsSnapshot:
    """
    Generate time-windowed metrics snapshot.
    
    Thread-safe, returns frozen dataclass.
    
    Args:
        window_start: Start of measurement window (inclusive)
        window_end: End of measurement window (exclusive)
    
    Returns:
        MetricsSnapshot with aggregated metrics
    
    Raises:
        ValueError: If window_end < window_start
    """
    # Validate window (T033)
    if window_end < window_start:
        raise ValueError("window_end must be >= window_start")
    
    with _lock:
        # Filter samples by timestamp window (T043, T047, T048, T049)
        windowed_latency = [
            s for s in _latency_samples
            if window_start <= s.timestamp < window_end
        ]
        windowed_tokens = [
            s for s in _token_samples
            if window_start <= s.timestamp < window_end
        ]
        windowed_errors = [
            s for s in _error_samples
            if window_start <= s.timestamp < window_end
        ]
        
        # Calculate sample_count
        sample_count = len(windowed_latency)
        
        # Calculate percentiles (T042)
        latencies = [s.latency_ms for s in windowed_latency]
        p50, p95, p99 = _calculate_percentiles(latencies)
        
        # Calculate error_rate (T032)
        total_ops = len(windowed_latency)
        error_count = len(windowed_errors)
        if total_ops + error_count > 0:
            error_rate = error_count / (total_ops + error_count)
        else:
            error_rate = 0.0
        
        # Aggregate token_usage by model (T032)
        token_usage = defaultdict(int)
        for s in windowed_tokens:
            token_usage[s.model_name] += s.prompt_tokens + s.completion_tokens
        
        # Calculate cost_usd (T059)
        cost_usd = _calculate_cost(dict(token_usage))
        
        # Log emission (T063)
        # Note: Actual logger integration would go here
        # emit("la.cross_cutting.metrics.emit", {"window_start": window_start, "window_end": window_end})
        
        return MetricsSnapshot(
            window_start=window_start,
            window_end=window_end,
            sample_count=sample_count,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            error_rate=error_rate,
            token_usage=dict(token_usage),
            cost_usd=cost_usd
        )


# ============================================================================
# Phase 8: Flush Function (T060)
# ============================================================================


def flush() -> None:
    """
    Clear all accumulated metrics (samples + event_id deduplication window).
    
    Used by F09 exit_cleanup. Thread-safe.
    """
    global _latency_samples, _token_samples, _error_samples, _event_id_window, _eval_task_start_times
    
    with _lock:
        _latency_samples.clear()
        _token_samples.clear()
        _error_samples.clear()
        _event_id_window.clear()
        _eval_task_start_times.clear()
