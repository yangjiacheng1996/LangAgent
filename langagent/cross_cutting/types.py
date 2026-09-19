"""
Shared type definitions for cross-cutting audit and guardrail system.

This module defines the core Pydantic schemas used by audit_recorder and
guardrail_middleware modules per Constitution Article X (Security & Privacy).
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Type aliases for guardrail modes
GuardrailMode = Literal["all", "smart", "strict"]
AuditCategory = Literal["unauthorized_tool", "pii_detected", "prompt_injection"]
AuditSeverity = Literal["debug", "info", "warn", "error"]


class AuditEntry(BaseModel):
    """
    Audit entry for security events.
    
    Immutable record of security-relevant actions (tool blocks, PII detection,
    prompt injection attempts) per Constitution Article X (Security & Privacy).
    """
    
    entry_id: str = Field(
        ...,
        description="UUID4 identifier for this audit entry",
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    )
    audited_at: datetime = Field(
        ...,
        description="Timestamp when event occurred (UTC timezone required)",
    )
    severity: AuditSeverity = Field(
        ...,
        description="Severity level: debug, info, warn, error",
    )
    category: AuditCategory = Field(
        ...,
        description="Event category: unauthorized_tool, pii_detected, prompt_injection",
    )
    actor: str = Field(
        ...,
        description="System-level identifier (format: system:<component>)",
        pattern=r"^system:[a-z_]+$",
    )
    action: str = Field(
        ...,
        description="Human-readable action description (e.g., 'tool_blocked', 'pii_redacted')",
    )
    target: str = Field(
        ...,
        description="Resource identifier (e.g., tool name, endpoint URL)",
    )
    outcome: str = Field(
        ...,
        description="Result of action (e.g., 'blocked', 'allowed', 'redacted')",
    )
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Contextual data (JSON-serializable, redacted before persistence)",
    )
    
    @field_validator("audited_at")
    @classmethod
    def validate_utc_timezone(cls, v: datetime) -> datetime:
        """Ensure timestamp is in UTC timezone."""
        if v.tzinfo is None:
            raise ValueError("audited_at must have timezone info (UTC required)")
        return v
    
    model_config = ConfigDict(frozen=True)  # Immutable after creation


class GuardrailPolicy(BaseModel):
    """
    Guardrail policy configuration.
    
    Defines security controls for tool execution, PII handling, and endpoint
    classification per Constitution Article X (Security & Privacy).
    """
    
    enabled: bool = Field(
        default=True,
        description="Whether guardrails are active (disabled = allow all)",
    )
    mode: GuardrailMode = Field(
        default="smart",
        description="Guardrail mode: all (interrupt all), smart (requires_approval only), strict (block all)",
    )
    redact_pii: bool = Field(
        default=True,
        description="Whether to redact PII patterns in tool outputs",
    )
    allow_internal_endpoints: bool = Field(
        default=False,
        description="Whether to allow internal endpoints without approval",
    )
    internal_endpoint_patterns: list[str] = Field(
        default_factory=list,
        description="CIDR or glob patterns for internal endpoints (e.g., '10.0.0.0/8', '*.internal.example.com')",
    )
    
    model_config = ConfigDict(frozen=True)  # Immutable during agent execution


class GuardrailDecision(BaseModel):
    """
    Guardrail evaluation decision.
    
    Ephemeral object returned by evaluate() method to indicate whether tool
    execution should proceed, trigger interrupt, or apply redaction.
    """
    
    allow: bool = Field(
        ...,
        description="Whether tool execution is permitted",
    )
    interrupt: bool = Field(
        ...,
        description="Whether to trigger LangGraph interrupt for human-in-the-loop",
    )
    redact: bool = Field(
        ...,
        description="Whether to apply PII redaction to tool outputs",
    )
    reason: str = Field(
        ...,
        description="Human-readable explanation for audit trail",
    )
    is_internal_endpoint: bool | None = Field(
        default=None,
        description="Endpoint classification result (None if not applicable)",
    )
    
    model_config = ConfigDict(frozen=True)  # Immutable after creation


__all__ = [
    "AuditEntry",
    "GuardrailPolicy",
    "GuardrailDecision",
    "GuardrailMode",
    "AuditCategory",
    "AuditSeverity",
]
