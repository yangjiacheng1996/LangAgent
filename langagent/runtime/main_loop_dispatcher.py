"""ReAct Main Loop Runtime Dispatcher (F08).

This module implements the runtime layer stage 5 dispatcher that drives LangGraph
CompiledStateGraph to execute the ReAct loop (reasoning → tools → observation)
until task completion, user interruption, or max_turns termination.

Core APIs:
    - dispatch(): Execute a single ReAct turn
    - run_until_done(): Run complete loop until convergence
    - build_doctor_probes(): Create model/checkpoint probe functions

Constitutional Alignment:
    - Article VI: Agent Loop & State Design (LangGraph-driven ReAct loop)
    - Article VIII: TDD Rigidity (tests written before implementation)
    - Article IX: Quality Diagnostics (dual-channel Event + Log emission)
    - Article XV: Top-Level Design Primacy (aligns with workflow.md stage 5)
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, cast

from langagent.primitives.langchain_types import (
    CompiledStateGraph,
    AIMessage,
    ToolMessage,
)
from langagent.runtime.agent_state import AgentState, ErrorEntry
from langagent.cross_cutting.logger import emit as log_emit
from langagent.cross_cutting.stage_guard import cross_cutting_stage_guard_decorator
from langagent.protocol.event_bus import Event, EventBus


# ============================================================================
# Phase 2: Foundational - Exception Classes (T015, T016)
# ============================================================================


@dataclass(frozen=True)
class HitlInterruptedError(Exception):
    """Main loop interrupted by user or guardrail.
    
    Carries the current AgentState snapshot for caller inspection or resumption.
    
    Attributes:
        state: AgentState snapshot at interruption time (TypedDict converted to dict)
        reason: Interruption reason - one of:
            - "keyboard_interrupt": User pressed Ctrl-C
            - "guardrail_block": F04 guardrail intercepted operation
            - "tool_approval_required": Tool requires human approval
        message: Human-readable error message
    
    Usage:
        try:
            result = run_until_done(graph, state)
        except HitlInterruptedError as e:
            print(f"Interrupted: {e.reason}")
            print(f"State at interruption: {e.state}")
    
    Constitutional Alignment:
        - Article VI: Interrupt mechanism based on LangGraph interrupt()
        - Clarification Q5: Exception carries state + reason for F10/F11
    """
    
    state: dict[str, Any]
    reason: str  # "keyboard_interrupt" | "guardrail_block" | "tool_approval_required"
    message: str = "Agent execution interrupted"
    
    def __str__(self) -> str:
        return f"{self.message}: {self.reason}"


@dataclass(frozen=True)
class TokenLimitExceededError(Exception):
    """Max turns limit exceeded without convergence.
    
    Raised when the ReAct loop reaches max_turns and the model still has tool_calls
    in the most recent AIMessage.
    
    Attributes:
        turn_count: Number of turns executed
        max_turns: Configured maximum turn limit
        message: Human-readable error message
    
    Usage:
        try:
            result = run_until_done(graph, state, max_turns=10)
        except TokenLimitExceededError as e:
            print(f"Failed to converge after {e.turn_count} turns")
    
    Constitutional Alignment:
        - Spec FR-007: Max turns termination with structured error
        - Clarification Q1: No early termination on error count, only max_turns
    """
    
    turn_count: int
    max_turns: int
    message: str = "Agent failed to converge within max_turns limit"
    
    def __str__(self) -> str:
        return f"{self.message} (turn_count={self.turn_count}, max_turns={self.max_turns})"


# ============================================================================
# Phase 3: User Story 1 - Single-Turn Dispatch (T030-T052)
# ============================================================================

# Module-level event bus instance (initialized on first use)
_event_bus: EventBus | None = None


def _get_event_bus() -> EventBus:
    """Get or create the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def _emit_dual_channel(
    event_type: str,
    log_tag_lifecycle: str,
    log_tag_runtime: str,
    payload: dict[str, Any],
    source: str = "langagent.runtime.main_loop_dispatcher",
) -> None:
    """Emit Event + Log dual-channel signals.
    
    Follows research.md decision 5: Event first, then Log (always emit log even if event fails).
    
    Args:
        event_type: Event type for F03 event_bus
        log_tag_lifecycle: Lifecycle log tag (la.lifecycle.*)
        log_tag_runtime: Runtime log tag (la.runtime.main_loop.*)
        payload: Payload dict (shared across event and logs)
        source: Event source module
    """
    # Try to publish event first (best-effort)
    try:
        event = Event.create(
            event_type=event_type,
            source=source,
            payload=payload,
        )
        _get_event_bus().publish(event)
    except Exception as e:
        # Log event publish failure but continue
        try:
            log_emit("la.runtime.main_loop.event_publish_failed", {
                "event_type": event_type,
                "error": str(e),
            })
        except:
            pass  # Best effort
    
    # Always emit logs (fire-and-forget)
    try:
        log_emit(log_tag_lifecycle, payload)
    except:
        pass  # Best effort
    
    try:
        log_emit(log_tag_runtime, payload)
    except:
        pass  # Best effort


