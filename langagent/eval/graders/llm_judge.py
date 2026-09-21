"""
LLM Judge Grader (T051)

Use independent LLM to judge semantic equivalence.
"""

from typing import Any


class LlmJudgeInvalidResponseError(Exception):
    """Raised when judge model returns non-YES/NO response."""
    pass


def grade(actual: str, expected: str | list[str], judge_model: Any, **kwargs) -> bool:
    """
    Grade using LLM judge for semantic equivalence.
    
    Args:
        actual: Agent's output
        expected: Reference answer(s)
        judge_model: Independent BaseChatModel instance
        
    Returns:
        True if judge says YES (semantically equivalent), False if NO
        
    Raises:
        LlmJudgeInvalidResponseError: If judge returns non-YES/NO response
    """
    # Construct judge prompt
    if isinstance(expected, list):
        expected_str = " OR ".join(expected)
    else:
        expected_str = expected
    
    prompt = f"""You are an evaluation judge. Compare the actual output to the expected output.
Answer with ONLY "YES" if semantically equivalent, or "NO" if not.

Expected: {expected_str}
Actual: {actual}"""
    
    # Call judge model
    # Assuming judge_model has invoke() method that accepts list of messages
    from langchain_core.messages import HumanMessage
    
    response = judge_model.invoke([HumanMessage(content=prompt)])
    
    # Extract response text
    response_text = response.content.strip().upper()
    
    # Parse response
    if response_text.startswith("YES"):
        return True
    elif response_text.startswith("NO"):
        return False
    else:
        raise LlmJudgeInvalidResponseError(
            f"Invalid judge response: expected YES or NO, got '{response.content}'"
        )


__all__ = ["grade", "LlmJudgeInvalidResponseError"]
