"""
Tests for llm_judge grader (T047-T050)

TDD: These tests must FAIL before implementation.
"""

import pytest
from unittest.mock import Mock

from langagent.eval.graders.llm_judge import grade


def test_llm_judge_pass():
    """T047: LLM judge returns YES for semantic match."""
    actual = "Buenos días"
    expected = "Hello"
    
    # Mock judge model
    judge_model = Mock()
    mock_response = Mock()
    mock_response.content = "YES"
    judge_model.invoke.return_value = mock_response
    
    result = grade(actual, expected, judge_model=judge_model)
    
    assert result is True
    assert judge_model.invoke.called


def test_llm_judge_fail():
    """T048: LLM judge returns NO for semantic mismatch."""
    actual = "Goodbye"
    expected = "Hello"
    
    # Mock judge model
    judge_model = Mock()
    mock_response = Mock()
    mock_response.content = "NO"
    judge_model.invoke.return_value = mock_response
    
    result = grade(actual, expected, judge_model=judge_model)
    
    assert result is False


def test_llm_judge_invalid_response():
    """T049: LLM judge with invalid response raises error."""
    actual = "test"
    expected = "test"
    
    # Mock judge model with invalid response
    judge_model = Mock()
    mock_response = Mock()
    mock_response.content = "MAYBE"
    judge_model.invoke.return_value = mock_response
    
    with pytest.raises(Exception) as exc_info:
        grade(actual, expected, judge_model=judge_model)
    
    assert "invalid" in str(exc_info.value).lower() or "response" in str(exc_info.value).lower()


def test_llm_judge_list_expected():
    """T050: LLM judge with list of expected values."""
    actual = "Hola"
    expected = ["Hello", "Hi", "Greetings"]
    
    # Mock judge model
    judge_model = Mock()
    mock_response = Mock()
    mock_response.content = "YES"
    judge_model.invoke.return_value = mock_response
    
    result = grade(actual, expected, judge_model=judge_model)
    
    assert result is True
