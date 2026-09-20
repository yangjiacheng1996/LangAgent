"""Safe tool without approval requirement."""

from langchain_core.tools import BaseTool


class SafeTool(BaseTool):
    """A safe tool that doesn't require approval."""
    name: str = "safe"
    description: str = "A safe operation that doesn't require approval"
    
    def _run(self) -> str:
        """Execute the safe operation."""
        return "Safe operation completed"


# Export the tool instance (no REQUIRES_APPROVAL constant)
safe = SafeTool()
