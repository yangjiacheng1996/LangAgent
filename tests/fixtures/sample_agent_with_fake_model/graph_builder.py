"""Integration test helper for building real LangGraph with FakeListChatModel.

This module provides utilities to construct real CompiledStateGraph instances
for testing F08 main_loop_dispatcher with actual LangGraph execution.
"""

from typing import Any
from unittest.mock import MagicMock

from langchain_core.language_models import FakeListChatModel
from langgraph.checkpoint.memory import MemorySaver

from langagent.primitives.state_graph_builder import build as build_graph
from langagent.runtime.agent_state import RuntimeConfig, GuardrailPolicy


def build_test_graph_with_fake_model(fake_model: FakeListChatModel):
    """Build a real CompiledStateGraph with FakeListChatModel for testing.
    
    Args:
        fake_model: FakeListChatModel with pre-programmed responses
    
    Returns:
        CompiledStateGraph ready for dispatch() testing
    """
    # Create mock LoadedAgent
    loaded_agent = MagicMock()
    loaded_agent.agent_dir = "/tmp/test_agent"
    loaded_agent.tool_ids = []  # No tools for basic tests
    
    # Create minimal RuntimeConfig
    config = RuntimeConfig(
        cli_args={},
        env_vars={},
        dotenv_values={},
        builtin_defaults={},
        model=fake_model,  # Use fake model
        model_provider="openai",
        model_name="fake-model",
        model_base_url=None,
        checkpointer="memory",
        middleware_ids=[],
        skill_dirs=[],
        log_level="INFO",
        guardrail_policy=None,
    )
    
    # Create memory checkpointer
    checkpoint = MemorySaver()
    
    # Build real graph
    graph = build_graph(loaded_agent, config, checkpoint)
    
    return graph


__all__ = ["build_test_graph_with_fake_model"]
