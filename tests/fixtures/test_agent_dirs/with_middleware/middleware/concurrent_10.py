"""Concurrent middleware 10 for testing."""

MIDDLEWARE_SPEC = {
    "id": "concurrent_10",
    "priority": 390,
    "hook_points": ["on_chat_model_start"]
}


def concurrent_10_middleware(state, runtime):
    """Middleware 10 implementation."""
    return state
