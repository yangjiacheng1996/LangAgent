"""State graph builder (F01) - Stub implementation for F10 testing.

This module will be fully implemented in F01 (specs/001-state-graph-builder).
For now, it provides stub functions to enable F10 CLI testing.
"""
from typing import Any


def build(loaded_agent: Any, config: Any) -> Any:
    """Build a LangGraph StateGraph from loaded agent and config.
    
    Args:
        loaded_agent: LoadedAgent instance from dir_loader
        config: Runtime configuration object
        
    Returns:
        Compiled StateGraph instance
        
    Note:
        This is a stub implementation. Full implementation in F01.
    """
    # Stub: return a mock object that will be replaced in F01
    class StubStateGraph:
        """Stub state graph for testing."""
        pass
    
    return StubStateGraph()