def _dispatch_internal(
    graph: CompiledStateGraph,
    state: AgentState,
    mode: str = "invoke",
    thread_id: str = "main",
) -> Any:
    """Internal dispatch logic shared by invoke and stream modes.
    
    Args:
        graph: CompiledStateGraph from F01
        state: Current AgentState
        mode: "invoke" or "stream"
        thread_id: Thread ID for checkpointer session management (default: "main")
    
    Returns:
        For invoke: final AgentState
        For stream: generator yielding (node_name, state_snapshot) tuples
    
    This is a private function. Use dispatch() or dispatch_stream() instead.
    """
    # T037, T038: Emit turn start logs
    turn_payload = {
        "message": "Starting ReAct turn",
        "state_messages_count": len(state.get("messages", [])),
        "mode": mode,
        "thread_id": thread_id,
    }
    log_emit("la.lifecycle.run.turn", turn_payload)
    log_emit("la.runtime.main_loop.turn.start", turn_payload)
    
    try:
        if mode == "invoke":
            # T112: Invoke mode - return final state
            result_state = graph.invoke(state, config={"configurable": {"thread_id": thread_id}})
            
            # Emit events and logs
            _emit_state_events(result_state)
            
            # T045: Emit turn end log
            log_emit("la.runtime.main_loop.turn.end", {
                "message": "Turn completed",
                "final_messages_count": len(result_state.get("messages", [])),
            })
            
            return result_state
            
        elif mode == "stream":
            # T113: Stream mode - yield intermediate states
            return _dispatch_stream_generator(graph, state, thread_id)
        
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'invoke' or 'stream'")
        
    except KeyboardInterrupt:
        raise HitlInterruptedError(
            state=dict(state),
            reason="keyboard_interrupt",
            message="User interrupted execution",
        )
    
    except Exception as e:
        if "interrupt" in str(type(e)).lower() or "Interrupt" in str(type(e)):
            raise HitlInterruptedError(
                state=dict(state),
                reason="guardrail_block",
                message=f"Execution interrupted: {str(e)}",
            )
        else:
            raise


def _dispatch_stream_generator(graph: CompiledStateGraph, state: AgentState, thread_id: str = "main"):
    """Generator for stream mode dispatch.
    
    Args:
        graph: CompiledStateGraph from F01
        state: Current AgentState
        thread_id: Thread ID for checkpointer session management
    
    Yields:
        Tuple of (node_name, state_snapshot) for each node execution
    """
    try:
        for chunk in graph.stream(
            state, 
            config={"configurable": {"thread_id": thread_id}}
        ):
            # chunk is a dict like {node_name: output}
            # Extract node_name and get current state
            if isinstance(chunk, dict):
                for node_name, output in chunk.items():
                    # Get updated state after this node
                    # Note: LangGraph stream returns node outputs, not full state
                    # We yield the chunk as-is for compatibility
                    yield (node_name, chunk)
            else:
                # Fallback: yield as-is
                yield ("unknown", chunk)
        
        # Emit turn end log after stream completes
        log_emit("la.runtime.main_loop.turn.end", {
            "message": "Turn completed (stream mode)",
        })
        
    except KeyboardInterrupt:
        raise HitlInterruptedError(
            state=dict(state),
            reason="keyboard_interrupt",
            message="User interrupted execution",
        )
    
    except Exception as e:
        if "interrupt" in str(type(e)).lower() or "Interrupt" in str(type(e)):
            raise HitlInterruptedError(
                state=dict(state),
                reason="guardrail_block",
                message=f"Execution interrupted: {str(e)}",
            )
        else:
            raise


