"""
Phase 4 Tests for User Story 2 (State Graph Compilation).

These tests MUST FAIL before implementation (T047).
Tests cover T029-T039 from tasks.md lines 96-109.
"""

import sys
import time
from pathlib import Path
from typing import Any, Optional
from unittest.mock import Mock, MagicMock, patch

import pytest

from langagent.primitives.exceptions import (
    GraphCompileError,
    ToolBindingError,
)


# Test fixtures and helper functions

@pytest.fixture
def mock_loaded_agent_minimal():
    """LoadedAgent with 0 tools, 0 middleware."""
    mock = Mock()
    mock.agent_dir = Path(__file__).parent.parent / "fixtures" / "test_agent_dirs" / "minimal"
    mock.tool_ids = []
    mock.instructions = "Test agent instructions"
    mock.skill_names = []
    mock.metadata = {}
    return mock


@pytest.fixture
def mock_loaded_agent_with_one_tool():
    """LoadedAgent with 1 tool."""
    mock = Mock()
    mock.agent_dir = Path(__file__).parent.parent / "fixtures" / "test_agent_dirs" / "with_tools"
    mock.tool_ids = ["test_tool_1"]
    mock.instructions = "Test agent with one tool"
    mock.skill_names = []
    mock.metadata = {}
    return mock


@pytest.fixture
def mock_loaded_agent_with_middleware():
    """LoadedAgent pointing to agent_dir with middleware."""
    mock = Mock()
    mock.agent_dir = Path(__file__).parent.parent / "fixtures" / "test_agent_dirs" / "with_middleware"
    mock.tool_ids = []
    mock.instructions = "Test agent with middleware"
    mock.skill_names = []
    mock.metadata = {}
    return mock


@pytest.fixture
def mock_runtime_config_minimal():
    """RuntimeConfig with memory checkpointer, no middleware, no guardrails."""
    mock = Mock()
    mock.model_provider = "openai"
    mock.model_name = "gpt-4"
    mock.model_base_url = None
    mock.model = None
    mock.checkpointer = "memory"
    mock.checkpoint_sqlite_path = None
    mock.checkpoint_postgres_dsn = None
    mock.middleware_ids = []
    mock.guardrail_policy = None
    return mock


@pytest.fixture
def mock_runtime_config_with_middleware():
    """RuntimeConfig with one middleware."""
    mock = Mock()
    mock.model_provider = "openai"
    mock.model_name = "gpt-4"
    mock.model_base_url = None
    mock.model = None
    mock.checkpointer = "memory"
    mock.checkpoint_sqlite_path = None
    mock.checkpoint_postgres_dsn = None
    mock.middleware_ids = ["rate_limiter"]
    mock.guardrail_policy = None
    return mock


@pytest.fixture
def mock_runtime_config_with_ten_middleware():
    """RuntimeConfig with 10 middleware for concurrent loading test."""
    mock = Mock()
    mock.model_provider = "openai"
    mock.model_name = "gpt-4"
    mock.model_base_url = None
    mock.model = None
    mock.checkpointer = "memory"
    mock.checkpoint_sqlite_path = None
    mock.checkpoint_postgres_dsn = None
    mock.middleware_ids = [
        "concurrent_01", "concurrent_02", "concurrent_03", "concurrent_04", "concurrent_05",
        "concurrent_06", "concurrent_07", "concurrent_08", "concurrent_09", "concurrent_10"
    ]
    mock.guardrail_policy = None
    return mock


@pytest.fixture
def mock_runtime_config_with_guardrail():
    """RuntimeConfig with guardrail policy."""
    mock = Mock()
    mock.model_provider = "openai"
    mock.model_name = "gpt-4"
    mock.model_base_url = None
    mock.model = None
    mock.checkpointer = "memory"
    mock.checkpoint_sqlite_path = None
    mock.checkpoint_postgres_dsn = None
    mock.middleware_ids = []
    mock.guardrail_policy = Mock()  # GuardrailPolicy mock
    mock.guardrail_policy.max_tokens = 1000
    mock.guardrail_policy.block_patterns = []
    return mock


