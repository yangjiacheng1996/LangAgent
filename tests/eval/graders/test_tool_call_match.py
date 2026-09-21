"""
Tests for tool_call_match grader (T043-T045)

TDD: These tests must FAIL before implementation.
"""

import pytest

from langagent.eval.graders.tool_call_match import grade


class MockAIMessage:
    """Mock AIMessage for testing."""
    def __init__(self, tool_calls):
        self.tool_calls = tool_calls


def test_tool_call_match_pass_by_id():
    """T043: Tool call with matching ID and args returns True."""
    expected = {"tool_id": "web_search", "args": {"query": "LangChain"}}
    
    ai_message = MockAIMessage(
        tool_calls=[
            {"name": "web_search", "args": {"query": "LangChain", "limit": 10}, "id": "call_123"}
        ]
    )
    
    result = grade(ai_message, expected)
    
    assert result is True


def test_tool_call_match_fail_by_args_mismatch():
    """T044: Tool call with missing required arg returns False."""
    expected = {"tool_id": "web_search", "args": {"query": "Python"}}
    
    ai_message = MockAIMessage(
        tool_calls=[
            {"name": "web_search", "args": {"limit": 5}, "id": "call_123"}
        ]
    )
    
    result = grade(ai_message, expected)
    
    assert result is False


def test_tool_call_match_fail_by_id_missing():
    """T045: Wrong tool ID returns False."""
    expected = {"tool_id": "calculator", "args": {"expression": "2+2"}}
    
    ai_message = MockAIMessage(
        tool_calls=[
            {"name": "web_search", "args": {"query": "test"}, "id": "call_123"}
        ]
    )
    
    result = grade(ai_message, expected)
    
    assert result is False
