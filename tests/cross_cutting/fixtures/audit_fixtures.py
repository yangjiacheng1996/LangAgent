"""
Test fixtures for audit recorder tests.

Provides factory functions for creating test AuditEntry instances and
mock data for unit testing.
"""

from datetime import datetime, timezone
from typing import Any, Dict
import uuid


def make_audit_entry(
    category: str = "unauthorized_tool",
    severity: str = "info",
    actor: str = "system:test",
    target: str = "test_tool",
    action: str = "tool_call_blocked",
    evidence: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Factory function for creating test audit entry dictionaries.
    
    Args:
        category: Audit category (unauthorized_tool, pii_detected, prompt_injection)
        severity: Severity level (info, warn, error)
        actor: System identifier (e.g., "system:guardrail_middleware")
        target: Target resource (e.g., tool name, endpoint)
        action: Action taken (e.g., tool_call_blocked, output_redacted)
        evidence: Additional evidence dictionary
        
    Returns:
        Dictionary with audit entry fields
    """
    return {
        "entry_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "category": category,
        "severity": severity,
        "actor": actor,
        "target": target,
        "action": action,
        "evidence": evidence or {},
        "redacted": False,
    }


__all__ = ["make_audit_entry"]
