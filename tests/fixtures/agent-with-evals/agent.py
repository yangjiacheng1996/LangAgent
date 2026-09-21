"""
Minimal functional test agent for eval subsystem testing.
"""

from typing import TypedDict
from langgraph.graph import StateGraph, END


class AgentState(TypedDict):
    """Minimal agent state."""
    messages: list[dict]
    final_output: str


def process_node(state: AgentState) -> AgentState:
    """Simple processing node."""
    messages = state.get("messages", [])
    if messages:
        last_message = messages[-1].get("content", "")
        # Echo the input as output
        return {"messages": messages, "final_output": last_message}
    return {"messages": [], "final_output": ""}


def create_graph():
    """Create minimal test graph."""
    workflow = StateGraph(AgentState)
    workflow.add_node("process", process_node)
    workflow.set_entry_point("process")
    workflow.add_edge("process", END)
    return workflow.compile()


if __name__ == "__main__":
    graph = create_graph()
    result = graph.invoke({"messages": [{"role": "user", "content": "Hello"}]})
    print(result)
