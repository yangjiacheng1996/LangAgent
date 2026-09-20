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
from langagent.protocol.skill_loader import load_all as load_skills, parse_frontmatter
from langagent.protocol.skill_schemas import (
    SkillFrontmatter,
    SkillFrontmatterParseError,
    SkillSpec,
    SEMVER_REGEX,
)
from langagent.protocol.tool_registry import register_all as register_tools, get_by_id
from langagent.protocol.tool_schemas import (
    ToolIdDuplicateError,
    ToolSpec,
    MINIMAL_JSON_SCHEMA,
)

__all__ = [
    # Event bus
    "Event",
    "EventBus",
    "SubscriptionToken",
    "UnknownEventTypeError",
    "EventDrainError",
    "ALLOWED_EVENT_TYPES",
    # Skill loader (F05)
    "load_skills",
    "parse_frontmatter",
    "SkillFrontmatter",
    "SkillFrontmatterParseError",
    "SkillSpec",
    "SEMVER_REGEX",
    # Tool registry (F05)
    "register_tools",
    "get_by_id",
    "ToolIdDuplicateError",
    "ToolSpec",
    "MINIMAL_JSON_SCHEMA",
]
