"""
MiddlewareSpec Pydantic model for middleware metadata.

This model validates middleware configuration from agent_dir/middleware/*.py files
per FR-018 and enforces valid hook_points against LangGraph protocol.
"""

from pydantic import BaseModel, Field, field_validator


class MiddlewareSpec(BaseModel, frozen=True):
    """
    Parsed middleware metadata. F01 owns this schema.
    
    Fields:
        id: Unique identifier (filename without .py)
        priority: Lower = earlier execution (0-1000)
        hook_points: LangGraph Runtime context hooks
    """
    
    id: str
    priority: int = Field(ge=0, le=1000)
    hook_points: list[str]
    
    @field_validator("hook_points")
    @classmethod
    def validate_hook_points(cls, v: list[str]) -> list[str]:
        """
        FR-018: Validate hook_points against exhaustive list of valid hook names.
        
        Valid hook names (7 total):
        - on_chat_model_start: Before chat model invocation
        - on_chat_model_end: After chat model completes
        - on_chat_model_stream: During streaming responses
        - on_tool_start: Before tool execution
        - on_tool_end: After tool execution
        - on_chain_start: Before LangChain chain starts
        - on_chain_end: After LangChain chain completes
        
        Args:
            v: List of hook point names
            
        Returns:
            Validated list of hook points
            
        Raises:
            ValueError: If any hook_points are invalid
        """
        allowed = [
            "on_chat_model_start",
            "on_chat_model_end",
            "on_chat_model_stream",
            "on_tool_start",
            "on_tool_end",
            "on_chain_start",
            "on_chain_end",
        ]
        invalid = [h for h in v if h not in allowed]
        if invalid:
            raise ValueError(f"Invalid hook_points: {invalid}. Allowed: {allowed}")
        return v


__all__ = ["MiddlewareSpec"]
