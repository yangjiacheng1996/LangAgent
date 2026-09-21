"""
Tests for contains grader (T033-T036a)

TDD: These tests must FAIL before implementation.
"""

import pytest

from langagent.eval.graders.contains import grade


def test_contains_pass_substring():
    """T033: Substring present returns True."""
    actual = "The answer is 42"
    expected = "42"
    
    result = grade(actual, expected)
    
    assert result is True


def test_contains_case_sensitive():
    """T034: Case-sensitive match by default."""
    actual = "Hello World"
    expected = "hello"
    
    result = grade(actual, expected)
    
    assert result is False


def test_contains_case_insensitive():
    """T035: Case-insensitive match with case_sensitive=False."""
    actual = "Hello World"
    expected = "hello"
    
    result = grade(actual, expected, case_sensitive=False)
    
    assert result is True


def test_contains_list_any_match():
    """T036: List of substrings - any match returns True."""
    actual = "def factorial(n):"
    expected = ["def ", "return"]
    
    result = grade(actual, expected)
    
    assert result is True


def test_contains_case_sensitive_default_true():
    """T036a: Verify case_sensitive defaults to True."""
    actual = "Hello World"
    expected = "HELLO"
    
    # Default behavior should be case-sensitive
    result = grade(actual, expected)
    
    assert result is False
