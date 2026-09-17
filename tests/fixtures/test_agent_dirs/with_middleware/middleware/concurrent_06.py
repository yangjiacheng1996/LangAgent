"""Concurrent middleware 06 for testing."""

MIDDLEWARE_SPEC = {
    "id": "concurrent_06",
    "priority": 350,
    "hook_points": ["on_chat_model_start"]
}


def concurrent_06_middleware(state, runtime):
    """Middleware 06 implementation."""
    return state
