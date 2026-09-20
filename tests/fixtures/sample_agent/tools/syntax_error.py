"""Tool with intentional syntax error for testing."""

from langchain_core.tools import BaseTool

# Intentional syntax error - unclosed bracket
class BrokenTool(BaseTool):
    name: str = "syntax_error"
    description: str = "A tool with syntax error"
    
    def _run(self) -> str:
        return "This won't work"
    
syntax_error = BrokenTool(
