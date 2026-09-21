"""Minimal test agent."""
from typing import Any


def get_instructions() -> str:
    """Return agent instructions."""
    return "You are a helpful assistant."


def process_message(message: str) -> dict[str, Any]:
    """Process a message and return a response."""
    return {"role": "assistant", "content": f"Echo: {message}"}
