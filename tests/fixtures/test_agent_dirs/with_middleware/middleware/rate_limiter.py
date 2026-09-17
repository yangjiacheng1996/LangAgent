"""Rate limiter middleware for testing."""

MIDDLEWARE_SPEC = {
    "id": "rate_limiter",
    "priority": 100,
    "hook_points": ["on_chat_model_start"]
}


def rate_limit_middleware(state, runtime):
    """Middleware implementation for rate limiting."""
    return state
