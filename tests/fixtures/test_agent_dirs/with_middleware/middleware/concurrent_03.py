"""Concurrent middleware 03 for testing."""

MIDDLEWARE_SPEC = {
    "id": "concurrent_03",
    "priority": 320,
    "hook_points": ["on_chat_model_start"]
}


def concurrent_03_middleware(state, runtime):
    """Middleware 03 implementation."""
    return state
