"""Cross-cutting logger module with structured logging and EventBusProtocol.

This module provides:
- Structured logging with tag whitelist validation (45 tags)
- Automatic secret redaction (api_key, password, secret, token)
- Thread-safe dual-format output (text + JSONL to stderr)
- Span buffering for tracing (F09 integration)
- EventBusProtocol interface definition (F03 contract)

Constitutional Alignment:
- Article II: Python stdlib only, no external dependencies
- Article VIII: TDD approach (tests written first)
- Article XIII: No print statements, structured logging only
"""

import json
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Literal, Protocol, runtime_checkable

# ============================================================================
# Phase 2: Foundational (T005-T009) - Core Types and Constants
# ============================================================================

# T005: Define Span dataclass with 7 fields (FR-019)
@dataclass(frozen=True)
class Span:
    """Represents a single trace span with timing information.
    
    Used for distributed tracing and performance analysis.
    Immutable to prevent accidental modification after creation.
    """
    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    start: float  # Unix timestamp (seconds since epoch)
    end: float    # Unix timestamp
    attributes: dict[str, Any]


# T006: Define LogLevel Literal type (FR-008)
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


# T007: Define ALLOWED_TAGS frozenset with 45 tags (FR-002, FR-018)
ALLOWED_TAGS: frozenset[str] = frozenset({
    # la.lifecycle.* (12 tags) - user-facing CLI lifecycle events
    "la.lifecycle.init.start",
    "la.lifecycle.init.end",
    "la.lifecycle.run.start",
    "la.lifecycle.run.turn",
    "la.lifecycle.run.tool_call",
    "la.lifecycle.run.tool_result",
    "la.lifecycle.run.model_response",
    "la.lifecycle.eval.start",
    "la.lifecycle.eval.case_done",
    "la.lifecycle.eval.summary",
    "la.lifecycle.doctor.check",
    "la.lifecycle.doctor.report",
    
    # la.runtime.* (29 tags) - internal stage events
    "la.runtime.dir_load.start",
    "la.runtime.dir_load.ok",
    "la.runtime.dir_load.fail",
    "la.runtime.config_resolve.start",
    "la.runtime.config_resolve.priority_merge",
    "la.runtime.config_resolve.ok",
    "la.runtime.config_resolve.fail",
    "la.runtime.model_adapt.start",
    "la.runtime.model_adapt.endpoint_probe",
    "la.runtime.model_adapt.ok",
    "la.runtime.model_adapt.fail",
    "la.runtime.graph_compose.start",
    "la.runtime.graph_compose.middleware_bind",
    "la.runtime.graph_compose.tool_bind",
    "la.runtime.graph_compose.ok",
    "la.runtime.graph_compose.fail",
    "la.runtime.main_loop.start",
    "la.runtime.main_loop.turn.start",
    "la.runtime.main_loop.turn.end",
    "la.runtime.main_loop.model_call",
    "la.runtime.main_loop.tool_call",
    "la.runtime.main_loop.tool_result",
    "la.runtime.main_loop.end",
    "la.runtime.exit_cleanup.start",
    "la.runtime.exit_cleanup.checkpointer_close",
    "la.runtime.exit_cleanup.report_write",
    "la.runtime.exit_cleanup.audit_flush",
    "la.runtime.exit_cleanup.ok",
    "la.runtime.exit_cleanup.fail",
    
    # la.cross_cutting.* (4 tags) - cross-cutting concerns
    "la.cross_cutting.guardrail.block",
    "la.cross_cutting.audit.write",
    "la.cross_cutting.metrics.emit",
    "la.cross_cutting.event_handler_error",
})


# T008: Define custom exceptions (FR-003, FR-011)
class UnknownLogTagError(ValueError):
    """Raised when emit() is called with an unregistered log tag.
    
    This enforces the tag whitelist contract and prevents typos.
    """
    pass


class SpanDrainError(RuntimeError):
    """Raised when drain_spans() fails (future I/O operations).
    
    In Phase 1, this is reserved for future use. Buffer is NOT cleared
    on error to allow caller retry.
    """
    pass


# T009: Create _REDACT_KEYS frozenset (FR-004)
_REDACT_KEYS: frozenset[str] = frozenset({"api_key", "password", "secret", "token"})