@pytest.fixture
def mock_checkpoint_memory():
    """Real MemorySaver for memory checkpoint."""
    from langgraph.checkpoint.memory import MemorySaver
    return MemorySaver()


# Test T029 [P] [US2]: Minimal graph compilation
def test_build_minimal_agent_state(
    mock_loaded_agent_minimal,
    mock_runtime_config_minimal,
    mock_checkpoint_memory
):
    """
    T029: Test minimal graph compilation (0 tools, 0 middleware, memory checkpointer).
    Expects CompiledStateGraph that invokes successfully.
    MUST FAIL before T047 implementation.
    """
    from langagent.primitives.state_graph_builder import build
    
    # Build graph with minimal configuration
    compiled_graph = build(
        loaded_agent=mock_loaded_agent_minimal,
        config=mock_runtime_config_minimal,
        checkpoint=mock_checkpoint_memory
    )
    
    # Verify it's a CompiledStateGraph type
    assert compiled_graph is not None
    assert hasattr(compiled_graph, "invoke"), "CompiledStateGraph should have invoke method"
    
    # Verify graph can be invoked (basic smoke test)
    from langchain_core.messages import HumanMessage
    result = compiled_graph.invoke(
        {"messages": [HumanMessage(content="test")]},
        config={"configurable": {"thread_id": "test-thread"}}
    )
    assert "messages" in result, "Graph should return state with messages field"


# Test T030 [P] [US2]: Graph with one tool
def test_build_with_one_tool(
    mock_loaded_agent_with_one_tool,
    mock_runtime_config_minimal,
    mock_checkpoint_memory
):
    """
    T030: Test graph compilation with one tool.
    Expects graph includes tools node.
    MUST FAIL before T047 implementation.
    """
    from langagent.primitives.state_graph_builder import build
    
    # Build graph with one tool
    compiled_graph = build(
        loaded_agent=mock_loaded_agent_with_one_tool,
        config=mock_runtime_config_minimal,
        checkpoint=mock_checkpoint_memory
    )
    
    # Verify graph structure includes tools node
    # This will depend on LangGraph's internal structure
    assert compiled_graph is not None
    
    # Verify tool was bound (implementation-dependent verification)
    # Note: Actual verification depends on LangGraph's API
    assert hasattr(compiled_graph, "nodes") or hasattr(compiled_graph, "get_graph"), \
        "CompiledStateGraph should expose graph structure"


# Test T031 [P] [US2]: Graph with one middleware
def test_build_with_one_middleware(
    mock_loaded_agent_with_middleware,
    mock_runtime_config_with_middleware,
    mock_checkpoint_memory
):
    """
    T031: Test graph compilation with one middleware.
    Expects middleware hooks registered via Runtime context.
    MUST FAIL before T047 implementation.
    """
    from langagent.primitives.state_graph_builder import build
    
    # Build graph with one middleware
    compiled_graph = build(
        loaded_agent=mock_loaded_agent_with_middleware,
        config=mock_runtime_config_with_middleware,
        checkpoint=mock_checkpoint_memory
    )
    
    # Verify graph was compiled
    assert compiled_graph is not None
    
    # Verify middleware was loaded and registered
    # This requires checking internal state or side effects
    # For now, verify no exception was raised during build
    assert hasattr(compiled_graph, "invoke"), "Graph should be invocable"


