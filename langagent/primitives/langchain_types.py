"""
Re-export all LangChain/LangGraph types.

ARCHITECTURAL BOUNDARY ENFORCEMENT:
Only langagent.primitives may import langchain/langgraph directly.
Other layers (runtime/cross_cutting/protocol/cli) MUST import through this module.

See: 宪法第 II 条, architecture_modules.md dependency matrix, FR-033
"""

# Messages
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
)

# Message reducer (from langgraph)
from langgraph.graph.message import add_messages

# Models
from langchain_core.language_models import BaseChatModel

# Tools
from langchain_core.tools import BaseTool, tool

# Graph
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

# Checkpointing
from langgraph.checkpoint.base import BaseCheckpointSaver

__all__ = [
    # Messages
    "BaseMessage",
    "HumanMessage",
    "AIMessage",
    "SystemMessage",
    "ToolMessage",
    "add_messages",
    # Models
    "BaseChatModel",
    # Tools
    "BaseTool",
    "tool",
    # Graph
    "StateGraph",
    "START",
    "END",
    # Checkpointing
    "BaseCheckpointSaver",
]
