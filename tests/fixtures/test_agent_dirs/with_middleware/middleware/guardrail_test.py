"""Guardrail middleware for testing."""

MIDDLEWARE_SPEC = {
    "id": "guardrail_test",
    "priority": 10,
    "hook_points": ["on_chat_model_start", "on_node_end"]
}


def guardrail_middleware(state, runtime):
    """Middleware implementation for guardrails."""
    return state
