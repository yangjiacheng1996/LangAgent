"""Cross-cutting logger with structured logging, tag validation, and secret redaction.

F02 Phase 1: Foundation for LangAgent's observability system.
"""
from dataclasses import dataclass
from typing import Literal, Protocol, Callable, Any, runtime_checkable
import threading
from datetime import datetime, timezone
import json
import sys


# Type definitions
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


@dataclass(frozen=True)
class Span:
    """Span for distributed tracing."""
    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    start: float  # Unix timestamp
    end: float    # Unix timestamp
    attributes: dict[str, Any]


# Custom exceptions
class UnknownLogTagError(ValueError):
    """Raised when an unknown log tag is used."""
    pass


class SpanDrainError(RuntimeError):
    """Raised when span buffer drain fails."""
    pass


# EventBusProtocol - Interface for F03 event bus implementation
@runtime_checkable
class EventBusProtocol(Protocol):
    """Contract for event bus implementations (F03).
    
    This protocol defines the required interface for any event bus implementation.
    F03 may add optional methods (publish_async, drain_events) but these 4 are mandatory.
    
    The protocol uses structural subtyping, so any class with these methods automatically
    satisfies the protocol without explicit inheritance.
    """
    
    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Emit event to all subscribers of event_type.
        
        Args:
            event_type: Type identifier for the event (e.g., "agent.tool_called")
            payload: Event data as dictionary
        """
        ...
    
    def subscribe(
        self, 
        event_type: str, 
        callback: Callable[[dict[str, Any]], None]
    ) -> str:
        """Register callback for event_type.
        
        Args:
            event_type: Type identifier to listen for
            callback: Function to call when event is published
        
        Returns:
            subscription_id: Unique identifier for this subscription (use for unsubscribe)
        """
        ...
    
    def unsubscribe(self, subscription_id: str) -> None:
        """Remove subscription by id.
        
        Args:
            subscription_id: ID returned from subscribe()
        """
        ...
    
    def flush(self) -> None:
        """Block until all pending events delivered.
        
        This is synchronous to simplify F09 cleanup logic during exit_cleanup phase.
        """
        ...


# Constants: 46 allowed log tags organized by namespace
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
    "la.runtime.model_adapt.ok",
    "la.runtime.model_adapt.fail",
    "la.runtime.tool_bind.start",
    "la.runtime.tool_bind.register",
    "la.runtime.tool_bind.ok",
    "la.runtime.tool_bind.fail",
    "la.runtime.graph_build.start",
    "la.runtime.graph_build.ok",
    "la.runtime.graph_build.fail",
    "la.runtime.main_loop.turn.start",
    "la.runtime.main_loop.turn.end",
    "la.runtime.main_loop.model_call.start",
    "la.runtime.main_loop.model_call.end",
    "la.runtime.main_loop.tool_exec.start",
    "la.runtime.main_loop.tool_exec.end",
    "la.runtime.main_loop.interrupt",
    "la.runtime.exit_cleanup.start",
    "la.runtime.exit_cleanup.drain_spans",
    "la.runtime.exit_cleanup.flush_events",
    "la.runtime.exit_cleanup.ok",
    "la.runtime.exit_cleanup.fail",
    
    # la.cross_cutting.* (4 tags) - cross-cutting concerns
    "la.cross_cutting.guardrail.block",
    "la.cross_cutting.audit.write",
    "la.cross_cutting.metrics.emit",
    "la.cross_cutting.event_handler_error",
    
    # la.tool.* (1 tag) - tool warnings
    "la.tool.suspicious_missing_side_effects",
})


# Sensitive field names for automatic redaction
_REDACT_KEYS: frozenset[str] = frozenset({"api_key", "password", "secret", "token"})


# Log level mapping
_LEVEL_VALUES: dict[str, int] = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}


# Module-level state
_emit_lock = threading.Lock()
_buffer_lock = threading.Lock()
_current_level: int = 20  # Default INFO
_span_buffer: list[Span] = []


# Helper functions

def _generate_timestamp() -> str:
    """Generate ISO8601 timestamp with local timezone."""
    return datetime.now(timezone.utc).astimezone().isoformat()


def _infer_tag_level(tag: str) -> int:
    """Infer log level from tag name."""
    if ".fail" in tag or ".error" in tag:
        return 40  # ERROR
    elif ".block" in tag:
        return 30  # WARNING
    elif ".start" in tag or ".ok" in tag or ".end" in tag:
        return 20  # INFO
    else:
        return 20  # Default INFO


def _redact(payload: dict[str, Any]) -> dict[str, Any]:
    """Deep recursive redaction of sensitive fields.
    
    Returns a new dict with sensitive fields replaced by '***'.
    """
    out: dict[str, Any] = {}
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


# Public API

def emit(tag: str, payload: dict[str, Any]) -> None:
    """Emit a structured log with tag validation and dual-format output.
    
    Args:
        tag: Log tag (must be in ALLOWED_TAGS whitelist)
        payload: Dictionary payload (will be redacted for sensitive fields)
    
    Raises:
        UnknownLogTagError: If tag is not in ALLOWED_TAGS
        TypeError: If payload is not a dict
    """
    # Validate payload type
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")
    
    # Validate tag
    if tag not in ALLOWED_TAGS:
        raise UnknownLogTagError(f"Unknown log tag: {tag}")
    
    # Check log level filtering
    tag_level = _infer_tag_level(tag)
    if tag_level < _current_level:
        return  # Filtered out
    
    # Redact sensitive fields
    redacted_payload = _redact(payload)
    
    # Generate timestamp
    timestamp = _generate_timestamp()
    
    # Acquire lock for thread-safe output
    with _emit_lock:
        try:
            # Text format (human-readable)
            message = redacted_payload.get("message", "")
            text_line = f"[{tag}] {timestamp} {message}\n"
            sys.stderr.write(text_line)
            
            # JSONL format (machine-parseable)
            jsonl_data = {
                "tag": tag,
                "timestamp": timestamp,
                "level": _infer_tag_level(tag),
                "payload": redacted_payload,
            }
            jsonl_line = json.dumps(jsonl_data) + "\n"
            sys.stderr.write(jsonl_line)
            
            sys.stderr.flush()
            
            # Handle span buffering (for User Story 4)
            if payload.get("kind") == "span":
                _buffer_span(payload)
                
        except Exception:
            # Fire-and-forget: suppress I/O errors
            pass


def _buffer_span(payload: dict[str, Any]) -> None:
    """Buffer span data for later draining (User Story 4)."""
    try:
        span = Span(
            trace_id=payload.get("trace_id", ""),
            span_id=payload.get("span_id", ""),
            parent_span_id=payload.get("parent_span_id"),
            name=payload.get("name", ""),
            start=payload.get("start", 0.0),
            end=payload.get("end", 0.0),
            attributes=payload.get("attributes", {}),
        )
        with _buffer_lock:
            _span_buffer.append(span)
    except Exception:
        # Fire-and-forget: don't propagate span buffer errors
        pass


def set_level(level: LogLevel) -> None:
    """Set the minimum log level for filtering.
    
    Args:
        level: One of "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    
    Raises:
        ValueError: If level is not valid
    """
    global _current_level
    if level not in _LEVEL_VALUES:
        raise ValueError(f"Invalid level: {level}. Must be one of {list(_LEVEL_VALUES.keys())}")
    _current_level = _LEVEL_VALUES[level]


def drain_spans() -> list[Span]:
    """Drain accumulated span buffer and return spans.
    
    This is a failure-safe operation: the buffer is only cleared if no exception occurs.
    
    Returns:
        List of accumulated Span objects
    
    Raises:
        SpanDrainError: If drain operation fails
    """
    with _buffer_lock:
        if not _span_buffer:
            return []
        
        # Copy buffer before clearing (防止清空后才发现异常)
        spans = _span_buffer.copy()
        
        try:
            # Clear buffer only if no exception
            _span_buffer.clear()
            return spans
        except Exception as e:
            # Do NOT clear buffer - allow caller to retry
            raise SpanDrainError(f"Failed to drain spans: {e}") from e
