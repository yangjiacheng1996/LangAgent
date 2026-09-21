"""
Tests for regex grader (T038-T041a)

TDD: These tests must FAIL before implementation.
"""

import pytest

from langagent.eval.graders.regex import grade


def test_regex_pass():
    """T038: Valid regex pattern match returns True."""
    actual = "Call me at 123-456-7890"
    expected = r"\d{3}-\d{3}-\d{4}"
    
    result = grade(actual, expected)
    
    assert result is True


def test_regex_compile_error():
    """T039: Invalid regex pattern raises error."""
    actual = "test"
    expected = "["  # Invalid regex
    
    with pytest.raises(Exception) as exc_info:
        grade(actual, expected)
    
    assert "regex" in str(exc_info.value).lower() or "compile" in str(exc_info.value).lower()


def test_regex_case_insensitive():
    """T040: Case-insensitive regex with case_sensitive=False."""
    actual = "Hello World"
    expected = r"^hello"
    
    result = grade(actual, expected, case_sensitive=False)
    
    assert result is True


def test_regex_list_any_pattern_match():
    """T041: List of patterns - any match returns True."""
    actual = "The result: 42"
    expected = [r"\d+", r"result"]
    
    result = grade(actual, expected)
    
    assert result is True


def test_regex_case_sensitive_default_true():
    """T041a: Verify case_sensitive defaults to True."""
    actual = "Hello World"
    expected = r"^hello"
    
    # Default should be case-sensitive
    result = grade(actual, expected)
    
    assert result is False
