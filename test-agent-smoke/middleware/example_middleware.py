"""Example middleware for the agent."""

from typing import Any, Callable


def example_middleware(next_handler: Callable) -> Callable:
    """Example middleware that wraps request handling.
    
    Args:
        next_handler: The next handler in the chain
        
    Returns:
        Wrapped handler function
    """
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Pre-processing
        print("Before processing")
        
        # Call next handler
        result = next_handler(*args, **kwargs)
        
        # Post-processing
        print("After processing")
        
        return result
    
    return wrapper
