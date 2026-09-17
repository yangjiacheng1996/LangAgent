"""Middleware A with same priority for testing tiebreaker."""

MIDDLEWARE_SPEC = {
    "id": "priority_a",
    "priority": 100,
    "hook_points": ["on_chat_model_start"]
}


def middleware_a(state, runtime):
    """Middleware A implementation."""
    return state
