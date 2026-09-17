"""Token counter middleware for testing."""

MIDDLEWARE_SPEC = {
    "id": "token_counter",
    "priority": 200,
    "hook_points": ["on_node_end"]
}


def token_counter_middleware(state, runtime):
    """Middleware implementation for token counting."""
    return state
