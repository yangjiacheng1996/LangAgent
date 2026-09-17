"""Concurrent middleware 02 for testing."""

MIDDLEWARE_SPEC = {
    "id": "concurrent_02",
    "priority": 310,
    "hook_points": ["on_chat_model_start"]
}


def concurrent_02_middleware(state, runtime):
    """Middleware 02 implementation."""
    return state
