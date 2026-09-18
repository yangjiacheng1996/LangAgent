"""
Event bus implementation for cross-module communication.

This module provides a publish/subscribe event bus that enables loose coupling
between runtime modules (publishers) and cross-cutting concerns (subscribers).
"""

import asyncio
import concurrent.futures
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, NewType, Any

from langagent.protocol.event_types import ALLOWED_EVENT_TYPES


# Type aliases
SubscriptionToken = NewType("SubscriptionToken", int)


# Exception classes
class UnknownEventTypeError(ValueError):
    """Raised when publishing an event type not in whitelist."""
    pass


class EventDrainError(RuntimeError):
    """Raised when event buffer drainage fails."""
    pass


# Event entity
@dataclass(frozen=True)
class Event:
    """
    Immutable record of a single system occurrence.
    
    Events represent significant occurrences in the system such as tool calls,
    model responses, guardrail blocks, etc. Each event has a unique ID, type,
    timestamp, source module, payload data, and optional trace ID.
    """
    event_id: str
    event_type: str
    emitted_at: str  # ISO 8601 UTC timestamp with 'Z' suffix
    source: str
    payload: dict
    trace_id: str
    
    @classmethod
    def create(
        cls,
        event_type: str,
        source: str,
        payload: dict,
        trace_id: str = "-"
    ) -> "Event":
        """
        Factory method to create an Event with auto-generated ID and timestamp.
        
        Args:
            event_type: Type of event (must be in ALLOWED_EVENT_TYPES)
            source: Module identifier (dot-separated, e.g., "langagent.runtime.main_loop")
            payload: JSON-serializable dict containing event data
            trace_id: Optional trace ID for distributed tracing (defaults to "-")
            
        Returns:
            New Event instance with generated event_id and emitted_at
        """
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            emitted_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            source=source,
            payload=payload,
            trace_id=trace_id
        )


