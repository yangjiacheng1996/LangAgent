"""Chat model factory (F02) - Stub implementation for F10 testing.

This module will be fully implemented in F02 (specs/002-chat-model-factory).
For now, it provides stub functions to enable F10 CLI testing.
"""
from typing import Any


def create(config: Any) -> Any:
    """Create a chat model instance from config.
    
    Args:
        config: Runtime configuration object
        
    Returns:
        Chat model instance (LangChain BaseChatModel)
        
    Note:
        This is a stub implementation. Full implementation in F02.
    """
    # Stub: return a mock object that will be replaced in F02
    class StubChatModel:
        """Stub chat model for testing."""
        pass
    
    return StubChatModel()