# ============================================================================
# Module-level state (T019 - implemented early for foundational setup)
# ============================================================================

_emit_lock = threading.Lock()
_current_level: int = 20  # Default INFO level

_LEVEL_VALUES: dict[str, int] = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}

# Span buffer (T039, T040 - implemented early)
_span_buffer: list[Span] = []
_buffer_lock = threading.Lock()


# ============================================================================
# Helper Functions (T017, T018 - implemented early for core logic)
# ============================================================================

def _generate_timestamp() -> str:
    """Generate ISO8601 timestamp with local timezone and UTC offset.
    
    Returns:
        Timestamp string like '2026-09-15T10:30:00.123456+08:00'
    
    Implementation follows FR-013 requirements.
    """
    return datetime.now(timezone.utc).astimezone().isoformat()


def _infer_tag_level(tag: str) -> int:
    """Infer numeric log level from tag suffix.
    
    Args:
        tag: Log tag string (e.g., 'la.runtime.dir_load.fail')
    
    Returns:
        Numeric level (10-50)
    
    Rules:
        - Tags ending in .fail / .error → ERROR (40)
        - Tags ending in .block → WARNING (30)
        - Tags ending in .start / .ok → INFO (20)
        - Default → INFO (20)
    """
    if tag.endswith((".fail", ".error")):
        return 40  # ERROR
    elif tag.endswith(".block"):
        return 30  # WARNING
    else:
        return 20  # INFO


