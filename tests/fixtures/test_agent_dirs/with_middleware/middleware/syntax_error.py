"""Middleware with syntax error for testing."""

MIDDLEWARE_SPEC = {
    "id": "syntax_error",
    "priority": 150,
    "hook_points": ["on_node_start"]
}


def syntax_error_middleware(state, runtime)
    """Missing colon causes syntax error."""
    return state
