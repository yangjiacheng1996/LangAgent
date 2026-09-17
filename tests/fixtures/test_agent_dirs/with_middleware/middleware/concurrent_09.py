"""Concurrent middleware 09 for testing."""

MIDDLEWARE_SPEC = {
    "id": "concurrent_09",
    "priority": 380,
    "hook_points": ["on_chat_model_start"]
}


def concurrent_09_middleware(state, runtime):
    """Middleware 09 implementation."""
    return state
