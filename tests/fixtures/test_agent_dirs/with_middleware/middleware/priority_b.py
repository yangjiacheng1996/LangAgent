"""Middleware B with same priority for testing tiebreaker."""

MIDDLEWARE_SPEC = {
    "id": "priority_b",
    "priority": 100,
    "hook_points": ["on_chat_model_start"]
}


def middleware_b(state, runtime):
    """Middleware B implementation."""
    return state