def _redact(payload: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact sensitive fields in payload.
    
    Args:
        payload: Dictionary to redact
    
    Returns:
        New dictionary with sensitive values replaced by '***'
    
    Redacts exact field names: api_key, password, secret, token
    Does NOT redact substring matches (e.g., input_tokens is safe).
    Implements FR-004, FR-005, FR-006.
    """
    out = {}
    for k, v in payload.items():
        if k in _REDACT_KEYS:
            out[k] = "***"
        elif isinstance(v, dict):
            out[k] = _redact(v)
        elif isinstance(v, list):
            out[k] = [_redact(x) if isinstance(x, dict) else x for x in v]
        else:
            out[k] = v
    return out


# ============================================================================
# Public API (T020, T021, T043, T049-T053)
# ============================================================================

def emit(tag: str, payload: dict[str, Any]) -> None:
    """Emit a structured log entry with tag validation and redaction.
    
    Args:
        tag: Log tag from ALLOWED_TAGS (45 registered tags)
        payload: Dictionary payload (will be redacted and serialized)
    
    Raises:
        UnknownLogTagError: If tag not in ALLOWED_TAGS
        TypeError: If payload is not a dict
    
    Behavior:
        - Validates tag and payload type
        - Filters by log level
        - Redacts sensitive fields
        - Writes dual format (text + JSONL) to stderr atomically
        - Fire-and-forget: I/O errors logged, not raised
        - Thread-safe: uses _emit_lock
        - Span buffering: detects payload.kind=="span" and buffers
    
    Implements FR-001, FR-002, FR-003, FR-007, FR-009, FR-012, FR-014, 
    FR-017, FR-020.
    """
    # FR-002, FR-003: Validate tag
    if tag not in ALLOWED_TAGS:
        raise UnknownLogTagError(f"Unknown log tag: {tag}. Must be one of {len(ALLOWED_TAGS)} registered tags.")
    
    # FR-020: Validate payload type
    if not isinstance(payload, dict):
        raise TypeError(f"Payload must be dict, got {type(payload).__name__}")
    
    # FR-007: Check log level filtering
    tag_level = _infer_tag_level(tag)
    if tag_level < _current_level:
        return  # Filtered out
    
    # Acquire lock for thread-safe operation (FR-012)
    with _emit_lock:
        try:
            # Generate timestamp (FR-013)
            timestamp = _generate_timestamp()
            
            # Redact sensitive fields (FR-004, FR-006)
            redacted_payload = _redact(payload)
            
            # FR-009: Span buffering
            if redacted_payload.get("kind") == "span":
                _buffer_span(redacted_payload)
            
            # Prepare text and JSONL formats (FR-001)
            text_line = f"[{tag}] {timestamp} {redacted_payload.get('message', '')}\n"
            jsonl_obj = {
                "tag": tag,
                "timestamp": timestamp,
                "level": _level_name_from_value(tag_level),
                "payload": redacted_payload,
                "trace_id": redacted_payload.get("trace_id"),
            }
            jsonl_line = json.dumps(jsonl_obj) + "\n"
            
            # FR-001, FR-014: Write to stderr only
            sys.stderr.write(text_line)
            sys.stderr.write(jsonl_line)
            sys.stderr.flush()
            
        except (IOError, OSError) as e:
            # FR-017: Fire-and-forget - log failure but don't raise
            try:
                sys.stderr.write(f"[logger_emit_failed] {timestamp} {str(e)}\n")
            except:
                pass  # Best effort, don't raise


def set_level(level: LogLevel) -> None:
    """Set the minimum log level for filtering.
    
    Args:
        level: One of DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    Raises:
        ValueError: If level is not one of the 5 valid values
    
    Implements FR-008.
    """
    global _current_level
    if level not in _LEVEL_VALUES:
        raise ValueError(f"Invalid level: {level}. Must be one of {list(_LEVEL_VALUES.keys())}")
    _current_level = _LEVEL_VALUES[level]


def drain_spans() -> list[Span]:
    """Retrieve and clear accumulated span buffer.
    
    Returns:
        List of Span objects accumulated since last drain
    
    Behavior:
        - Thread-safe: uses _buffer_lock
        - Atomic: returns copy then clears buffer
        - Failure-safe: buffer NOT cleared if exception raised
        - Empty buffer returns empty list
    
    Implements FR-010, FR-011, FR-012.
    """
    with _buffer_lock:
        if not _span_buffer:
            return []
        
        # Copy buffer before clearing (FR-011: allows retry on failure)
        spans = _span_buffer.copy()
        
        # Clear buffer (pure memory operation, cannot fail in Phase 1)
        _span_buffer.clear()
        
        return spans


# ============================================================================
# EventBusProtocol (T049-T053) - Phase 7
# ============================================================================

@runtime_checkable
class EventBusProtocol(Protocol):
    """Protocol interface for event bus implementations (F03 contract).
    
    This protocol defines the contract that F03's EventBus must implement.
    F03 may add optional methods (publish_async, drain_events), but these
    4 methods are mandatory.
    
    Implements FR-015, FR-016.
    """
    
    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Emit event to all subscribers of event_type.
        
        Args:
            event_type: Event type identifier (e.g., 'model_response')
            payload: Event data dictionary
        """
        ...
    
    def subscribe(
        self, 
        event_type: str, 
        callback: Callable[[dict[str, Any]], None]
    ) -> str:
        """Register callback for event_type.
        
        Args:
            event_type: Event type to subscribe to
            callback: Function to call when event occurs
        
        Returns:
            subscription_id: Unique identifier for this subscription
        """
        ...
    
    def unsubscribe(self, subscription_id: str) -> None:
        """Remove subscription by ID.
        
        Args:
            subscription_id: ID returned from subscribe()
        """
        ...
    
    def flush(self) -> None:
        """Block until all pending events are delivered.
        
        Used during shutdown to ensure no events are lost.
        """
        ...


# ============================================================================
# Private Helper Functions
# ============================================================================

def _level_name_from_value(value: int) -> str:
    """Convert numeric level back to name for JSONL output."""
    for name, val in _LEVEL_VALUES.items():
        if val == value:
            return name
    return "INFO"  # Fallback


def _buffer_span(payload: dict[str, Any]) -> None:
    """Buffer a span from payload (called under _emit_lock).
    
    Args:
        payload: Redacted payload with kind=="span"
    
    Implements FR-009.
    """
    try:
        span = Span(
            trace_id=payload.get("trace_id", ""),
            span_id=payload.get("span_id", ""),
            parent_span_id=payload.get("parent_span_id"),
            name=payload.get("name", ""),
            start=float(payload.get("start", 0.0)),
            end=float(payload.get("end", 0.0)),
            attributes=payload.get("attributes", {}),
        )
        with _buffer_lock:
            _span_buffer.append(span)
    except (KeyError, TypeError, ValueError):
        # Malformed span, skip buffering
        pass