# EventBus class
class EventBus:
    """
    Thread-safe publish/subscribe event bus for cross-module communication.
    
    The EventBus provides:
    - Synchronous and asynchronous event publication
    - FIFO-ordered handler execution
    - Error isolation (handler exceptions don't propagate)
    - Thread-safe subscription management
    - Graceful shutdown via flush()
    - Event drainage for persistence
    """
    
    def __init__(self) -> None:
        """Initialize the event bus with empty state."""
        self._lock = threading.RLock()
        self._subscribers: dict[str, list[tuple[SubscriptionToken, Callable[[Event], None]]]] = {}
        self._token_map: dict[SubscriptionToken, tuple[str, Callable[[Event], None]]] = {}
        self._event_buffer: list[Event] = []
        self._next_token_id = 0
        self._error_count = 0
        self._pending_futures: list[concurrent.futures.Future[Any]] = []
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
    
    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> SubscriptionToken:
        """
        Subscribe a handler to receive events of a specific type.
        
        Args:
            event_type: The type of event to subscribe to
            handler: Callable that accepts an Event and returns None
            
        Returns:
            SubscriptionToken that can be used to unsubscribe
        """
        with self._lock:
            token = SubscriptionToken(self._next_token_id)
            self._next_token_id += 1
            
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            
            self._subscribers[event_type].append((token, handler))
            self._token_map[token] = (event_type, handler)
            
            return token
    
    def unsubscribe(self, token: SubscriptionToken) -> None:
        """
        Unsubscribe a handler using its subscription token.
        
        Args:
            token: The subscription token returned by subscribe()
        """
        with self._lock:
            if token not in self._token_map:
                return  # Idempotent: already unsubscribed
            
            event_type, handler = self._token_map.pop(token)
            self._subscribers[event_type] = [
                (t, h) for t, h in self._subscribers[event_type] if t != token
            ]
    
    def publish(self, event: Event) -> None:
        """
        Publish an event synchronously to all registered handlers.
        
        Handlers are executed in FIFO order (registration order).
        Handler exceptions are caught and logged, but do not propagate.
        
        Args:
            event: The event to publish
            
        Raises:
            UnknownEventTypeError: If event type is not in ALLOWED_EVENT_TYPES
        """
        # Validate event type
        if event.event_type not in ALLOWED_EVENT_TYPES:
            raise UnknownEventTypeError(
                f"Event type '{event.event_type}' not in whitelist. "
                f"Allowed types: {sorted(ALLOWED_EVENT_TYPES)}"
            )
        
        # Get snapshot of handlers
        with self._lock:
            handlers = self._subscribers.get(event.event_type, []).copy()
        
        # Execute handlers outside lock (for concurrency)
        for token, handler in handlers:
            future = self._executor.submit(self._execute_handler, handler, event, token)
            with self._lock:
                self._pending_futures.append(future)
        
        # Append to buffer
        with self._lock:
            self._event_buffer.append(event)
    
    def _execute_handler(self, handler: Callable[[Event], None], event: Event, token: SubscriptionToken) -> None:
        """Execute a handler and log any exceptions."""
        try:
            handler(event)
        except Exception as e:
            self._log_handler_error(e, token)
    
    def _log_handler_error(self, exception: Exception, token: SubscriptionToken) -> None:
        """Log handler error via F02 emit()."""
        try:
            from langagent.cross_cutting.logger import emit
            emit(
                tag="la.cross_cutting.event_handler_error",
                payload={
                    "message": f"Handler {token} raised {type(exception).__name__}: {exception}",
                    "token": int(token),
                    "exception_type": type(exception).__name__,
                    "exception_message": str(exception),
                }
            )
        except ImportError:
            # F02 logger not available yet - fail silently for now
            pass
        
        # Increment error counter
        with self._lock:
            self._error_count += 1
    
    async def publish_async(self, event: Event) -> None:
        """
        Publish an event asynchronously to all registered handlers.
        
        Async handlers run concurrently via asyncio.gather.
        Sync handlers are wrapped with asyncio.to_thread.
        Handler exceptions are isolated (return_exceptions=True).
        
        Args:
            event: The event to publish
            
        Raises:
            UnknownEventTypeError: If event type is not in ALLOWED_EVENT_TYPES
        """
        # Validate event type
        if event.event_type not in ALLOWED_EVENT_TYPES:
            raise UnknownEventTypeError(
                f"Event type '{event.event_type}' not in whitelist. "
                f"Allowed types: {sorted(ALLOWED_EVENT_TYPES)}"
            )
        
        # Get snapshot of handlers
        with self._lock:
            handlers = self._subscribers.get(event.event_type, []).copy()
        
        # Build tasks
        tasks = []
        for token, handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                tasks.append(self._execute_async_handler(handler, event, token))
            else:
                tasks.append(self._execute_sync_handler_async(handler, event, token))
        
        # Execute with error isolation
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log exceptions without re-raising
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    token, _ = handlers[i]
                    self._log_handler_error(result, token)
        
        # Append to buffer
        with self._lock:
            self._event_buffer.append(event)
    
    async def _execute_async_handler(self, handler: Callable[[Event], None], event: Event, token: SubscriptionToken) -> None:
        """Execute an async handler."""
        await handler(event)
    
    async def _execute_sync_handler_async(self, handler: Callable[[Event], None], event: Event, token: SubscriptionToken) -> None:
        """Execute a sync handler in a thread pool."""
        await asyncio.to_thread(handler, event)
    
    def flush(self, timeout: float = 5.0) -> None:
        """
        Wait for all pending handlers to complete.
        
        Args:
            timeout: Maximum time to wait in seconds (default: 5.0)
        """
        with self._lock:
            futures_snapshot = self._pending_futures.copy()
        
        if not futures_snapshot:
            return  # No pending handlers
        
        done, not_done = concurrent.futures.wait(
            futures_snapshot,
            timeout=timeout,
            return_when=concurrent.futures.ALL_COMPLETED
        )
        
        if not_done:
            # Log timeout but don't raise exception
            try:
                from langagent.cross_cutting.logger import emit
                emit(
                    tag="la.cross_cutting.event_handler_error",
                    payload={
                        "message": f"flush() timeout: {len(not_done)} handlers still running"
                    }
                )
            except ImportError:
                # F02 logger not available yet
                pass
    
    def drain_events(self) -> list[Event]:
        """
        Drain all accumulated events from the buffer.
        
        This atomically reads and clears the event buffer.
        Subsequent calls return empty list until new events are published.
        
        Returns:
            List of all events accumulated since last drain
            
        Raises:
            EventDrainError: If buffer drainage fails
        """
        try:
            with self._lock:
                snapshot = self._event_buffer.copy()
                self._event_buffer.clear()
            return snapshot
        except Exception as e:
            # Do NOT clear buffer on failure (allow retry)
            raise EventDrainError(f"Failed to drain event buffer: {e}") from e
