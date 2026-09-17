"""Concurrent middleware 08 for testing."""

MIDDLEWARE_SPEC = {
    "id": "concurrent_08",
    "priority": 370,
    "hook_points": ["on_chat_model_start"]
}


def concurrent_08_middleware(state, runtime):
    """Middleware 08 implementation."""
    return state
