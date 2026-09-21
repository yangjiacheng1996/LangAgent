"""
Contains Grader (T037)

Substring containment check with optional case sensitivity.
"""


def grade(actual: str, expected: str | list[str], case_sensitive: bool = True, **kwargs) -> bool:
    """
    Grade using substring containment check.
    
    Args:
        actual: Agent's output
        expected: Substring(s) that must appear in actual
        case_sensitive: Whether to match case (default: True)
        
    Returns:
        True if expected substring found in actual, False otherwise
    """
    # Apply case normalization if needed
    if not case_sensitive:
        actual_normalized = actual.lower()
    else:
        actual_normalized = actual
    
    # Handle list of expected values
    if isinstance(expected, list):
        for exp in expected:
            exp_normalized = exp.lower() if not case_sensitive else exp
            if exp_normalized in actual_normalized:
                return True
        return False
    
    # Single expected value
    expected_normalized = expected.lower() if not case_sensitive else expected
    return expected_normalized in actual_normalized


__all__ = ["grade"]
