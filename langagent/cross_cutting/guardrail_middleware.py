"""
Guardrail middleware for tool permission controls and PII redaction.

Implements three-level guardrail modes (all/smart/strict), internal endpoint
detection, PII redaction, and prompt injection detection per Constitution
Article X (Security & Privacy).
"""

import fnmatch
import ipaddress
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from langagent.cross_cutting.audit_recorder import AuditRecorder
from langagent.cross_cutting.types import GuardrailPolicy, GuardrailDecision, AuditEntry


def is_internal(endpoint: str, patterns: list[str]) -> bool:
    """
    Check if endpoint matches internal endpoint patterns.
    
    Supports CIDR notation (e.g., "10.0.0.0/8") and glob patterns
    (e.g., "*.internal.example.com").
    
    Args:
        endpoint: URL or hostname to check
        patterns: List of CIDR or glob patterns
        
    Returns:
        True if endpoint matches any pattern, False otherwise
    """
    if not patterns:
        return False
    
    # Parse URL to extract hostname
    try:
        parsed = urlparse(endpoint)
        hostname = parsed.hostname or parsed.netloc or endpoint
    except Exception:
        hostname = endpoint
    
    for pattern in patterns:
        # Try CIDR matching
        if "/" in pattern:
            try:
                network = ipaddress.ip_network(pattern, strict=False)
                try:
                    ip = ipaddress.ip_address(hostname)
                    if ip in network:
                        return True
                except ValueError:
                    # Not an IP address, try resolving hostname (skip for now)
                    pass
            except ValueError:
                # Not a valid CIDR pattern
                pass
        
        # Try glob matching
        if fnmatch.fnmatch(hostname, pattern):
            return True
    
    return False


def evaluate(
    tool_name: str,
    requires_approval: bool,
    endpoint: str | None,
    policy: GuardrailPolicy,
) -> GuardrailDecision:
    """
    Evaluate whether tool call should be allowed based on guardrail policy.
    
    Args:
        tool_name: Name of the tool being called
        requires_approval: Whether tool requires human approval
        endpoint: Optional endpoint URL for internal/external classification
        policy: GuardrailPolicy configuration
        
    Returns:
        GuardrailDecision with allow/interrupt/redact flags + reason
    """
    # If guardrails are disabled, allow everything
    if not policy.enabled:
        return GuardrailDecision(
            allow=True,
            interrupt=False,
            redact=False,
            reason="guardrails disabled",
            is_internal_endpoint=None,
        )
    
    # Strict mode: deny all tools
    if policy.mode == "strict":
        return GuardrailDecision(
            allow=False,
            interrupt=True,
            redact=policy.redact_pii,
            reason="strict mode: deny all tools",
            is_internal_endpoint=None,
        )
    
    # All mode: require approval for all tools
    if policy.mode == "all":
        return GuardrailDecision(
            allow=False,
            interrupt=True,
            redact=policy.redact_pii,
            reason="all mode: require approval for all tools",
            is_internal_endpoint=None,
        )
    
    # Smart mode: respect requires_approval and internal endpoint checks
    if policy.mode == "smart":
        # Check internal endpoint classification if applicable
        is_internal_endpoint = None
        if endpoint:
            is_internal_endpoint = is_internal(endpoint, policy.internal_endpoint_patterns)
            
            # If allow_internal_endpoints is enabled and this is internal, allow
            if policy.allow_internal_endpoints and is_internal_endpoint:
                return GuardrailDecision(
                    allow=True,
                    interrupt=False,
                    redact=policy.redact_pii,
                    reason="internal endpoint allowed",
                    is_internal_endpoint=True,
                )
            
            # If endpoint is external (public), require approval
            if policy.allow_internal_endpoints and not is_internal_endpoint:
                return GuardrailDecision(
                    allow=False,
                    interrupt=True,
                    redact=policy.redact_pii,
                    reason="public endpoint requires approval",
                    is_internal_endpoint=False,
                )
        
        # Check requires_approval annotation
        if requires_approval:
            return GuardrailDecision(
                allow=False,
                interrupt=True,
                redact=policy.redact_pii,
                reason="tool requires approval",
                is_internal_endpoint=is_internal_endpoint,
            )
        
        # Default: allow
        return GuardrailDecision(
            allow=True,
            interrupt=False,
            redact=policy.redact_pii,
            reason="allowed",
            is_internal_endpoint=is_internal_endpoint,
        )
    
    # Fallback: allow (should not reach here)
    return GuardrailDecision(
        allow=True,
        interrupt=False,
        redact=policy.redact_pii,
        reason="fallback: allowed",
        is_internal_endpoint=None,
    )


