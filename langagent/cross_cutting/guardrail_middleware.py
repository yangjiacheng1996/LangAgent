"""
Guardrail middleware stub for testing.

This module defines the Protocol interface for guardrail middleware per Assumption 6.
F06 creates this stub, F04 Phase 1 will fill actual implementation.
"""

from typing import Protocol, Any


class GuardrailPolicy(Protocol):
    """Protocol for guardrail policy configuration."""
    pass


class GuardrailMiddleware:
    """Mock guardrail middleware instance for testing."""
    
    def __init__(self, policy: Any):
        """
        Initialize guardrail middleware with policy.
        
        Args:
            policy: Guardrail policy configuration
        """
        self.policy = policy
    
    def __call__(self, state: Any, runtime: Any) -> Any:
        """
        Execute guardrail middleware.
        
        Args:
            state: Current agent state
            runtime: LangGraph runtime context
            
        Returns:
            Modified state or original state
        """
        # Stub implementation - returns state unchanged
        return state


def build_middleware(policy: Any) -> GuardrailMiddleware:
    """
    Build guardrail middleware instance from policy.
    
    This is the Protocol interface per Assumption 6. F04 Phase 1 will provide
    actual implementation of policy validation and guardrail logic.
    
    Args:
        policy: Guardrail policy configuration (type TBD by F04)
        
    Returns:
        GuardrailMiddleware instance
    """
    return GuardrailMiddleware(policy)


__all__ = [
    "GuardrailPolicy",
    "GuardrailMiddleware",
    "build_middleware",
]
