"""Concurrent middleware 05 for testing."""

MIDDLEWARE_SPEC = {
    "id": "concurrent_05",
    "priority": 340,
    "hook_points": ["on_chat_model_start"]
}


def concurrent_05_middleware(state, runtime):
    """Middleware 05 implementation."""
    return state
