"""
Event type whitelist for the protocol event bus.

This module defines all allowed event types that can be published through
the event bus. Event types must be registered here to be valid.
"""

ALLOWED_EVENT_TYPES: frozenset[str] = frozenset({
    # Runtime events (F08 main loop)
    "tool_call",          # Model invokes a tool
    "tool_result",        # Tool execution returns result
    "model_response",     # Model returns AIMessage
    
    # Guardrail events (F04)
    "guardrail_block",    # Guardrail intercepted request/response
    
    # Skill/tool lifecycle (F05)
    "skill_loaded",       # Skill loaded successfully
    "skill_load_failed",  # Skill loading failed
    "tool_registered",    # Tool registered in tool registry
    "tool_load_failed",   # Tool loading failed
    
    # Graph events (F01)
    "graph_composed",     # LangGraph compiled successfully
    
    # Eval events (F11)
    "eval_task_started",  # Eval task begins
    "eval_task_done",     # Eval task completes
    
    # Observability events (F02/F04)
    "audit_written",      # Audit entry persisted
    "metrics_snapshot",   # Metrics snapshot generated
    
    # Error events (F03)
    "event_handler_error", # Handler raised exception
})
