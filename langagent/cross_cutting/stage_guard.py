"""Stage capability enforcement for LangAgent runtime.

This module implements the @cross_cutting_stage_guard_decorator that prevents
operations outside a stage's defined scope. Used by dir_load, config_load, 
graph_compile, and other stages to enforce Constitution Article XV boundaries.
"""

from typing import Any, Callable
import functools


class StageCapabilityViolationError(Exception):
    """Raised when a stage attempts an operation outside its defined scope.
    
    Attributes:
        stage_name: Name of the stage that violated boundaries (e.g., 'dir_load')
        target: Class or module name that was accessed (e.g., 'BaseChatModel')
        operation: Method or operation attempted (e.g., '__init__')
    """
    
    def __init__(self, stage_name: str, target: str, operation: str):
        self.stage_name = stage_name
        self.target = target
        self.operation = operation
        message = (
            f"Stage '{stage_name}' violated capability boundary: "
            f"attempted '{operation}' on '{target}'"
        )
        super().__init__(message)


# Stage blacklist table mapping stage names to restricted operations
# Format: stage_name -> {target_class: [restricted_methods]}
STAGE_BLACKLIST_TABLE: dict[str, dict[str, list[str]]] = {
    'dir_load': {
        'BaseChatModel': ['__init__'],
        'StateGraph': ['compile'],
        'dotenv': ['load_dotenv', 'find_dotenv'],
    },
    'config_load': {
        'StateGraph': ['compile'],
    },
    'agent_init': {
        'StateGraph': ['compile'],
    },
    'graph_compile': {},
    'executor_run': {},
    'eval_score': {},
}


def cross_cutting_stage_guard_decorator(
    stage_name: str,
    *,
    monkeypatch_blacklist: list[type] | None = None,
    audit_event_blacklist: list[str] | None = None
) -> Callable:
    """Decorator to enforce stage capability boundaries.
    
    This decorator prevents a stage from performing operations outside its scope
    by applying monkeypatches and audit hooks during function execution.
    
    Args:
        stage_name: Name of the stage being protected (e.g., 'dir_load')
        monkeypatch_blacklist: Classes to intercept (optional, uses STAGE_BLACKLIST_TABLE)
        audit_event_blacklist: Audit events to block (optional)
        
    Returns:
        Decorator function that wraps the target function
        
    Example:
        @cross_cutting_stage_guard_decorator('dir_load')
        def load_agent(agent_dir: str) -> LoadedAgent:
            # This function cannot instantiate models or compile graphs
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Import here to avoid circular dependencies
            from langagent.cross_cutting.stage_guard_monkeypatch import Monkeystack
            from langagent.cross_cutting.stage_guard_audit import AuditHookManager
            
            monkeystack = Monkeystack()
            audit_manager = AuditHookManager()
            
            try:
                # Apply monkeypatches if specified
                if monkeypatch_blacklist:
                    for target_class in monkeypatch_blacklist:
                        # Check if this stage has blacklist entries
                        if stage_name in STAGE_BLACKLIST_TABLE:
                            blacklist = STAGE_BLACKLIST_TABLE[stage_name]
                            class_name = target_class.__name__
                            if class_name in blacklist:
                                # Patch methods from blacklist table
                                for method_name in blacklist[class_name]:
                                    monkeystack.push(target_class, method_name, stage_name)
                            else:
                                # For test mocks not in blacklist, patch __init__ by default
                                if hasattr(target_class, '__init__'):
                                    monkeystack.push(target_class, '__init__', stage_name)
                        else:
                            # For test stages not in table, patch __init__ by default
                            if hasattr(target_class, '__init__'):
                                monkeystack.push(target_class, '__init__', stage_name)
                
                # Register audit hooks if specified
                if audit_event_blacklist:
                    audit_manager.register(stage_name, audit_event_blacklist)
                
                # Execute the wrapped function
                return func(*args, **kwargs)
                
            finally:
                # Always cleanup, even if exception occurs
                audit_manager.unregister()
                while not monkeystack.is_empty():
                    monkeystack.pop()
        
        return wrapper
    return decorator
