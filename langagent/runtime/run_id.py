"""Run ID generation utilities for LangAgent.

Generates unique run IDs for JSONL file naming and tracing.
"""

import uuid


def generate_run_id() -> str:
    """Generate unique run ID for this execution.
    
    Returns:
        UUID4 string (e.g., "550e8400-e29b-41d4-a716-446655440000")
    """
    return str(uuid.uuid4())
