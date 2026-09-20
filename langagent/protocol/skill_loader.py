"""Skill loader for protocol layer.

This module provides:
- load_all(): Load all skills from an agent directory's skills/ subdirectory
- parse_frontmatter(): Parse YAML frontmatter from SKILL.md files with validation
"""

import os
import re
from typing import Optional

import yaml

from langagent.cross_cutting import logger
from langagent.protocol.event_bus import EventBus
from langagent.protocol.skill_schemas import (
    SEMVER_REGEX,
    SkillFrontmatter,
    SkillFrontmatterParseError,
    SkillSpec,
)


# Initialize event bus
event_bus = EventBus()


def parse_frontmatter(md_path: str) -> SkillFrontmatter:
    """Parse YAML frontmatter from SKILL.md file.
    
    Args:
        md_path: Absolute path to SKILL.md file
        
    Returns:
        SkillFrontmatter object with parsed fields
        
    Raises:
        SkillFrontmatterParseError: If YAML is invalid or required fields missing
            - Exit code 65 (EX_DATAERR) for missing name/description/version
            - Exit code 65 for invalid semver format
    """
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract YAML frontmatter between --- markers
        if not content.startswith('---'):
            raise SkillFrontmatterParseError(
                f"Missing YAML frontmatter in {md_path}",
                exit_code=65
            )
        
        # Find the end of frontmatter
        end_marker = content.find('\n---\n', 3)
        if end_marker == -1:
            raise SkillFrontmatterParseError(
                f"Malformed YAML frontmatter (missing closing ---) in {md_path}",
                exit_code=65
            )
        
        yaml_content = content[4:end_marker]  # Skip opening ---\n
        
        # Parse YAML
        try:
            frontmatter_dict = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise SkillFrontmatterParseError(
                f"Invalid YAML syntax in {md_path}: {e}",
                exit_code=65
            )
        
        if not isinstance(frontmatter_dict, dict):
            raise SkillFrontmatterParseError(
                f"YAML frontmatter must be a dictionary in {md_path}",
                exit_code=65
            )
        
        # Validate required fields
        required_fields = ['name', 'description', 'version']
        for field in required_fields:
            if field not in frontmatter_dict:
                raise SkillFrontmatterParseError(
                    f"Missing required field '{field}' in {md_path}",
                    exit_code=65
                )
        
        # Validate semver format
        version = frontmatter_dict['version']
        if not SEMVER_REGEX.match(version):
            raise SkillFrontmatterParseError(
                f"Invalid semver format '{version}' in {md_path}. Expected format: vX.Y.Z",
                exit_code=65
            )
        
        # Extract fields with defaults for optional fields
        return SkillFrontmatter(
            name=frontmatter_dict['name'],
            description=frontmatter_dict['description'],
            version=version,
            author=frontmatter_dict.get('author'),
            tags=frontmatter_dict.get('tags', []),
            requires=frontmatter_dict.get('requires', [])
        )
        
    except SkillFrontmatterParseError:
        raise
    except Exception as e:
        raise SkillFrontmatterParseError(
            f"Failed to parse {md_path}: {e}",
            exit_code=65
        )


def load_all(skills_dir: str) -> list[SkillSpec]:
    """Load all skills from skills_dir.
    
    Args:
        skills_dir: Absolute path to agent directory's skills/ subdirectory
    
    Returns:
        List of SkillSpec objects for successfully loaded skills
        
    Side Effects:
        - Publishes skill_loaded event for each success
        - Publishes skill_load_failed event for each failure
        - Logs to la.runtime.skill_load_failed for failures
        
    Errors:
        Does not raise exceptions for individual skill failures (fail-soft).
        Returns empty list if skills_dir does not exist.
    """
    if not os.path.exists(skills_dir):
        return []
    
    if not os.path.isdir(skills_dir):
        return []
    
    loaded_skills = []
    
    # Scan for skill subdirectories
    try:
        entries = os.listdir(skills_dir)
    except OSError as e:
        logger.emit(
            tag="la.runtime.skill_load_failed",
            payload={"error": f"Failed to list skills directory {skills_dir}: {e}"}
        )
        return []
    
    for entry in sorted(entries):
        skill_subdir = os.path.join(skills_dir, entry)
        
        if not os.path.isdir(skill_subdir):
            continue
        
        skill_md_path = os.path.join(skill_subdir, "SKILL.md")
        
        if not os.path.exists(skill_md_path):
            continue
        
        try:
            # Parse frontmatter
            frontmatter = parse_frontmatter(skill_md_path)
            
            # Create SkillSpec
            skill_spec = SkillSpec(
                name=frontmatter.name,
                description=frontmatter.description,
                version=frontmatter.version,
                author=frontmatter.author,
                tags=frontmatter.tags if frontmatter.tags else [],
                requires=frontmatter.requires if frontmatter.requires else [],
                body_path=os.path.abspath(skill_md_path),
                enabled=True
            )
            
            loaded_skills.append(skill_spec)
            
            # Publish skill_loaded event
            try:
                event_bus.publish(
                    event_type="skill_loaded",
                    source="protocol_skill_loader",
                    payload={
                        "skill_name": skill_spec.name,
                        "version": skill_spec.version,
                        "body_path": skill_spec.body_path
                    }
                )
            except Exception as e:
                # Don't fail if event bus is unavailable
                pass  # Silently ignore event bus errors
        
        except SkillFrontmatterParseError as e:
            # Fail-soft: log error and continue
            logger.emit(
                tag="la.runtime.skill_load_failed",
                payload={
                    "path": skill_md_path,
                    "error": str(e),
                    "exit_code": e.exit_code
                }
            )
            
            # Publish skill_load_failed event
            try:
                event_bus.publish(
                    event_type="skill_load_failed",
                    source="protocol_skill_loader",
                    payload={
                        "path": skill_md_path,
                        "error": str(e),
                        "exit_code": e.exit_code
                    }
                )
            except Exception as pub_error:
                # Don't fail if event bus is unavailable
                pass  # Silently ignore event bus errors
        
        except Exception as e:
            # Catch all other exceptions (unexpected errors)
            logger.emit(
                tag="la.runtime.skill_load_failed",
                payload={
                    "path": skill_md_path,
                    "error": str(e)
                }
            )
            
            # Publish skill_load_failed event
            try:
                event_bus.publish(
                    event_type="skill_load_failed",
                    source="protocol_skill_loader",
                    payload={
                        "path": skill_md_path,
                        "error": str(e)
                    }
                )
            except Exception as pub_error:
                pass  # Silently ignore event bus errors
    
    return loaded_skills


__all__ = [
    "load_all",
    "parse_frontmatter",
]