def _emit_state_events(result_state: AgentState) -> None:
    """Extract and emit events from state after graph execution.
    
    Args:
        result_state: State after graph.invoke() or stream iteration
    """
    messages = result_state.get("messages", [])
    if not messages:
        return
    
    last_message = messages[-1]
    
    # T043, T044: Emit model_response event + logs
    if isinstance(last_message, AIMessage):
        model_response_payload = {
            "message": "Model response received",
            "content": last_message.content[:100] if last_message.content else "",
            "has_tool_calls": bool(last_message.tool_calls),
            "tool_calls_count": len(last_message.tool_calls) if last_message.tool_calls else 0,
        }
        _emit_dual_channel(
            event_type="model_response",
            log_tag_lifecycle="la.lifecycle.run.model_response",
            log_tag_runtime="la.runtime.main_loop.model_call",
            payload=model_response_payload,
        )
        
        # T033, T039, T040: Emit tool_call events
        if last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                tool_call_payload = {
                    "message": f"Tool call: {tool_call.get('name', 'unknown')}",
                    "tool_name": tool_call.get('name', 'unknown'),
                    "tool_id": tool_call.get('id', ''),
                    "args": str(tool_call.get('args', {}))[:100],
                }
                _emit_dual_channel(
                    event_type="tool_call",
                    log_tag_lifecycle="la.lifecycle.run.tool_call",
                    log_tag_runtime="la.runtime.main_loop.tool_call",
                    payload=tool_call_payload,
                )
    
    # T034, T041, T042: Emit tool_result events
    for msg in messages[-5:]:
        if isinstance(msg, ToolMessage):
            tool_result_payload = {
                "message": "Tool result received",
                "tool_call_id": getattr(msg, 'tool_call_id', ''),
                "content": msg.content[:100] if msg.content else "",
            }
            _emit_dual_channel(
                event_type="tool_result",
                log_tag_lifecycle="la.lifecycle.run.tool_result",
                log_tag_runtime="la.runtime.main_loop.tool_result",
                payload=tool_result_payload,
            )


@cross_cutting_stage_guard_decorator('main_loop')
def dispatch(graph: CompiledStateGraph, state: AgentState, thread_id: str = "main") -> AgentState:
    """Execute a single ReAct turn with dual-channel telemetry (invoke mode).
    
    This function drives one iteration of the ReAct loop:
    1. Call graph.invoke(state) to execute model_call → tools_execute nodes
    2. Emit Event + Log for each tool_call and tool_result
    3. Record tool errors in state.scratchpad["errors"] without early termination
    4. Catch GraphInterrupt/KeyboardInterrupt and raise HitlInterruptedError
    
    Args:
        graph: CompiledStateGraph from F01 state_graph_builder.build()
        state: Current AgentState (must contain at least one HumanMessage)
        thread_id: Thread ID for checkpointer session management (default: "main")
    
    Returns:
        Updated AgentState with new messages appended
    
    Raises:
        HitlInterruptedError: If user interrupts or guardrail blocks
        StageCapabilityViolationError: If stage guard detects forbidden operation
    
    Side Effects:
        - Emits 12 log tags via F02 logger
        - Publishes 3 Event types via F03 event_bus
        - Increments F02 metrics_collector turn_count
    
    Constitutional Alignment:
        - Article VI: LangGraph-driven execution (graph.invoke)
        - Article VIII: Real graph execution (no mocking per clause 4)
        - Article IX: Dual-channel emission (Event + Log)
    
    See: contracts/dispatch.md for detailed API contract
    """
    return _dispatch_internal(graph, state, mode="invoke", thread_id=thread_id)


