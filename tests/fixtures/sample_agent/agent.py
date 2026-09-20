"""Sample agent for testing."""

from typing import TypedDict
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """Agent state with 5 required fields per Constitution Article VI."""
    messages: list[BaseMessage]
    todos: list[str]
    files: dict[str, str]
    context: dict[str, str]
    scratchpad: str


def create_graph():
    """Create the agent graph."""
    # Placeholder implementation
    pass
