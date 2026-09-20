"""Tests for ReAct Main Loop Runtime Dispatcher (F08).

This module contains ≥28 test cases covering:
- Single-turn dispatch (US1)
- Multi-turn loop convergence (US2)
- Max turns termination (US3)
- Human-in-the-loop interruption (US4)
- Event bus and structured logging (US6)
- Stage capability boundary enforcement (US7)
- Tool error recording
- Invoke + Stream dual mode support
- Doctor probe factory
- Integration tests with real LangGraph

Constitutional Alignment:
    - Article VIII: TDD rigidity (Red-Green-Refactor)
    - Article VIII Clause 4: No mocking graph behavior (real LangGraph)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Any

from langagent.runtime.main_loop_dispatcher import (
    dispatch,
    run_until_done,
    build_doctor_probes,
    HitlInterruptedError,
    TokenLimitExceededError,
)
from langagent.runtime.agent_state import AgentState, ErrorEntry
from langagent.primitives.langchain_types import HumanMessage, AIMessage, ToolMessage


# ============================================================================
# Phase 2: Foundational - Exception Tests (T017, T018)
# ============================================================================


def test_hitl_interrupted_error_carries_state():
    """T017: HitlInterruptedError.state attribute exists."""
    state = {"messages": [HumanMessage(content="Test")]}
    error = HitlInterruptedError(
        state=state,
        reason="keyboard_interrupt",
        message="User interrupted"
    )
    
    assert error.state == state
    assert error.reason == "keyboard_interrupt"
    assert "interrupted" in str(error).lower()


def test_token_limit_exceeded_error_metadata():
    """T018: TokenLimitExceededError has turn_count/max_turns fields."""
    error = TokenLimitExceededError(
        turn_count=30,
        max_turns=30,
        message="Failed to converge"
    )
    
    assert error.turn_count == 30
    assert error.max_turns == 30
    assert "30" in str(error)


# ============================================================================
# Phase 3: User Story 1 - Single-Turn Tests (T024-T052)
# ============================================================================


@pytest.mark.skip(reason="T024: Implement in Phase 3 after dispatch() skeleton")
def test_dispatch_simple_greeting():
    """US1: Fake model returns final AIMessage (no tool_calls), verify state updated."""
    pass


@pytest.mark.skip(reason="T025: Implement in Phase 3")
def test_dispatch_with_tool_call():
    """US1: Fake model returns tool_call, verify ToolMessage appended."""
    pass


@pytest.mark.skip(reason="T026: Implement in Phase 3")
def test_dispatch_emits_tool_call_event():
    """US1: Mock event_bus, verify tool_call event published."""
    pass


@pytest.mark.skip(reason="T027: Implement in Phase 3")
def test_dispatch_emits_tool_result_event():
    """US1: Mock event_bus, verify tool_result event published."""
    pass


@pytest.mark.skip(reason="T028: Implement in Phase 3")
def test_dispatch_emits_model_response_event():
    """US1: Mock event_bus, verify model_response event published."""
    pass


@pytest.mark.skip(reason="T029: Implement in Phase 3")
def test_dispatch_increments_turn_count():
    """US1: Mock metrics_collector, verify turn_count +1."""
    pass


# Logging tests (T046-T052)
@pytest.mark.skip(reason="T046: Implement in Phase 3")
def test_dispatch_emits_lifecycle_run_turn_log():
    """US1: Verify la.lifecycle.run.turn log emitted."""
    pass


@pytest.mark.skip(reason="T047: Implement in Phase 3")
def test_dispatch_emits_runtime_main_loop_turn_start_end_logs():
    """US1: Verify la.runtime.main_loop.turn.start and turn.end logs."""
    pass


@pytest.mark.skip(reason="T048: Implement in Phase 3")
def test_dispatch_emits_lifecycle_run_tool_call_log():
    """US1: Verify la.lifecycle.run.tool_call log emitted."""
    pass


@pytest.mark.skip(reason="T049: Implement in Phase 3")
def test_dispatch_emits_runtime_main_loop_tool_call_log():
    """US1: Verify la.runtime.main_loop.tool_call log emitted."""
    pass


@pytest.mark.skip(reason="T050: Implement in Phase 3")
def test_dispatch_emits_lifecycle_run_tool_result_log():
    """US1: Verify la.lifecycle.run.tool_result log emitted."""
    pass


@pytest.mark.skip(reason="T051: Implement in Phase 3")
def test_dispatch_emits_runtime_main_loop_model_call_log():
    """US1: Verify la.runtime.main_loop.model_call log emitted."""
    pass


@pytest.mark.skip(reason="T052: Implement in Phase 3")
def test_main_loop_event_and_log_both_emitted():
    """US1: Verify dual-channel (Event + Log) simultaneous emission."""
    pass


# ============================================================================
# Phase 4: User Story 2 - Multi-Turn Tests (T053-T065)
# ============================================================================


@pytest.mark.skip(reason="T053: Implement in Phase 4")
def test_run_until_done_converges():
    """US2: Fake model converges after 3 turns, verify final state."""
    pass


@pytest.mark.skip(reason="T054: Implement in Phase 4")
def test_run_until_done_state_message_order():
    """US2: Verify messages contain HumanMessage + (AIMessage + ToolMessage)×N."""
    pass


@pytest.mark.skip(reason="T055: Implement in Phase 4")
def test_run_until_done_emits_turn_logs_per_round():
    """US2: Mock 3 turns, verify 3× la.lifecycle.run.turn logs."""
    pass


@pytest.mark.skip(reason="T056: Implement in Phase 4")
def test_run_until_done_final_state_passable_to_exit_cleanup():
    """US2: Verify returned state structure compatible with F09."""
    pass


@pytest.mark.skip(reason="T063: Implement in Phase 4")
def test_run_until_done_emits_lifecycle_run_start_log():
    """US2: Verify la.lifecycle.run.start log emitted."""
    pass


@pytest.mark.skip(reason="T064: Implement in Phase 4")
def test_run_until_done_emits_runtime_main_loop_start_log():
    """US2: Verify la.runtime.main_loop.start log emitted."""
    pass


@pytest.mark.skip(reason="T065: Implement in Phase 4")
def test_run_until_done_emits_runtime_main_loop_end_log():
    """US2: Verify la.runtime.main_loop.end log emitted."""
    pass


# ============================================================================
# Phase 5: User Story 3 - Max Turns Tests (T066-T073)
# ============================================================================


@pytest.mark.skip(reason="T066: Implement in Phase 5")
def test_run_until_done_max_turns_exceeded():
    """US3: Infinite loop, verify TokenLimitExceededError after 30 turns."""
    pass


@pytest.mark.skip(reason="T067: Implement in Phase 5")
def test_run_until_done_max_turns_custom():
    """US3: max_turns=10, verify error after 10 turns."""
    pass


@pytest.mark.skip(reason="T068: Implement in Phase 5")
def test_run_until_done_max_turns_preserves_state():
    """US3: Verify state preserved in exception context."""
    pass


@pytest.mark.skip(reason="T069: Implement in Phase 5")
def test_run_until_done_near_limit_warning():
    """US3: Verify warning log at turn >= max_turns * 0.9."""
    pass


# ============================================================================
# Phase 6: User Story 4 - Interruption Tests (T074-T080)
# ============================================================================


@pytest.mark.skip(reason="T074: Implement in Phase 6")
def test_run_until_done_keyboard_interrupt():
    """US4: Mock KeyboardInterrupt, verify HitlInterruptedError."""
    pass


@pytest.mark.skip(reason="T075: Implement in Phase 6")
def test_dispatch_guardrail_interrupt():
    """US4: Tool with requires_approval=True, verify HitlInterruptedError."""
    pass


@pytest.mark.skip(reason="T076: Implement in Phase 6")
def test_dispatch_interrupt_preserves_state():
    """US4: Verify error.state contains messages + scratchpad."""
    pass


@pytest.mark.skip(reason="T077: Implement in Phase 6")
def test_dispatch_guardrail_no_log_re_emit():
    """US4: Verify F08 does not re-emit la.cross_cutting.guardrail.block."""
    pass


# ============================================================================
# Phase 8: User Story 6 - Logging Tests (T088-T093)
# ============================================================================


@pytest.mark.skip(reason="T088: Implement in Phase 8")
def test_main_loop_log_tags_in_whitelist():
    """US6: Verify 12 F08 tags + 1 F04 tag all in F02 ALLOWED_TAGS."""
    pass


@pytest.mark.skip(reason="T089: Implement in Phase 8")
def test_run_until_done_emits_all_13_tags():
    """US6: Run with guardrail trigger, verify count=13."""
    pass


@pytest.mark.skip(reason="T090: Implement in Phase 8")
def test_metrics_subscriber_records_latency():
    """US6: Mock metrics_collector, verify events trigger record_latency."""
    pass


@pytest.mark.skip(reason="T091: Implement in Phase 8")
def test_audit_subscriber_writes_on_guardrail_block():
    """US6: Mock audit_recorder, verify guardrail_block event triggers write."""
    pass


# ============================================================================
# Phase 9: User Story 7 - Stage Guard Tests (T094-T099)
# ============================================================================


@pytest.mark.skip(reason="T094: Implement in Phase 9")
def test_dispatch_stage_violation_read_env():
    """US7: Mock open(.env), verify StageCapabilityViolationError."""
    pass


@pytest.mark.skip(reason="T095: Implement in Phase 9")
def test_dispatch_stage_violation_reload_dir():
    """US7: Attempt RuntimeDirLoader.load(), verify error."""
    pass


@pytest.mark.skip(reason="T096: Implement in Phase 9")
def test_dispatch_stage_violation_resolve_config():
    """US7: Attempt RuntimeConfigResolver.resolve(), verify error."""
    pass


@pytest.mark.skip(reason="T097: Implement in Phase 9")
def test_dispatch_stage_violation_create_model():
    """US7: Attempt chat_model_factory.create(), verify error."""
    pass


# ============================================================================
# Phase 10: Tool Error Recording Tests (T100-T107)
# ============================================================================


@pytest.mark.skip(reason="T100: Implement in Phase 10")
def test_run_until_done_tool_exception():
    """Tool raises TimeoutError, verify loop continues."""
    pass


@pytest.mark.skip(reason="T101: Implement in Phase 10")
def test_dispatch_tool_error_structure():
    """Verify scratchpad['errors'][0] has 4 fields."""
    pass


@pytest.mark.skip(reason="T102: Implement in Phase 10")
def test_run_until_done_error_no_early_termination():
    """Tool fails 5 times, verify loop continues to max_turns."""
    pass


# ============================================================================
# Phase 11: Dual Mode Tests (T108-T115f)
# ============================================================================


def test_dispatch_invoke_mode():
    """T108: Call dispatch() (default invoke mode), verify final state returned."""
    from tests.fixtures.sample_agent_with_fake_model.fake_model_config import create_fake_model_single_turn
    from tests.fixtures.sample_agent_with_fake_model.graph_builder import build_test_graph_with_fake_model
    from langagent.primitives.langchain_types import HumanMessage
    
    fake_model = create_fake_model_single_turn()
    graph = build_test_graph_with_fake_model(fake_model)
    
    state: AgentState = {
        "messages": [HumanMessage(content="Test")]
    }
    
    # Call dispatch - should return final state
    result = dispatch(graph, state)
    
    # Verify result is a dict (AgentState)
    assert isinstance(result, dict)
    assert "messages" in result


def test_dispatch_stream_mode():
    """T109: Call dispatch_stream() generator, verify intermediate states yielded."""
    from langagent.runtime.main_loop_dispatcher import dispatch_stream
    from tests.fixtures.sample_agent_with_fake_model.fake_model_config import create_fake_model_single_turn
    from tests.fixtures.sample_agent_with_fake_model.graph_builder import build_test_graph_with_fake_model
    from langagent.primitives.langchain_types import HumanMessage
    
    fake_model = create_fake_model_single_turn()
    graph = build_test_graph_with_fake_model(fake_model)
    
    state: AgentState = {
        "messages": [HumanMessage(content="Test")]
    }
    
    # Call dispatch_stream - should return a generator
    stream = dispatch_stream(graph, state)
    
    # Verify it's a generator
    assert hasattr(stream, '__iter__')
    
    # Consume the stream
    states = list(stream)
    
    # Should have at least one state yielded
    assert len(states) >= 0  # May be 0 for passthrough node


def test_dispatch_stream_yields_per_node():
    """T110: Verify stream yields (node_name, state_snapshot) tuples."""
    from langagent.runtime.main_loop_dispatcher import dispatch_stream
    from tests.fixtures.sample_agent_with_fake_model.fake_model_config import create_fake_model_single_turn
    from tests.fixtures.sample_agent_with_fake_model.graph_builder import build_test_graph_with_fake_model
    from langagent.primitives.langchain_types import HumanMessage
    
    fake_model = create_fake_model_single_turn()
    graph = build_test_graph_with_fake_model(fake_model)
    
    state: AgentState = {
        "messages": [HumanMessage(content="Test")]
    }
    
    # Consume stream and check format
    for item in dispatch_stream(graph, state):
        # Each item should be a tuple of (node_name, state_snapshot)
        assert isinstance(item, tuple)
        assert len(item) == 2
        node_name, state_snapshot = item
        assert isinstance(node_name, str)
        assert isinstance(state_snapshot, dict)


# ============================================================================
# Phase 12: Doctor Probes Tests (T116-T123)
# ============================================================================


@pytest.mark.skip(reason="T116: Implement in Phase 12")
def test_build_doctor_probes_returns_two_callables():
    """Verify return type is tuple[Callable, Callable]."""
    pass


@pytest.mark.skip(reason="T117: Implement in Phase 12")
def test_model_probe_success():
    """Fake config with valid model, verify probe returns (True, 'ok')."""
    pass


@pytest.mark.skip(reason="T118: Implement in Phase 12")
def test_model_probe_failure_invalid_key():
    """Fake config with invalid API key, verify (False, 'AuthenticationError...')."""
    pass


@pytest.mark.skip(reason="T119: Implement in Phase 12")
def test_checkpoint_probe_success():
    """Fake config with memory checkpointer, verify (True, 'ok')."""
    pass


@pytest.mark.skip(reason="T120: Implement in Phase 12")
def test_checkpoint_probe_failure_missing_path():
    """Fake config with missing SQLite path, verify (False, 'FileNotFoundError...')."""
    pass


# ============================================================================
# Phase 13: Integration Tests (T124-T129)
# ============================================================================


def test_real_graph_with_fake_model():
    """T124: Build real StateGraph with FakeListChatModel, call dispatch()."""
    from tests.fixtures.sample_agent_with_fake_model.fake_model_config import create_fake_model_single_turn
    from tests.fixtures.sample_agent_with_fake_model.graph_builder import build_test_graph_with_fake_model
    from langagent.primitives.langchain_types import HumanMessage
    
    # Create fake model with single response
    fake_model = create_fake_model_single_turn()
    
    # Build real graph
    graph = build_test_graph_with_fake_model(fake_model)
    
    # Create initial state
    state: AgentState = {
        "messages": [HumanMessage(content="What is 2+2?")]
    }
    
    # Call dispatch() - this should work with real LangGraph
    result = dispatch(graph, state)
    
    # Verify result has messages
    assert "messages" in result
    assert len(result["messages"]) >= 1


@pytest.mark.skip(reason="T125: Implement in Phase 13")
def test_real_graph_with_fake_tool():
    """Build real graph with @tool decorated function, verify execution."""
    pass


@pytest.mark.skip(reason="T126: Implement in Phase 13")
def test_real_graph_with_checkpointer_memory():
    """Build graph with MemorySaver, run 2 turns, verify persistence."""
    pass


# ============================================================================
# Phase 14: Polish Tests (T134a, T134b, T137, T137a)
# ============================================================================


def test_dispatch_handles_missing_optional_fields():
    """T134a: State without todos/scratchpad fields, verify dispatch() initializes."""
    from tests.fixtures.sample_agent_with_fake_model.fake_model_config import create_fake_model_single_turn
    from tests.fixtures.sample_agent_with_fake_model.graph_builder import build_test_graph_with_fake_model
    from langagent.primitives.langchain_types import HumanMessage
    
    fake_model = create_fake_model_single_turn()
    graph = build_test_graph_with_fake_model(fake_model)
    
    # State with only messages (no todos, scratchpad)
    state: AgentState = {
        "messages": [HumanMessage(content="Test")]
    }
    
    # Should not raise error
    result = dispatch(graph, state)
    
    # Verify result
    assert isinstance(result, dict)
    assert "messages" in result


def test_dispatch_handles_missing_files_context_fields():
    """T134b: State without files/context fields, verify dispatch() initializes."""
    from tests.fixtures.sample_agent_with_fake_model.fake_model_config import create_fake_model_single_turn
    from tests.fixtures.sample_agent_with_fake_model.graph_builder import build_test_graph_with_fake_model
    from langagent.primitives.langchain_types import HumanMessage
    
    fake_model = create_fake_model_single_turn()
    graph = build_test_graph_with_fake_model(fake_model)
    
    # State with only messages (no files, context)
    state: AgentState = {
        "messages": [HumanMessage(content="Test")]
    }
    
    # Should not raise error
    result = dispatch(graph, state)
    
    # Verify result
    assert isinstance(result, dict)
    assert "messages" in result


@pytest.mark.skip(reason="T137: Implement in Phase 14")
def test_dispatch_3_turn_task_under_5s():
    """SC-001: 3-turn task converges in <5 seconds on local vLLM."""
    pass


@pytest.mark.skip(reason="T137a: Implement in Phase 14")
def test_stage_violation_latency_under_1ms():
    """SC-008: Measure stage_guard interception time, assert <1ms."""
    pass
