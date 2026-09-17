"""PII filter middleware for testing."""

MIDDLEWARE_SPEC = {
    "id": "pii_filter",
    "priority": 50,
    "hook_points": ["on_state_update"]
}


def pii_filter_middleware(state, runtime):
    """Middleware implementation for PII filtering."""
    return state
