"""Concurrent middleware 04 for testing."""

MIDDLEWARE_SPEC = {
    "id": "concurrent_04",
    "priority": 330,
    "hook_points": ["on_chat_model_start"]
}


def concurrent_04_middleware(state, runtime):
    """Middleware 04 implementation."""
    return state
