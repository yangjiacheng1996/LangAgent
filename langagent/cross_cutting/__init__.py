"""Cross-cutting concerns: logging, tracing, audit, and guardrails.

This module provides foundational observability and security infrastructure for LangAgent.
All features (F01, F03-F11) depend on this module for structured logging.

Public API:
    - emit: Emit structured logs with tag validation
    - set_level: Configure log verbosity
    - drain_spans: Retrieve accumulated span logs
    - EventBusProtocol: Interface for event bus implementations (F03)
    - Span: Tracing span dataclass
    - LogLevel: Log level type
    - UnknownLogTagError: Exception for invalid log tags
    - SpanDrainError: Exception for span drain failures
    - AuditRecorder: Audit trail recorder (F04)
    - GuardrailMiddleware: Security guardrails (F04)
"""

from langagent.cross_cutting.logger import (
    emit,
    set_level,
    drain_spans,
    EventBusProtocol,
    Span,
    LogLevel,
    UnknownLogTagError,
    SpanDrainError,
    ALLOWED_TAGS,
)
from langagent.cross_cutting.audit_recorder import AuditRecorder, AuditFlushError
from langagent.cross_cutting.guardrail_middleware import (
    GuardrailMiddleware,
    build_middleware,
    evaluate,
    is_internal,
)
from langagent.cross_cutting.types import (
    AuditEntry,
    AuditCategory,
    AuditSeverity,
    GuardrailPolicy,
    GuardrailDecision,
    GuardrailMode,
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
    # F04 Audit & Guardrails
    "AuditRecorder",
    "AuditFlushError",
    "GuardrailMiddleware",
    "build_middleware",
    "evaluate",
    "is_internal",
    "AuditEntry",
    "AuditCategory",
    "AuditSeverity",
    "GuardrailPolicy",
    "GuardrailDecision",
    "GuardrailMode",
]
