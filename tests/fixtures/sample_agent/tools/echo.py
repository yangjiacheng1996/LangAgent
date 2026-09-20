"""Echo tool for testing - returns input text."""

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class EchoInput(BaseModel):
    """Input schema for echo tool."""
    text: str = Field(description="Text to echo back")


class EchoTool(BaseTool):
    """A simple tool that echoes input text."""
    name: str = "echo"
    description: str = "Echoes input text back to the user"
    args_schema: type[BaseModel] = EchoInput
    
    def _run(self, text: str) -> str:
        """Execute the echo tool."""
        return text


# Export the tool instance with name matching filename
echo = EchoTool()
