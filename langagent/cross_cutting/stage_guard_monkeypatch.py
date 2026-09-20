"""Monkeypatch management for stage guard enforcement.

This module provides utilities to temporarily intercept class methods
to enforce stage capability boundaries without modifying source code.
"""

from typing import Any, Callable
from langagent.cross_cutting.stage_guard import StageCapabilityViolationError


def patch_class_method(
    target_class: type,
    method_name: str,
    stage_name: str
) -> Callable:
    """Create a blocking patch for a class method.
    
    Args:
        target_class: The class to patch
        method_name: Name of the method to intercept
        stage_name: Name of the stage enforcing the restriction
        
    Returns:
        A function that raises StageCapabilityViolationError when called
    """
    def blocking_method(*args: Any, **kwargs: Any) -> None:
        raise StageCapabilityViolationError(
            stage_name=stage_name,
            target=target_class.__name__,
            operation=method_name
        )
    return blocking_method


def restore_class_method(
    target_class: type,
    method_name: str,
    original_method: Callable
) -> None:
    """Restore an original class method after patching.
    
    Args:
        target_class: The class that was patched
        method_name: Name of the method to restore
        original_method: The original method to restore
    """
    setattr(target_class, method_name, original_method)


class Monkeystack:
    """Stack-based monkeypatch manager for nested decorator safety.
    
    Maintains a stack of applied patches to ensure proper cleanup
    in nested contexts and exception scenarios.
    """
    
    def __init__(self):
        self._stack: list[tuple[type, str, Callable]] = []
    
    def push(self, target_class: type, method_name: str, stage_name: str) -> None:
        """Apply a monkeypatch and push it onto the stack.
        
        Args:
            target_class: The class to patch
            method_name: Name of the method to intercept
            stage_name: Name of the stage enforcing the restriction
        """
        # Save the original method
        original_method = getattr(target_class, method_name, None)
        if original_method is None:
            return
        
        # Apply the blocking patch
        blocking_method = patch_class_method(target_class, method_name, stage_name)
        setattr(target_class, method_name, blocking_method)
        
        # Push onto stack for later restoration
        self._stack.append((target_class, method_name, original_method))
    
    def pop(self) -> None:
        """Remove and restore the most recent monkeypatch."""
        if not self._stack:
            return
        
        target_class, method_name, original_method = self._stack.pop()
        restore_class_method(target_class, method_name, original_method)
    
    def is_empty(self) -> bool:
        """Check if the stack is empty."""
        return len(self._stack) == 0
