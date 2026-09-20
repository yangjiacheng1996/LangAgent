"""Test helper for generating unique run IDs.

Provides utilities for:
- Generating consistent test run IDs
- Mocking run ID generation in tests
"""

import uuid


def generate_test_run_id(prefix: str = "test") -> str:
    """Generate deterministic run ID for tests.
    
    Args:
        prefix: Optional prefix for the run ID
        
    Returns:
        Run ID string (UUID4 format)
    """
    return f"{prefix}-{uuid.uuid4()}"


def mock_run_id() -> str:
    """Generate a fixed run ID for mocking.
    
    Returns:
        Fixed UUID string for predictable tests
    """
    return "550e8400-e29b-41d4-a716-446655440000"