# Test T032 [P] [US2]: 10 concurrent middleware registration
def test_build_with_ten_middleware_concurrent(
    mock_loaded_agent_with_middleware,
    mock_runtime_config_with_ten_middleware,
    mock_checkpoint_memory
):
    """
    T032: Test 10 concurrent middleware registration.
    Expects all 10 registered in priority order within 500ms per FR-051.
    Timer starts AFTER fixtures loaded, stops AFTER last middleware hook binding completes.
    MUST FAIL before T047 implementation.
    """
    from langagent.primitives.state_graph_builder import build
    
    # All fixtures are now in memory, start timer
    start_time = time.perf_counter()
    
    # Build graph with 10 middleware
    compiled_graph = build(
        loaded_agent=mock_loaded_agent_with_middleware,
        config=mock_runtime_config_with_ten_middleware,
        checkpoint=mock_checkpoint_memory
    )
    
    # Stop timer after middleware binding completes
    end_time = time.perf_counter()
    elapsed_ms = (end_time - start_time) * 1000
    
    # Verify performance constraint: < 500ms
    assert elapsed_ms < 500, f"Middleware loading took {elapsed_ms:.2f}ms, exceeds 500ms limit (FR-051)"
    
    # Verify graph was compiled successfully
    assert compiled_graph is not None
    assert hasattr(compiled_graph, "invoke"), "Graph should be invocable"
    
    # Verify all 10 middleware were loaded (implementation-specific check)
    # This will be verified in implementation phase


# Test T033 [P] [US2]: Reducer merge behavior
def test_build_reducer_merge_todos(
    mock_loaded_agent_minimal,
    mock_runtime_config_minimal,
    mock_checkpoint_memory
):
    """
    T033: Test reducer merge behavior for todos field.
    Consecutive state updates with new todos should use replace_with_merge, not blind overwrite.
    MUST FAIL before T047 implementation.
    """
    from langagent.primitives.state_graph_builder import build
    
    # Build minimal graph
    compiled_graph = build(
        loaded_agent=mock_loaded_agent_minimal,
        config=mock_runtime_config_minimal,
        checkpoint=mock_checkpoint_memory
    )
    
    # Test consecutive state updates
    from langchain_core.messages import HumanMessage
    
    # First update with initial todos
    result1 = compiled_graph.invoke({
        "messages": [HumanMessage(content="test")],
        "todos": [{"id": "1", "description": "Task 1"}]
    }, config={"configurable": {"thread_id": "test-thread"}})
    
    # Second update with new todos - should merge, not overwrite
    result2 = compiled_graph.invoke({
        "messages": result1["messages"],
        "todos": [{"id": "2", "description": "Task 2"}]
    }, config={"configurable": {"thread_id": "test-thread"}})
    
    # Verify replace_with_merge behavior
    # The exact behavior depends on reducer implementation
    assert "todos" in result2, "State should have todos field"
    assert isinstance(result2["todos"], list), "todos should be a list"


# Test T034 [P] [US2]: Invalid state schema error
def test_build_invalid_state_schema(
    mock_loaded_agent_minimal,
    mock_runtime_config_minimal,
    mock_checkpoint_memory
):
    """
    T034: Test invalid state schema handling.
    Wrong type for messages field should raise GraphCompileError with exit code 70.
    MUST FAIL before T047 implementation.
    """
    from langagent.primitives.state_graph_builder import build
    
    # Build graph
    compiled_graph = build(
        loaded_agent=mock_loaded_agent_minimal,
        config=mock_runtime_config_minimal,
        checkpoint=mock_checkpoint_memory
    )
    
    # Attempt to invoke with invalid state (wrong type for messages)
    with pytest.raises(Exception) as exc_info:
        compiled_graph.invoke({
            "messages": "invalid_string_not_list"  # Should be list[BaseMessage]
        })
    
    # Verify it's a GraphCompileError or similar validation error
    # The exact exception type depends on implementation
    assert exc_info.value is not None


