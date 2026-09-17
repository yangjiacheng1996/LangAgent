"""
Primitives layer - LangChain/LangGraph interface encapsulation.

Public API exports for F01 Primitives Layer per FR-001 to FR-048.

This module re-exports all public functions and types needed by higher layers:
- chat_model_factory.create: Instantiate BaseChatModel from RuntimeConfig
- checkpoint_adapter.create/close: Create and cleanup checkpoint backends
- state_graph_builder.build: Compile StateGraph with middleware and tools
- langchain_types: Re-exported LangChain/LangGraph types
- state_reducers: Custom reducers for AgentState fields
- exceptions: All primitives layer exceptions
"""

# Chat model factory
from langagent.primitives.chat_model_factory import create as create_chat_model

# Checkpoint adapter
from langagent.primitives.checkpoint_adapter import create as create_checkpoint
from langagent.primitives.checkpoint_adapter import close as close_checkpoint

# State graph builder
from langagent.primitives.state_graph_builder import build as build_state_graph
from langagent.primitives.state_graph_builder import AgentState

# Re-export modules for sub-imports
from langagent.primitives import langchain_types
from langagent.primitives import state_reducers
from langagent.primitives import exceptions

# Re-export common types for convenience
from langagent.primitives.langchain_types import (
    BaseChatModel,
    BaseCheckpointSaver,
    CompiledStateGraph,
    HumanMessage,
    AIMessage,
    SystemMessage,
)

# Re-export reducers
from langagent.primitives.state_reducers import (
    replace_with_merge,
    merge_dict,
    overwrite_or_merge,
)

# Re-export exceptions
from langagent.primitives.exceptions import (
    ProviderUnsupportedError,
    AuthFailedError,
    EndpointUnreachableError,
    RequiredFieldMissingError,
    GraphCompileError,
    ToolBindingError,
    CheckpointTypeUnsupportedError,
    StageCapabilityViolationError,
)

__all__ = [
    # Factory functions
    "create_chat_model",
    "create_checkpoint",
    "close_checkpoint",
    "build_state_graph",
    # Types
    "AgentState",
    "BaseChatModel",
    "BaseCheckpointSaver",
    "CompiledStateGraph",
    "HumanMessage",
    "AIMessage",
    "SystemMessage",
    # Modules
    "langchain_types",
    "state_reducers",
    "exceptions",
    # Reducers
    "replace_with_merge",
    "merge_dict",
    "overwrite_or_merge",
    # Exceptions
    "ProviderUnsupportedError",
    "AuthFailedError",
    "EndpointUnreachableError",
    "RequiredFieldMissingError",
    "GraphCompileError",
    "ToolBindingError",
    "CheckpointTypeUnsupportedError",
    "StageCapabilityViolationError",
]
