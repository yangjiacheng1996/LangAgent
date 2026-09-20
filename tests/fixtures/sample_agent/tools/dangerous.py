"""Dangerous tool requiring approval."""

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


# Module-level constant indicating approval requirement
REQUIRES_APPROVAL = True


class DangerousInput(BaseModel):
    """Input schema for dangerous tool."""
    command: str = Field(description="Command to execute")


class DangerousTool(BaseTool):
    """A tool that requires approval before execution."""
    name: str = "dangerous"
    description: str = "Executes a potentially dangerous operation"
    args_schema: type[BaseModel] = DangerousInput
    
    def _run(self, command: str) -> str:
        """Execute the dangerous operation."""
        return f"Executed: {command}"


# Export the tool instance
dangerous = DangerousTool()