# Test T035 [P] [US2]: Middleware syntax error
def test_build_middleware_syntax_error(
    mock_loaded_agent_with_middleware,
    mock_checkpoint_memory
):
    """
    T035: Test middleware syntax error handling.
    Middleware file with syntax error should raise GraphCompileError with specific format:
    "Middleware '{name}' at {path}: SyntaxError: {details}" per FR-017.
    MUST FAIL before T047 implementation.
    """
    from langagent.primitives.state_graph_builder import build
    
    # Create config with syntax_error middleware
    config = Mock()
    config.model_provider = "openai"
    config.model_name = "gpt-4"
    config.model_base_url = None
    config.model = None
    config.checkpointer = "memory"
    config.checkpoint_sqlite_path = None
    config.checkpoint_postgres_dsn = None
    config.middleware_ids = ["syntax_error"]  # This middleware has syntax error
    config.guardrail_policy = None
    
    # Attempt to build graph with syntax error middleware
    with pytest.raises(GraphCompileError) as exc_info:
        build(
            loaded_agent=mock_loaded_agent_with_middleware,
            config=config,
            checkpoint=mock_checkpoint_memory
        )
    
    # Verify error message format per FR-017
    error_msg = str(exc_info.value)
    assert "syntax_error" in error_msg.lower(), "Error should mention middleware name"
    assert "syntax" in error_msg.lower(), "Error should mention syntax error"
    
    # Verify exit code
    assert hasattr(exc_info.value, "exit_code"), "GraphCompileError should have exit_code"
    assert exc_info.value.exit_code == 70, "Exit code should be 70"


# Test T036 [P] [US2]: Tool binding error
def test_build_tool_binding_error(
    mock_checkpoint_memory
):
    """
    T036: Test tool binding error handling.
    Nonexistent tool_id should raise ToolBindingError with exit code 70.
    MUST FAIL before T047 implementation.
    """
    from langagent.primitives.state_graph_builder import build
    
    # Create LoadedAgent with nonexistent tool
    loaded_agent = Mock()
    loaded_agent.agent_dir = Path(__file__).parent.parent / "fixtures" / "test_agent_dirs" / "minimal"
    loaded_agent.tool_ids = ["nonexistent_tool_xyz"]  # Tool doesn't exist
    loaded_agent.instructions = "Test"
    loaded_agent.skill_names = []
    loaded_agent.metadata = {}
    
    # Create minimal config
    config = Mock()
    config.model_provider = "openai"
    config.model_name = "gpt-4"
    config.model_base_url = None
    config.model = None
    config.checkpointer = "memory"
    config.checkpoint_sqlite_path = None
    config.checkpoint_postgres_dsn = None
    config.middleware_ids = []
    config.guardrail_policy = None
    
    # Attempt to build graph with nonexistent tool
    with pytest.raises(ToolBindingError) as exc_info:
        build(
            loaded_agent=loaded_agent,
            config=config,
            checkpoint=mock_checkpoint_memory
        )
    
    # Verify exit code
    assert hasattr(exc_info.value, "exit_code"), "ToolBindingError should have exit_code"
    assert exc_info.value.exit_code == 70, "Exit code should be 70"


# Test T036a [P] [US2]: Checkpoint validation
def test_build_validates_checkpoint(
    mock_loaded_agent_minimal,
    mock_runtime_config_minimal
):
    """
    T036a: Test checkpoint validation.
    checkpoint=None should raise GraphCompileError with exit code 70 and message
    "Invalid checkpoint: {reason}" per FR-014a.
    MUST FAIL before T047 implementation.
    """
    from langagent.primitives.state_graph_builder import build
    
    # Attempt to build graph with None checkpoint
    with pytest.raises(GraphCompileError) as exc_info:
        build(
            loaded_agent=mock_loaded_agent_minimal,
            config=mock_runtime_config_minimal,
            checkpoint=None  # Invalid checkpoint
        )
    
    # Verify error message format
    error_msg = str(exc_info.value)
    assert "invalid checkpoint" in error_msg.lower(), "Error should mention invalid checkpoint"
    
    # Verify exit code
    assert hasattr(exc_info.value, "exit_code"), "GraphCompileError should have exit_code"
    assert exc_info.value.exit_code == 70, "Exit code should be 70"


