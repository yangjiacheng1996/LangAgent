"""Skill schemas and data models for protocol layer.

This module provides:
- SkillFrontmatter: Parsed YAML frontmatter from SKILL.md files
- SkillSpec: Complete skill specification with metadata
- SkillFrontmatterParseError: Exception for parsing errors
- SEMVER_REGEX: Validation pattern for semantic versioning
"""

import re
from dataclasses import dataclass


# T010: Add semver regex validation constant (^v\d+\.\d+\.\d+$)
SEMVER_REGEX = re.compile(r"^v\d+\.\d+\.\d+$")


# T005: Create custom exception classes (SkillFrontmatterParseError with exit_code=65)
class SkillFrontmatterParseError(Exception):
    """Raised when YAML frontmatter parsing fails or validation fails.
    
    Exit code 65 corresponds to EX_DATAERR in BSD sysexits.h convention.
    """
    
    def __init__(self, message: str, exit_code: int = 65):
        super().__init__(message)
        self.exit_code = exit_code


# T007: Define SkillFrontmatter dataclass (frozen) with fields
@dataclass(frozen=True)
class SkillFrontmatter:
    """Represents parsed YAML frontmatter from SKILL.md file.
    
    Only name, description, and version are required fields.
    Optional fields (author, tags, requires) have default values.
    """
    name: str  # Required
    description: str  # Required
    version: str  # Required, must match SEMVER_REGEX
    author: str | None = None  # Optional, defaults to None
    tags: list[str] | None = None  # Optional, defaults to empty list
    requires: list[str] | None = None  # Optional, defaults to empty list


# T008: Define SkillSpec dataclass (frozen) with all SkillFrontmatter fields + body_path, enabled
@dataclass(frozen=True)
class SkillSpec:
    """Represents a loaded skill with complete metadata.
    
    Includes all frontmatter fields plus body_path and enabled status.
    """
    name: str
    description: str
    version: str
    author: str | None
    tags: list[str]
    requires: list[str]
    body_path: str  # Absolute path to SKILL.md file
    enabled: bool = True  # Defaults to True (FR-015)


__all__ = [
    "SEMVER_REGEX",
    "SkillFrontmatterParseError",
    "SkillFrontmatter",
    "SkillSpec",
]
