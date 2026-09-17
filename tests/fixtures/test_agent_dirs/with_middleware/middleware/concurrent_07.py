"""Concurrent middleware 07 for testing."""

MIDDLEWARE_SPEC = {
    "id": "concurrent_07",
    "priority": 360,
    "hook_points": ["on_chat_model_start"]
}


def concurrent_07_middleware(state, runtime):
    """Middleware 07 implementation."""
    return state
