"""
Grader Registry (T052)

Maps grader names to grader functions for runtime selection.
"""

from typing import Any, Callable

# Import all grader implementations
from langagent.eval.graders import exact_match
from langagent.eval.graders import contains
from langagent.eval.graders import regex
from langagent.eval.graders import llm_judge
from langagent.eval.graders import tool_call_match

GraderFunction = Callable[..., bool]

# Populate registry with all 5 graders
GRADER_REGISTRY: dict[str, GraderFunction] = {
    "exact_match": exact_match.grade,
    "contains": contains.grade,
    "regex": regex.grade,
    "llm_judge": llm_judge.grade,
    "tool_call_match": tool_call_match.grade,
}


def get_grader(grader_name: str) -> GraderFunction:
    """Retrieve grader function by name."""
    if grader_name not in GRADER_REGISTRY:
        raise ValueError(f"Unknown grader: {grader_name}")
    return GRADER_REGISTRY[grader_name]


__all__ = ["GraderFunction", "GRADER_REGISTRY", "get_grader"]