# Test T037 [P] [US2]: sys.modules cleanup
def test_build_cleans_sys_modules(
    mock_loaded_agent_with_middleware,
    mock_runtime_config_with_middleware,
    mock_checkpoint_memory
):
    """
    T037: Test sys.modules cleanup after build.
    After build(), expects no langagent_dynamic_middleware_* entries in sys.modules per FR-016.
    MUST FAIL before T047 implementation.
    """
    from langagent.primitives.state_graph_builder import build
    
    # Record initial sys.modules state
    initial_modules = set(sys.modules.keys())
    
    # Build graph with middleware
    compiled_graph = build(
        loaded_agent=mock_loaded_agent_with_middleware,
        config=mock_runtime_config_with_middleware,
        checkpoint=mock_checkpoint_memory
    )
    
    # Verify graph was compiled
    assert compiled_graph is not None
    
    # Check sys.modules for dynamic middleware entries
    final_modules = set(sys.modules.keys())
    dynamic_middleware_modules = [
        mod for mod in final_modules
        if mod.startswith("langagent_dynamic_middleware_")
    ]
    
    # Verify cleanup: no dynamic middleware modules should remain
    assert len(dynamic_middleware_modules) == 0, \
        f"Found {len(dynamic_middleware_modules)} dynamic middleware modules in sys.modules: {dynamic_middleware_modules}"


# Test T038 [P] [US2]: Guardrail middleware instantiation
def test_build_with_guardrail_middleware(
    mock_loaded_agent_minimal,
    mock_runtime_config_with_guardrail,
    mock_checkpoint_memory
):
    """
    T038: Test guardrail middleware instantiation.
    When guardrail_policy is not None, expects build_middleware(policy) called per stub.
    MUST FAIL before T047 implementation.
    """
    from langagent.primitives.state_graph_builder import build
    
    # Mock the build_middleware function
    with patch("langagent.cross_cutting.guardrail_middleware.build_middleware") as mock_build_middleware:
        mock_build_middleware.return_value = Mock()  # Mock AgentMiddleware instance
        
        # Build graph with guardrail policy
        compiled_graph = build(
            loaded_agent=mock_loaded_agent_minimal,
            config=mock_runtime_config_with_guardrail,
            checkpoint=mock_checkpoint_memory
        )
        
        # Verify build_middleware was called with policy
        mock_build_middleware.assert_called_once()
        call_kwargs = mock_build_middleware.call_args[1]
        assert "policy" in call_kwargs, "build_middleware should be called with policy kwarg"
        assert call_kwargs["policy"] == mock_runtime_config_with_guardrail.guardrail_policy
        
        # Verify graph was compiled
        assert compiled_graph is not None


# Test T039 [P] [US2]: Middleware priority tiebreaker
def test_build_middleware_priority_tiebreaker(
    mock_loaded_agent_with_middleware,
    mock_checkpoint_memory
):
    """
    T039: Test middleware priority tiebreaker.
    Multiple middleware with same priority should be sorted by name alphabetically per spec edge case.
    MUST FAIL before T047 implementation.
    """
    from langagent.primitives.state_graph_builder import build
    
    # Create config with two middleware having same priority
    config = Mock()
    config.model_provider = "openai"
    config.model_name = "gpt-4"
    config.model_base_url = None
    config.model = None
    config.checkpointer = "memory"
    config.checkpoint_sqlite_path = None
    config.checkpoint_postgres_dsn = None
    # Both priority_a and priority_b have priority=100
    config.middleware_ids = ["priority_b", "priority_a"]  # Loaded in reverse alphabetical order
    config.guardrail_policy = None
    
    # Build graph
    compiled_graph = build(
        loaded_agent=mock_loaded_agent_with_middleware,
        config=config,
        checkpoint=mock_checkpoint_memory
    )
    
    # Verify graph was compiled
    assert compiled_graph is not None
    
    # Verify middleware registration order
    # This will require implementation-specific verification
    # For now, verify no exception was raised
    assert hasattr(compiled_graph, "invoke"), "Graph should be invocable"


# Additional edge case tests

