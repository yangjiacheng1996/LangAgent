"""
Protocol layer: Event bus and event types for cross-module communication.

This module provides the publish/subscribe event bus infrastructure for
LangAgent's protocol layer, enabling loose coupling between runtime modules
and cross-cutting concerns.
"""

from langagent.protocol.event_bus import (
    Event,
    EventBus,
    SubscriptionToken,
    UnknownEventTypeError,
    EventDrainError,
)
from langagent.protocol.event_types import ALLOWED_EVENT_TYPES

__all__ = [
    "Event",
    "EventBus",
    "SubscriptionToken",
    "UnknownEventTypeError",
    "EventDrainError",
    "ALLOWED_EVENT_TYPES",
]
