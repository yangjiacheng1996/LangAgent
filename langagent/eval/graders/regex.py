"""
Regex Grader (T042)

Regular expression pattern matching with optional case sensitivity.
"""

import re


class RegexCompileError(Exception):
    """Raised when regex pattern compilation fails."""
    pass


def grade(actual: str, expected: str | list[str], case_sensitive: bool = True, **kwargs) -> bool:
    """
    Grade using regex pattern matching.
    
    Args:
        actual: Agent's output
        expected: Regex pattern(s) to match
        case_sensitive: Whether to match case (default: True)
        
    Returns:
        True if pattern matches, False otherwise
        
    Raises:
        RegexCompileError: If pattern compilation fails
    """
    # Determine regex flags
    flags = 0 if case_sensitive else re.IGNORECASE
    
    # Handle list of expected patterns
    if isinstance(expected, list):
        for pattern in expected:
            try:
                compiled = re.compile(pattern, flags)
                if compiled.search(actual) is not None:
                    return True
            except re.error as e:
                raise RegexCompileError(f"Invalid regex pattern '{pattern}': {e}")
        return False
    
    # Single pattern
    try:
        compiled = re.compile(expected, flags)
        return compiled.search(actual) is not None
    except re.error as e:
        raise RegexCompileError(f"Invalid regex pattern '{expected}': {e}")


__all__ = ["grade", "RegexCompileError"]
