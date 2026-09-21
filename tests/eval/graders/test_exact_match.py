"""
Tests for exact_match grader (T028-T031a)

TDD: These tests must FAIL before implementation.
"""

import pytest
from pydantic import ValidationError

# Import will fail until implementation exists - expected for TDD
from langagent.eval.graders.exact_match import grade


def test_exact_match_pass():
    """T028: Exact match returns True for identical strings."""
    actual = "Hello, World!"
    expected = "Hello, World!"
    
    result = grade(actual, expected)
    
    assert result is True


def test_exact_match_fail_with_whitespace():
    """T029: Whitespace is stripped before comparison."""
    actual = "  Hello  "
    expected = "Hello"
    
    result = grade(actual, expected)
    
    assert result is True


def test_exact_match_fail():
    """T030: Different strings return False."""
    actual = "Hello"
    expected = "Goodbye"
    
    result = grade(actual, expected)
    
    assert result is False


def test_exact_match_list_any_match():
    """T031: List of expected values - any match returns True."""
    actual = "Hello"
    expected = ["Hi", "Hello", "Hey"]
    
    result = grade(actual, expected)
    
    assert result is True


def test_exact_match_rejects_case_sensitive():
    """T031a: exact_match should reject case_sensitive parameter."""
    actual = "Hello"
    expected = "hello"
    
    # exact_match is always case-sensitive, so this should fail
    result = grade(actual, expected)
    assert result is False
    
    # If case_sensitive kwarg is provided, it should be ignored or raise error
    # For now, we'll just ensure case matters
    result_upper = grade("HELLO", "hello")
    assert result_upper is False
