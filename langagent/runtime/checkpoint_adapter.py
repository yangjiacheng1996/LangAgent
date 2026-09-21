"""Checkpoint adapter (F05) - Stub implementation for F10 testing.

This module will be fully implemented in F05 (specs/005-checkpoint-adapter).
For now, it provides stub functions to enable F10 CLI testing.
"""
from typing import Any


def create(config: Any) -> Any:
    """Create a checkpoint instance from config.
    
    Args:
        config: Runtime configuration object
        
    Returns:
        Checkpoint instance (LangGraph BaseCheckpointSaver)
        
    Note:
        This is a stub implementation. Full implementation in F05.
    """
    # Stub: return a mock object that will be replaced in F05
    class StubCheckpoint:
        """Stub checkpoint for testing."""
        pass
    
    return StubCheckpoint()