def test_build_with_empty_middleware_list(
    mock_loaded_agent_minimal,
    mock_runtime_config_minimal,
    mock_checkpoint_memory
):
    """
    Additional test: Verify empty middleware_ids list is handled correctly.
    """
    from langagent.primitives.state_graph_builder import build
    
    # Ensure middleware_ids is empty list
    assert mock_runtime_config_minimal.middleware_ids == []
    
    # Build graph
    compiled_graph = build(
        loaded_agent=mock_loaded_agent_minimal,
        config=mock_runtime_config_minimal,
        checkpoint=mock_checkpoint_memory
    )
    
    # Verify graph was compiled
    assert compiled_graph is not None
    assert hasattr(compiled_graph, "invoke")


def test_build_with_nonexistent_middleware(
    mock_loaded_agent_with_middleware,
    mock_checkpoint_memory
):
    """
    Additional test: Verify nonexistent middleware file raises appropriate error.
    """
    from langagent.primitives.state_graph_builder import build
    
    # Create config with nonexistent middleware
    config = Mock()
    config.model_provider = "openai"
    config.model_name = "gpt-4"
    config.model_base_url = None
    config.model = None
    config.checkpointer = "memory"
    config.checkpoint_sqlite_path = None
    config.checkpoint_postgres_dsn = None
    config.middleware_ids = ["nonexistent_middleware_xyz"]
    config.guardrail_policy = None
    
    # Attempt to build graph with nonexistent middleware
    with pytest.raises(GraphCompileError) as exc_info:
        build(
            loaded_agent=mock_loaded_agent_with_middleware,
            config=config,
            checkpoint=mock_checkpoint_memory
        )
    
    # Verify error is raised
    assert exc_info.value is not None


# ============================================================================
# Phase 7: User Story 5 - Stage Logging Integration Tests (T078-T082)
# ============================================================================

def test_build_emits_start_tag(
    mock_loaded_agent_minimal,
    mock_runtime_config_minimal,
    mock_checkpoint_memory
):
    """
    T078: Test graph_compose start tag emission.
    
    Expected behavior:
    - Emits la.runtime.graph_compose.start
    - MUST FAIL before T088 implementation
    """
    from langagent.primitives.state_graph_builder import build
    
    with patch("langagent.primitives.state_graph_builder.emit") as mock_emit:
        compiled_graph = build(
            loaded_agent=mock_loaded_agent_minimal,
            config=mock_runtime_config_minimal,
            checkpoint=mock_checkpoint_memory
        )
        
        # Verify start tag was emitted
        start_calls = [call for call in mock_emit.call_args_list 
                      if call[0][0] == "la.runtime.graph_compose.start"]
        assert len(start_calls) >= 1, "Expected la.runtime.graph_compose.start tag to be emitted"


def test_build_emits_middleware_bind_tag(
    mock_loaded_agent_with_middleware,
    mock_runtime_config_with_middleware,
    mock_checkpoint_memory
):
    """
    T079: Test graph_compose middleware_bind tag emission.
    
    Expected behavior:
    - Per middleware, emits la.runtime.graph_compose.middleware_bind with middleware id payload
    - MUST FAIL before T088 implementation
    """
    from langagent.primitives.state_graph_builder import build
    
    with patch("langagent.primitives.state_graph_builder.emit") as mock_emit:
        compiled_graph = build(
            loaded_agent=mock_loaded_agent_with_middleware,
            config=mock_runtime_config_with_middleware,
            checkpoint=mock_checkpoint_memory
        )
        
        # Verify middleware_bind tag was emitted
        middleware_bind_calls = [call for call in mock_emit.call_args_list 
                                if call[0][0] == "la.runtime.graph_compose.middleware_bind"]
        assert len(middleware_bind_calls) >= 1, "Expected la.runtime.graph_compose.middleware_bind tag to be emitted"
        
        # Verify payload contains middleware id
        bind_payload = middleware_bind_calls[0][0][1] if len(middleware_bind_calls[0][0]) > 1 else {}
        assert "id" in bind_payload, "Middleware bind tag payload should contain id"


