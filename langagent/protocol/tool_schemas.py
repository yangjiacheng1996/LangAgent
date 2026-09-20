"""Tool schemas and data models for protocol layer.

This module provides:
- ToolSpec: Complete tool specification with metadata
- ToolIdDuplicateError: Exception for duplicate tool_id detection
- MINIMAL_JSON_SCHEMA: Fallback JSON Schema Draft 7 when args_schema is None
"""

from pydantic import BaseModel


# T011: Add JSON Schema Draft 7 minimal fallback constant
MINIMAL_JSON_SCHEMA = {
    "type": "object",
    "properties": {},
    "$schema": "http://json-schema.org/draft-07/schema#"
}


# T006: Create custom exception classes (ToolIdDuplicateError with exit_code=70)
class ToolIdDuplicateError(Exception):
    """Raised when two tools have the same tool_id.
    
    Exit code 70 corresponds to EX_SOFTWARE in BSD sysexits.h convention.
    """
    
    def __init__(self, message: str, exit_code: int = 70):
        super().__init__(message)
        self.exit_code = exit_code


# T009: Define ToolSpec Pydantic BaseModel with fields
class ToolSpec(BaseModel):
    """Represents a registered tool with complete metadata.
    
    Fields:
    - tool_id: Tool identifier (filename without .py extension)
    - tool_name: Tool name (identical to tool_id for naming consistency)
    - description: Tool description from BaseTool.description
    - args_schema: JSON Schema Draft 7 dictionary
    - enabled: Tool enabled status (defaults to False - FR-016)
    - requires_approval: Whether tool requires approval before execution
    """
    tool_id: str
    tool_name: str  # Always equal to tool_id for naming consistency
    description: str
    args_schema: dict  # JSON Schema Draft 7
    enabled: bool = False  # Defaults to False (FR-016)
    requires_approval: bool = False  # Defaults to False


__all__ = [
    "MINIMAL_JSON_SCHEMA",
    "ToolIdDuplicateError",
    "ToolSpec",
]
