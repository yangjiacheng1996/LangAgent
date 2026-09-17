"""Fake chat model implementations for testing."""

from typing import Any, Optional, List
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class FakeChatModel(BaseChatModel):
    """Fake chat model for testing that returns configurable responses."""
    
    responses: List[str] = ["Test response"]
    current_index: int = 0
    
    def __init__(self, responses: Optional[List[str]] = None, **kwargs):
        super().__init__(**kwargs)
        if responses:
            self.responses = responses
        self.current_index = 0
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a fake response."""
        response = self.responses[self.current_index % len(self.responses)]
        self.current_index += 1
        
        message = AIMessage(content=response)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])
    
    @property
    def _llm_type(self) -> str:
        """Return type of chat model."""
        return "fake"
