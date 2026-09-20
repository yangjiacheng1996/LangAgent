"""Tool with import error for testing."""

from langchain_core.tools import BaseTool
import non_existent_module  # This will cause ImportError


class ImportErrorTool(BaseTool):
    """A tool that has import errors."""
    name: str = "import_error"
    description: str = "A tool with import error"
    
    def _run(self) -> str:
        """Execute the tool."""
        return "This won't work due to import error"


# Export the tool instance
import_error = ImportErrorTool()
