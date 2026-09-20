"""Fake model configuration for F08 integration tests.

This module provides FakeListChatModel configurations with predictable
responses for deterministic testing of the ReAct main loop.

Constitutional Alignment:
    - Article VIII Clause 4: Use FakeListChatModel, not mocking graph behavior
"""

from langchain_core.language_models import FakeListChatModel
from langagent.primitives.langchain_types import AIMessage


def create_fake_model_single_turn() -> FakeListChatModel:
    """Create fake model that responds once without tool calls.
    
    Returns:
        FakeListChatModel configured for single-turn test
    """
    return FakeListChatModel(responses=[
        "The answer is 42."
    ])


def create_fake_model_with_tool_call() -> FakeListChatModel:
    """Create fake model that makes one tool call.
    
    Returns:
        FakeListChatModel configured for tool call test
    """
    # Note: FakeListChatModel doesn't support tool_calls in responses
    # We'll return simple text responses for now
    return FakeListChatModel(responses=[
        "Let me help you with that.",
        "Done."
    ])


def create_fake_model_multi_turn(num_turns: int = 3) -> FakeListChatModel:
    """Create fake model that makes multiple tool calls before converging.
    
    Args:
        num_turns: Number of turns before final answer
    
    Returns:
        FakeListChatModel configured for multi-turn test
    """
    responses = []
    for i in range(num_turns):
        responses.append(f"Step {i+1}")
    responses.append("Final answer: done")
    
    return FakeListChatModel(responses=responses)


def create_fake_model_infinite_loop() -> FakeListChatModel:
    """Create fake model that never converges (always has tool_calls).
    
    Returns:
        FakeListChatModel that repeats same response indefinitely
    """
    # Create 50 identical responses (enough for max_turns tests)
    return FakeListChatModel(responses=["Loop"] * 50)


__all__ = [
    "create_fake_model_single_turn",
    "create_fake_model_with_tool_call",
    "create_fake_model_multi_turn",
    "create_fake_model_infinite_loop",
]
