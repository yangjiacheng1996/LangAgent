"""Cross-cutting concerns module - Public API exports.

F02 Phase 1: Structured logging with tag validation, secret redaction, and EventBusProtocol.
"""
from langagent.cross_cutting.logger import (
    # Core functions
    emit,
    set_level,
    drain_spans,
    # Types
    EventBusProtocol,
    Span,
    LogLevel,
    # Exceptions
    UnknownLogTagError,
    SpanDrainError,
    # Constants
    ALLOWED_TAGS,
)

__all__ = [
    "emit",
    "set_level",
    "drain_spans",
    "EventBusProtocol",
    "Span",
    "LogLevel",
    "UnknownLogTagError",
    "SpanDrainError",
    "ALLOWED_TAGS",
]