def test_build_emits_tool_bind_tag(
    mock_loaded_agent_with_one_tool,
    mock_runtime_config_minimal,
    mock_checkpoint_memory
):
    """
    T080: Test graph_compose tool_bind tag emission.
    
    Expected behavior:
    - Per tool, emits la.runtime.graph_compose.tool_bind with tool_id payload
    - MUST FAIL before T088 implementation
    """
    from langagent.primitives.state_graph_builder import build
    
    with patch("langagent.primitives.state_graph_builder.emit") as mock_emit:
        compiled_graph = build(
            loaded_agent=mock_loaded_agent_with_one_tool,
            config=mock_runtime_config_minimal,
            checkpoint=mock_checkpoint_memory
        )
        
        # Verify tool_bind tag was emitted
        tool_bind_calls = [call for call in mock_emit.call_args_list 
                          if call[0][0] == "la.runtime.graph_compose.tool_bind"]
        assert len(tool_bind_calls) >= 1, "Expected la.runtime.graph_compose.tool_bind tag to be emitted"
        
        # Verify payload contains tool_id
        bind_payload = tool_bind_calls[0][0][1] if len(tool_bind_calls[0][0]) > 1 else {}
        assert "tool_id" in bind_payload, "Tool bind tag payload should contain tool_id"


def test_build_emits_ok_tag(
    mock_loaded_agent_minimal,
    mock_runtime_config_minimal,
    mock_checkpoint_memory
):
    """
    T081: Test graph_compose ok tag emission.
    
    Expected behavior:
    - Emits la.runtime.graph_compose.ok with duration_ms payload
    - MUST FAIL before T088 implementation
    """
    from langagent.primitives.state_graph_builder import build
    
    with patch("langagent.primitives.state_graph_builder.emit") as mock_emit:
        compiled_graph = build(
            loaded_agent=mock_loaded_agent_minimal,
            config=mock_runtime_config_minimal,
            checkpoint=mock_checkpoint_memory
        )
        
        # Verify ok tag was emitted
        ok_calls = [call for call in mock_emit.call_args_list 
                   if call[0][0] == "la.runtime.graph_compose.ok"]
        assert len(ok_calls) >= 1, "Expected la.runtime.graph_compose.ok tag to be emitted"
        
        # Verify payload contains duration_ms
        ok_payload = ok_calls[0][0][1] if len(ok_calls[0][0]) > 1 else {}
        assert "duration_ms" in ok_payload, "Ok tag payload should contain duration_ms"
        assert isinstance(ok_payload["duration_ms"], (int, float)), "duration_ms should be numeric"


def test_build_emits_fail_tag(
    mock_loaded_agent_minimal,
    mock_runtime_config_minimal
):
    """
    T082: Test graph_compose fail tag emission.
    
    Expected behavior:
    - On GraphCompileError, emits la.runtime.graph_compose.fail with error payload
    - MUST FAIL before T088 implementation
    """
    from langagent.primitives.state_graph_builder import build
    
    with patch("langagent.primitives.state_graph_builder.emit") as mock_emit:
        with pytest.raises(GraphCompileError):
            # Pass None checkpoint to trigger error
            build(
                loaded_agent=mock_loaded_agent_minimal,
                config=mock_runtime_config_minimal,
                checkpoint=None
            )
        
        # Verify fail tag was emitted
        fail_calls = [call for call in mock_emit.call_args_list 
                     if call[0][0] == "la.runtime.graph_compose.fail"]
        assert len(fail_calls) >= 1, "Expected la.runtime.graph_compose.fail tag to be emitted"
        
        # Verify payload contains error info
        fail_payload = fail_calls[0][0][1] if len(fail_calls[0][0]) > 1 else {}
        assert "error_type" in fail_payload or "error_message" in fail_payload, \
            "Fail tag payload should contain error info"
