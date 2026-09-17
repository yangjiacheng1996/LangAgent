"""Concurrent middleware 01 for testing."""

MIDDLEWARE_SPEC = {
    "id": "concurrent_01",
    "priority": 300,
    "hook_points": ["on_chat_model_start"]
}


def concurrent_01_middleware(state, runtime):
    """Middleware 01 implementation."""
    return state
