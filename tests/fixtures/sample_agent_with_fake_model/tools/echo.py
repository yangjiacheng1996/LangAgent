"""Simple echo tool for F08 integration tests.

Constitutional Alignment:
    - Article VIII: Real BaseTool, not mocked
"""

from langagent.primitives.langchain_types import tool


@tool
def echo(text: str) -> str:
    """Echo the input text back.
    
    Args:
        text: Text to echo
    
    Returns:
        The same text
    """
    return text


__all__ = ["echo"]