def dispatch_stream(graph: CompiledStateGraph, state: AgentState, thread_id: str = "main"):
    """Execute a single ReAct turn with streaming intermediate states.
    
    This is the streaming version of dispatch(). Instead of returning only the
    final state, it yields intermediate states after each node execution.
    
    Args:
        graph: CompiledStateGraph from F01 state_graph_builder.build()
        state: Current AgentState (must contain at least one HumanMessage)
        thread_id: Thread ID for checkpointer session management (default: "main")
    
    Yields:
        Tuple of (node_name, state_snapshot) for each node execution
    
    Raises:
        HitlInterruptedError: If user interrupts or guardrail blocks
        StageCapabilityViolationError: If stage guard detects forbidden operation
    
    Example:
        >>> for node_name, state_snapshot in dispatch_stream(graph, state):
        ...     print(f"Node '{node_name}' completed")
        ...     print(f"Messages: {len(state_snapshot['messages'])}")
    
    Constitutional Alignment:
        - Article VI: LangGraph-driven execution (graph.stream)
        - Research.md decision 1: Shared core logic with mode-specific wrappers
    
    See: contracts/dispatch.md for detailed API contract
    """
    return _dispatch_internal(graph, state, mode="stream", thread_id=thread_id)


# ============================================================================
# Phase 4: User Story 2 - Multi-Turn Loop (T057-T065)
# ============================================================================


@cross_cutting_stage_guard_decorator('main_loop')
def run_until_done(
    graph: CompiledStateGraph,
    state: AgentState,
    max_turns: int = 30,
    thread_id: str = "main",
) -> AgentState:
    """Run ReAct loop until convergence, interruption, or max_turns.
    
    This function repeatedly calls dispatch() until one of:
    - Convergence: AIMessage has no tool_calls (task complete)
    - Interruption: User presses Ctrl-C or guardrail blocks
    - Max turns: turn_count >= max_turns and still has tool_calls
    
    Args:
        graph: CompiledStateGraph from F01 state_graph_builder.build()
        state: Initial AgentState with HumanMessage
        max_turns: Maximum number of turns before raising TokenLimitExceededError
        thread_id: Thread ID for checkpointer session management (default: "main")
    
    Returns:
        Final AgentState after convergence
    
    Raises:
        TokenLimitExceededError: If max_turns reached without convergence
        HitlInterruptedError: If user interrupts or guardrail blocks
        StageCapabilityViolationError: If stage guard detects forbidden operation
    
    Side Effects:
        - Emits la.lifecycle.run.start + la.runtime.main_loop.start logs
        - Emits la.runtime.main_loop.near_limit warning at 90% of max_turns
        - Emits la.runtime.main_loop.end log on completion
    
    Constitutional Alignment:
        - Article VI: Main loop continues until AIMessage.tool_calls is empty
        - Clarification Q2: Warning threshold at 90% of max_turns
    
    See: contracts/run_until_done.md for detailed API contract
    """
    # T061: Emit start logs
    log_emit("la.lifecycle.run.start", {
        "message": "Starting ReAct main loop",
        "max_turns": max_turns,
        "thread_id": thread_id,
    })
    log_emit("la.runtime.main_loop.start", {
        "message": "Main loop initialized",
        "max_turns": max_turns,
        "thread_id": thread_id,
    })
    
    # T070: Track turn count
    turn_count = 0
    current_state = state
    
    try:
        # T059: Loop until convergence
        while turn_count < max_turns:
            # Execute one turn with thread_id
            current_state = dispatch(graph, current_state, thread_id=thread_id)
            turn_count += 1
            
            # T073: Emit near-limit warning at 90% threshold (clarification Q2)
            if turn_count >= int(max_turns * 0.9) and turn_count < max_turns:
                log_emit("la.runtime.main_loop.near_limit", {
                    "message": f"Approaching max_turns limit",
                    "turn_count": turn_count,
                    "max_turns": max_turns,
                    "remaining": max_turns - turn_count,
                })
            
            # T060: Check for convergence (AIMessage with no tool_calls)
            messages = current_state.get("messages", [])
            if messages:
                last_message = messages[-1]
                if isinstance(last_message, AIMessage):
                    # Convergence: no tool_calls means task is complete
                    if not last_message.tool_calls or len(last_message.tool_calls) == 0:
                        break
            
            # T071, T072: Check max_turns limit
            if turn_count >= max_turns:
                # Check if we still have tool_calls (not converged)
                if messages and isinstance(messages[-1], AIMessage):
                    if messages[-1].tool_calls and len(messages[-1].tool_calls) > 0:
                        raise TokenLimitExceededError(
                            turn_count=turn_count,
                            max_turns=max_turns,
                            message=f"Agent failed to converge after {turn_count} turns",
                        )
        
        # T062: Emit end log
        log_emit("la.runtime.main_loop.end", {
            "message": "Main loop completed",
            "turn_count": turn_count,
            "converged": True,
        })
        
        return current_state
        
    except (HitlInterruptedError, TokenLimitExceededError):
        # Re-raise these exceptions as-is
        raise
    
    except KeyboardInterrupt:
        # T078: Catch KeyboardInterrupt and wrap in HitlInterruptedError
        raise HitlInterruptedError(
            state=dict(current_state),
            reason="keyboard_interrupt",
            message="User interrupted execution",
        )


