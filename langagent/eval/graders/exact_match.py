"""
Exact Match Grader (T032)

Exact string equality after whitespace normalization.
"""


def grade(actual: str, expected: str | list[str], **kwargs) -> bool:
    """
    Grade using exact string match after whitespace stripping.
    
    Args:
        actual: Agent's output
        expected: Expected string or list of acceptable strings
        
    Returns:
        True if exact match (after strip), False otherwise
        
    Note:
        exact_match is always case-sensitive and does not accept case_sensitive parameter.
    """
    # Strip whitespace from actual
    actual_stripped = actual.strip()
    
    # Handle list of expected values
    if isinstance(expected, list):
        return any(actual_stripped == exp.strip() for exp in expected)
    
    # Single expected value
    return actual_stripped == expected.strip()


__all__ = ["grade"]