class GuardrailMiddleware:
    """
    LangChain AgentMiddleware implementation for guardrails.
    
    Implements three hooks: before_tools, after_tools, wrap_model_call.
    """
    
    def __init__(self, policy: GuardrailPolicy, audit_recorder: AuditRecorder):
        """
        Initialize guardrail middleware with policy and audit recorder.
        
        Args:
            policy: GuardrailPolicy configuration
            audit_recorder: AuditRecorder instance for audit logging
        """
        self.policy = policy
        self.audit_recorder = audit_recorder
    
    def _redact_pii(self, text: str) -> str:
        """
        Apply PII redaction patterns to text.
        
        Redacts emails to ***@domain.com and phone numbers to ***.
        """
        # Redact emails
        text = re.sub(
            r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'***@\2',
            text
        )
        # Redact phone numbers
        text = re.sub(r'\+?\d[\d\s\-\(\)]{7,}\d', '***', text)
        return text
    
    def before_tools(self, state: dict[str, Any], tools: list[Any]) -> dict[str, Any]:
        """
        Hook called before tool execution.
        
        Evaluates guardrail policy and triggers interrupt if needed.
        Writes audit entries for blocked tools.
        
        Args:
            state: Current agent state
            tools: List of tool specs being called
            
        Returns:
            Modified state (with interrupt if blocked)
        """
        for tool in tools:
            tool_name = getattr(tool, "name", "unknown")
            requires_approval = getattr(tool, "requires_approval", False)
            endpoint = getattr(tool, "endpoint", None)
            
            decision = evaluate(
                tool_name=tool_name,
                requires_approval=requires_approval,
                endpoint=endpoint,
                policy=self.policy,
            )
            
            # Write audit entry if blocked
            if not decision.allow or decision.interrupt:
                audit_entry = AuditEntry(
                    entry_id=str(uuid.uuid4()),
                    audited_at=datetime.now(timezone.utc),
                    severity="info",
                    category="unauthorized_tool",
                    actor="system:guardrail_middleware",
                    action="tool_call_blocked",
                    target=tool_name,
                    outcome="blocked" if not decision.allow else "interrupted",
                    evidence={"reason": decision.reason, "mode": self.policy.mode},
                )
                self.audit_recorder.write(audit_entry)
            
            # Trigger interrupt if needed
            if decision.interrupt:
                state["interrupt"] = True
                state["interrupt_reason"] = decision.reason
        
        return state
    
    def after_tools(self, state: dict[str, Any], tools: list[Any]) -> dict[str, Any]:
        """
        Hook called after tool execution.
        
        Applies PII redaction to tool outputs if enabled.
        
        Args:
            state: Current agent state with tool outputs
            tools: List of tool specs that were called
            
        Returns:
            Modified state with redacted outputs
        """
        if not self.policy.redact_pii:
            return state
        
        # Redact PII in messages
        if "messages" in state:
            for message in state["messages"]:
                if isinstance(message, dict) and "content" in message:
                    message["content"] = self._redact_pii(message["content"])
        
        return state
    
    def wrap_model_call(self, state: dict[str, Any], model_call: Any) -> dict[str, Any]:
        """
        Hook called before model invocation.
        
        Detects prompt injection patterns and writes audit entries.
        In v1, we audit and mark but do NOT block execution.
        
        Args:
            state: Current agent state with messages
            model_call: Model call function
            
        Returns:
            State (potentially with untrusted marker)
        """
        # Prompt injection patterns
        injection_patterns = [
            r"忽略以上指令",
            r"ignore previous instructions",
            r"disregard all prior",
            r"你现在是",
            r"you are now",
        ]
        
        # Check messages for injection patterns
        if "messages" in state:
            for message in state["messages"]:
                if isinstance(message, dict) and "content" in message:
                    content = message.get("content", "")
                    for pattern in injection_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            # Write audit entry
                            audit_entry = AuditEntry(
                                entry_id=str(uuid.uuid4()),
                                audited_at=datetime.now(timezone.utc),
                                severity="warn",
                                category="prompt_injection",
                                actor="system:guardrail_middleware",
                                action="injection_detected",
                                target="user_message",
                                outcome="marked_untrusted",
                                evidence={"pattern": pattern, "content_preview": content[:100]},
                            )
                            self.audit_recorder.write(audit_entry)
                            
                            # Mark message as untrusted (but do NOT block)
                            message["untrusted"] = True
                            break
        
        return state


def build_middleware(
    policy: GuardrailPolicy,
    audit_dir: Path = Path.home() / ".local/share/langagent",
) -> GuardrailMiddleware:
    """
    Build guardrail middleware instance from policy.
    
    Args:
        policy: GuardrailPolicy configuration
        audit_dir: Directory for audit logs (default: ~/.local/share/langagent/)
        
    Returns:
        GuardrailMiddleware instance implementing AgentMiddleware protocol
    """
    audit_recorder = AuditRecorder(audit_dir=audit_dir)
    return GuardrailMiddleware(policy, audit_recorder)


__all__ = [
    "GuardrailMiddleware",
    "build_middleware",
    "evaluate",
    "is_internal",
]
