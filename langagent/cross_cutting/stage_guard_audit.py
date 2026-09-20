"""Audit hook management for stage guard enforcement.

This module provides utilities to register CPython audit hooks
to block file system and import operations during stage execution.
"""

import sys
from typing import Any
from langagent.cross_cutting.stage_guard import StageCapabilityViolationError


class AuditHookManager:
    """Manager for CPython audit hooks to enforce stage boundaries.
    
    Registers hooks to intercept operations like file opens and imports,
    blocking those that violate stage capability constraints.
    """
    
    def __init__(self):
        self._hook_registered = False
        self._stage_name: str | None = None
        self._blacklist: list[str] = []
    
    def register(self, stage_name: str, event_blacklist: list[str]) -> None:
        """Register an audit hook with a blacklist of events.
        
        Args:
            stage_name: Name of the stage enforcing the restriction
            event_blacklist: List of audit event names to block
        """
        self._stage_name = stage_name
        self._blacklist = event_blacklist
        
        # Register the audit hook
        sys.addaudithook(self._audit_hook)
        self._hook_registered = True
    
    def _audit_hook(self, event: str, args: tuple[Any, ...]) -> None:
        """Internal audit hook callback.
        
        Args:
            event: The audit event name
            args: Arguments passed to the audit event
            
        Raises:
            StageCapabilityViolationError: If the event is blacklisted
        """
        # Check if this event is blacklisted
        if event in self._blacklist and self._stage_name:
            # Special handling for specific events
            if event == 'open':
                filename = args[0] if args else 'unknown'
                # Block .env file reads during dir_load
                if '.env' in str(filename):
                    raise StageCapabilityViolationError(
                        stage_name=self._stage_name,
                        target='open',
                        operation=f'open({filename})'
                    )
            elif event == 'import':
                module_name = args[0] if args else 'unknown'
                raise StageCapabilityViolationError(
                    stage_name=self._stage_name,
                    target='import',
                    operation=f'import {module_name}'
                )
    
    def unregister(self) -> None:
        """Unregister the audit hook.
        
        Note: CPython audit hooks cannot be truly unregistered,
        but we can disable the check by clearing the blacklist.
        """
        self._blacklist = []
        self._stage_name = None
        self._hook_registered = False