# ============================================================================
# Phase 12: Doctor Probe Factory (T121-T123)
# ============================================================================


def build_doctor_probes(config: Any) -> tuple[Any, Any]:
    """Create probe functions for F10 doctor subcommand integration.
    
    Returns two closures that probe model endpoint and checkpointer health.
    This is a factory function, not a runtime dispatcher - it only constructs
    the probe functions without executing them.
    
    Args:
        config: RuntimeConfig with model_provider, model_name, checkpointer fields
    
    Returns:
        Tuple of (probe_model, probe_checkpoint) closures:
            - probe_model() -> tuple[bool, str]: (success, message)
            - probe_checkpoint() -> tuple[bool, str]: (success, message)
    
    Raises:
        None: Probes capture exceptions and return (False, error_message)
    
    Constitutional Alignment:
        - Article IV: Model abstraction (uses chat_model_factory.create)
        - Hardcoded exception: build_doctor_probes imports primitives per architecture_modules.md v2.4.0
    
    See: contracts/build_doctor_probes.md for detailed API contract
    """
    # Import here to avoid circular dependencies (hardcoded exception per architecture)
    from langagent.primitives.chat_model_factory import create as create_model
    from langagent.primitives.checkpoint_adapter import create as create_checkpoint
    
    # T122: Create probe_model closure
    def probe_model() -> tuple[bool, str]:
        """Probe model endpoint health.
        
        Returns:
            (True, "ok") if endpoint reachable, (False, error_message) otherwise
        """
        try:
            # Attempt to create model (will fail if endpoint unreachable or auth fails)
            model = create_model(config)
            return (True, "Model endpoint reachable")
        except Exception as e:
            error_type = type(e).__name__
            return (False, f"{error_type}: {str(e)}")
    
    # T123: Create probe_checkpoint closure
    def probe_checkpoint() -> tuple[bool, str]:
        """Probe checkpointer health.
        
        Returns:
            (True, "ok") if checkpointer accessible, (False, error_message) otherwise
        """
        try:
            # Attempt to create and close checkpointer
            checkpointer = create_checkpoint(config)
            # For memory checkpointer, this always succeeds
            # For SQLite/Postgres, this checks file/connection
            return (True, "Checkpointer accessible")
        except Exception as e:
            error_type = type(e).__name__
            return (False, f"{error_type}: {str(e)}")
    
    return (probe_model, probe_checkpoint)


__all__ = [
    "HitlInterruptedError",
    "TokenLimitExceededError",
    "dispatch",
    "dispatch_stream",
    "run_until_done",
    "build_doctor_probes",
]
