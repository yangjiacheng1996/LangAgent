"""
Tool Call Match Grader (T046)

Verify agent invoked specific tool with correct arguments.
"""

from typing import Any


def grade(actual_ai_message: Any, expected: dict[str, Any], strict_args: bool = False, **kwargs) -> bool:
    """
    Grade using tool call verification.
    
    Args:
        actual_ai_message: AIMessage with tool_calls attribute
        expected: Dict with 'tool_id' and 'args' keys
        strict_args: If True, require exact args match (default: False for subset match)
        
    Returns:
        True if tool was called with matching args, False otherwise
    """
    # Validate expected format
    if not isinstance(expected, dict):
        raise ValueError("tool_call_match grader requires expected as dict")
    
    if "tool_id" not in expected or "args" not in expected:
        raise ValueError("expected dict must contain 'tool_id' and 'args' keys")
    
    expected_tool_id = expected["tool_id"]
    expected_args = expected["args"]
    
    # Check if actual_ai_message has tool_calls
    if not hasattr(actual_ai_message, "tool_calls"):
        return False
    
    # Iterate over tool calls
    for call in actual_ai_message.tool_calls:
        # Check tool name/id match
        if call.get("name") != expected_tool_id:
            continue
        
        # Check args
        actual_args = call.get("args", {})
        
        if strict_args:
            # Exact match required
            if actual_args == expected_args:
                return True
        else:
            # Subset match: all expected args must be present with correct values
            if all(actual_args.get(k) == v for k, v in expected_args.items()):
                return True
    
    return False


__all__ = ["grade"]
