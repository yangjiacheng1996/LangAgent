"""Tests for AgentState TypedDict and reducer behavior.

This module tests:
1. AgentState instantiation with partial fields (total=False)
2. ErrorEntry structure validation
3. State reducer correctness across multiple dispatch() calls

Constitutional Alignment:
    - Article VIII: TDD rigidity (tests written before implementation)
    - Phase 2 Foundational + Phase 7 User Story 5
"""

import pytest
from typing import Any

from langagent.runtime.agent_state import AgentState, ErrorEntry
from langagent.primitives.langchain_types import HumanMessage, AIMessage, ToolMessage


# ============================================================================
# Phase 2: Foundational Tests (T013, T014)
# ============================================================================


def test_agent_state_instantiation():
    """T013: AgentState can be created with partial fields (total=False)."""
    # Empty state (all fields optional)
    state: AgentState = {}
    assert state == {}
    
    # Partial state (only messages)
    state_partial: AgentState = {
        "messages": [HumanMessage(content="Hello")]
    }
    assert "messages" in state_partial
    assert len(state_partial["messages"]) == 1
    
    # Full state (all 5 fields)
    state_full: AgentState = {
        "messages": [HumanMessage(content="Hello")],
        "todos": [{"id": "1", "status": "pending"}],
        "files": {"main.py": {"content": "print('hello')"}},
        "context": {"user_id": "alice"},
        "scratchpad": {"step": 1},
    }
    assert len(state_full) == 5


def test_error_entry_structure():
    """T014: ErrorEntry matches clarification Q4 format (4 fields)."""
    error: ErrorEntry = {
        "turn": 3,
        "tool": "echo",
        "error": "TimeoutError: Operation timed out after 5s",
        "timestamp": "2026-09-20T10:30:45.123456Z",
    }
    
    # Verify all required fields present
    assert error["turn"] == 3
    assert error["tool"] == "echo"
    assert "TimeoutError" in error["error"]
    assert error["timestamp"].endswith("Z")  # ISO8601 UTC


# ============================================================================
# Phase 7: User Story 5 - Reducer Tests (T019-T023, T081-T087)
# ============================================================================


def test_state_messages_add_messages_reducer():
    """T019: Messages append without overwrite (add_messages reducer)."""
    # This test will be expanded once we have graph integration
    # For now, verify basic message list behavior
    state: AgentState = {
        "messages": [HumanMessage(content="First")]
    }
    
    # Simulate append (reducer will do this in real graph)
    state["messages"].append(AIMessage(content="Response"))
    
    assert len(state["messages"]) == 2
    assert isinstance(state["messages"][0], HumanMessage)
    assert isinstance(state["messages"][1], AIMessage)


def test_state_todos_replace_with_merge():
    """T020: Todos use replace_with_merge (complete replacement)."""
    from langagent.primitives.state_reducers import replace_with_merge
    
    current = [{"id": "1", "status": "done"}]
    update = [{"id": "2", "status": "pending"}, {"id": "3", "status": "pending"}]
    
    result = replace_with_merge(current, update)
    
    # Update completely replaces current
    assert len(result) == 2
    assert result[0]["id"] == "2"
    assert result[1]["id"] == "3"


def test_state_files_merge_dict():
    """T021: Files use merge_dict (key-level merge)."""
    from langagent.primitives.state_reducers import merge_dict
    
    current = {
        "main.py": {"content": "old", "version": 1},
        "util.py": {"content": "keep", "version": 1},
    }
    update = {
        "main.py": {"content": "new", "version": 2},
    }
    
    result = merge_dict(current, update)
    
    # main.py updated, util.py preserved
    assert result["main.py"]["content"] == "new"
    assert result["main.py"]["version"] == 2
    assert result["util.py"]["content"] == "keep"


def test_state_context_overwrite_or_merge():
    """T022: Context uses overwrite_or_merge (mode-based)."""
    from langagent.primitives.state_reducers import overwrite_or_merge
    
    current = {"user_id": "alice", "session": "s1"}
    update = {"user_id": "bob"}
    
    # Mode: merge_with_prior (default)
    result_merge = overwrite_or_merge(current, update, mode="merge_with_prior")
    assert result_merge["user_id"] == "bob"  # Updated
    assert result_merge["session"] == "s1"   # Preserved
    
    # Mode: overwrite
    result_overwrite = overwrite_or_merge(current, update, mode="overwrite")
    assert result_overwrite["user_id"] == "bob"
    assert "session" not in result_overwrite  # Discarded


def test_state_scratchpad_replace_with_merge():
    """T023: Scratchpad uses replace_with_merge (dict replacement)."""
    from langagent.primitives.state_reducers import replace_with_merge
    
    current = [{"step": 1}]
    update = [{"step": 2, "reasoning": "next phase"}]
    
    result = replace_with_merge(current, update)
    
    # Complete replacement
    assert len(result) == 1
    assert result[0]["step"] == 2
    assert "reasoning" in result[0]


# ============================================================================
# Phase 7: User Story 5 - Multi-Turn Reducer Tests (T081-T087)
# ============================================================================


@pytest.mark.skip(reason="Integration test - requires real LangGraph (Phase 13)")
def test_state_messages_across_10_turns():
    """T081: 10× dispatch(), verify messages length = initial + turns."""
    # TODO: Implement in Phase 13 with real graph
    pass


@pytest.mark.skip(reason="Integration test - requires real LangGraph (Phase 13)")
def test_state_todos_across_10_updates():
    """T082: 10× updates with replace_with_merge, verify latest."""
    # TODO: Implement in Phase 13 with real graph
    pass


@pytest.mark.skip(reason="Integration test - requires real LangGraph (Phase 13)")
def test_state_files_across_10_updates():
    """T083: 10× updates, verify merge_dict key-level merge."""
    # TODO: Implement in Phase 13 with real graph
    pass


@pytest.mark.skip(reason="Integration test - requires real LangGraph (Phase 13)")
def test_state_context_overwrite_vs_merge():
    """T084: Alternate overwrite/merge modes, verify behavior."""
    # TODO: Implement in Phase 13 with real graph
    pass


@pytest.mark.skip(reason="Integration test - requires real LangGraph (Phase 13)")
def test_state_scratchpad_across_10_updates():
    """T085: 10× updates with replace_with_merge, verify replacement."""
    # TODO: Implement in Phase 13 with real graph
    pass


@pytest.mark.skip(reason="Helper function - not a test")
def build_graph_with_state_updates():
    """T087: Helper to construct graph that updates all 5 fields."""
    # TODO: Implement in Phase 13
    pass
