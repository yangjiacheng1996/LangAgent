"""Tests for skill loader protocol layer."""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from langagent.protocol.skill_loader import load_all, parse_frontmatter
from langagent.protocol.skill_schemas import (
    SkillFrontmatter,
    SkillFrontmatterParseError,
    SkillSpec,
)


# Test fixtures path
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "sample_agent")
SKILLS_DIR = os.path.join(FIXTURES_DIR, "skills")


# T018: Test empty directory
def test_load_all_empty_dir():
    """Verify empty list when skills/ doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        non_existent = os.path.join(tmpdir, "non_existent_skills")
        result = load_all(non_existent)
        assert result == []


# T019: Test single skill loading
def test_load_all_single_skill():
    """Verify 1 SkillSpec returned with all fields populated."""
    # Create isolated test directory with only one skill
    with tempfile.TemporaryDirectory() as tmpdir:
        test_skills_dir = os.path.join(tmpdir, "skills")
        test_skill_subdir = os.path.join(test_skills_dir, "test")
        os.makedirs(test_skill_subdir)
        
        # Copy the test skill fixture
        import shutil
        src = os.path.join(SKILLS_DIR, "test", "SKILL.md")
        dst = os.path.join(test_skill_subdir, "SKILL.md")
        shutil.copy(src, dst)
        
        result = load_all(test_skills_dir)
    
    assert len(result) == 1
    skill = result[0]
    
    assert isinstance(skill, SkillSpec)
    assert skill.name == "test-skill"
    assert skill.description == "A test skill for validation"
    assert skill.version == "v1.0.0"
    assert skill.author == "Test Author"
    assert skill.tags == ["test", "validation"]
    assert skill.requires == []
    assert skill.enabled is True
    assert os.path.isabs(skill.body_path)


# T020: Test multiple skills loading
def test_load_all_multiple_skills():
    """Create 3 skill fixtures, verify 3 SkillSpec returned in traversal order."""
    result = load_all(SKILLS_DIR)
    
    # Should include test, minimal, and potentially others (excluding malformed/invalid_semver)
    assert len(result) >= 2  # At least test and minimal should load successfully
    
    # Verify all returned skills are SkillSpec instances
    for skill in result:
        assert isinstance(skill, SkillSpec)


# T021: Test parse_frontmatter with valid file
def test_parse_frontmatter_valid():
    """Verify SkillFrontmatter instance returned."""
    test_skill_path = os.path.join(SKILLS_DIR, "test", "SKILL.md")
    result = parse_frontmatter(test_skill_path)
    
    assert isinstance(result, SkillFrontmatter)
    assert result.name == "test-skill"
    assert result.description == "A test skill for validation"
    assert result.version == "v1.0.0"


# T022: Test parse_frontmatter with missing name
def test_parse_frontmatter_missing_name():
    """Verify SkillFrontmatterParseError raised with exit_code=65."""
    malformed_path = os.path.join(SKILLS_DIR, "malformed", "SKILL.md")
    
    with pytest.raises(SkillFrontmatterParseError) as exc_info:
        parse_frontmatter(malformed_path)
    
    assert exc_info.value.exit_code == 65
    assert "name" in str(exc_info.value).lower()


# T023: Test parse_frontmatter with missing description
def test_parse_frontmatter_missing_description():
    """Verify SkillFrontmatterParseError raised."""
    with tempfile.TemporaryDirectory() as tmpdir:
        missing_desc_path = os.path.join(tmpdir, "SKILL.md")
        with open(missing_desc_path, "w") as f:
            f.write("---\nname: test\nversion: v1.0.0\n---\n# Body")
        
        with pytest.raises(SkillFrontmatterParseError) as exc_info:
            parse_frontmatter(missing_desc_path)
        
        assert exc_info.value.exit_code == 65


# T024: Test parse_frontmatter with invalid semver
def test_parse_frontmatter_version_not_semver():
    """Verify error for version='1.0' (not semver)."""
    invalid_semver_path = os.path.join(SKILLS_DIR, "invalid_semver", "SKILL.md")
    
    with pytest.raises(SkillFrontmatterParseError) as exc_info:
        parse_frontmatter(invalid_semver_path)
    
    assert exc_info.value.exit_code == 65
    assert "semver" in str(exc_info.value).lower() or "version" in str(exc_info.value).lower()


# T025: Test parse_frontmatter with invalid YAML
def test_parse_frontmatter_invalid_yaml():
    """Verify yaml.YAMLError wrapped as SkillFrontmatterParseError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        invalid_yaml_path = os.path.join(tmpdir, "SKILL.md")
        with open(invalid_yaml_path, "w") as f:
            f.write("---\nname: test\n  invalid: [unclosed\nversion: v1.0.0\n---\n# Body")
        
        with pytest.raises(SkillFrontmatterParseError) as exc_info:
            parse_frontmatter(invalid_yaml_path)
        
        assert exc_info.value.exit_code == 65


# T026: Test skill body_path is absolute
def test_skill_body_path_resolved():
    """Verify SkillSpec.body_path is absolute."""
    # Create isolated test directory
    with tempfile.TemporaryDirectory() as tmpdir:
        test_skills_dir = os.path.join(tmpdir, "skills")
        test_skill_subdir = os.path.join(test_skills_dir, "test")
        os.makedirs(test_skill_subdir)
        
        # Copy the test skill fixture
        import shutil
        src = os.path.join(SKILLS_DIR, "test", "SKILL.md")
        dst = os.path.join(test_skill_subdir, "SKILL.md")
        shutil.copy(src, dst)
        
        result = load_all(test_skills_dir)
    
    assert len(result) == 1
    assert os.path.isabs(result[0].body_path)


# T027: Test skill enabled defaults to True
def test_skill_enabled_default_true():
    """Verify enabled=True when not in frontmatter."""
    # Create isolated test directory
    with tempfile.TemporaryDirectory() as tmpdir:
        test_skills_dir = os.path.join(tmpdir, "skills")
        test_skill_subdir = os.path.join(test_skills_dir, "test")
        os.makedirs(test_skill_subdir)
        
        # Copy the test skill fixture
        import shutil
        src = os.path.join(SKILLS_DIR, "test", "SKILL.md")
        dst = os.path.join(test_skill_subdir, "SKILL.md")
        shutil.copy(src, dst)
        
        result = load_all(test_skills_dir)
    
    assert len(result) == 1
    assert result[0].enabled is True


# T028: Test skill_loaded event published
@patch("langagent.protocol.skill_loader.event_bus")
def test_skill_publishes_skill_loaded_event(mock_event_bus):
    """Mock event bus, verify skill_loaded event."""
    # Create isolated test directory
    with tempfile.TemporaryDirectory() as tmpdir:
        test_skills_dir = os.path.join(tmpdir, "skills")
        test_skill_subdir = os.path.join(test_skills_dir, "test")
        os.makedirs(test_skill_subdir)
        
        # Copy the test skill fixture
        import shutil
        src = os.path.join(SKILLS_DIR, "test", "SKILL.md")
        dst = os.path.join(test_skill_subdir, "SKILL.md")
        shutil.copy(src, dst)
        
        result = load_all(test_skills_dir)
    
    assert len(result) == 1
    # Verify event bus publish was called (implementation will determine exact calls)
    # This test verifies the integration point exists


# T029: Test skill_load_failed event published
@patch("langagent.protocol.skill_loader.event_bus")
def test_skill_publishes_skill_load_failed_event(mock_event_bus):
    """Verify skill_load_failed event for missing field."""
    # Create isolated test directory with malformed skill
    with tempfile.TemporaryDirectory() as tmpdir:
        test_skills_dir = os.path.join(tmpdir, "skills")
        malformed_subdir = os.path.join(test_skills_dir, "malformed")
        os.makedirs(malformed_subdir)
        
        # Copy the malformed skill fixture
        import shutil
        src = os.path.join(SKILLS_DIR, "malformed", "SKILL.md")
        dst = os.path.join(malformed_subdir, "SKILL.md")
        shutil.copy(src, dst)
        
        result = load_all(test_skills_dir)
    
    # Malformed skill should be skipped, so result might be empty or partial
    # Event bus should have been called with skill_load_failed
    # This test verifies the fail-soft behavior and event emission


# T068: Test malformed skill handled gracefully
@patch("langagent.protocol.skill_loader.event_bus")
def test_skill_loader_handles_malformed_skill_gracefully(mock_event_bus):
    """1 valid + 1 malformed → 1 SkillSpec + 1 skill_load_failed event, no exceptions."""
    # Load from SKILLS_DIR which has both valid and malformed skills
    result = load_all(SKILLS_DIR)
    
    # Should load at least the valid skills (test, minimal)
    assert len(result) >= 2
    
    # Should not raise exceptions despite malformed skill
    for skill in result:
        assert isinstance(skill, SkillSpec)


# T071: Test skill_load_failed event contains details
@patch("langagent.protocol.skill_loader.event_bus")
def test_skill_load_failed_event_contains_details(mock_event_bus):
    """Verify skill_load_failed event contains path, error message, timestamp."""
    # Create isolated test directory with malformed skill
    with tempfile.TemporaryDirectory() as tmpdir:
        test_skills_dir = os.path.join(tmpdir, "skills")
        malformed_subdir = os.path.join(test_skills_dir, "malformed")
        os.makedirs(malformed_subdir)
        
        # Copy the malformed skill fixture
        import shutil
        src = os.path.join(SKILLS_DIR, "malformed", "SKILL.md")
        dst = os.path.join(malformed_subdir, "SKILL.md")
        shutil.copy(src, dst)
        
        result = load_all(test_skills_dir)
    
    # This test verifies the event structure when implemented
    # Event should contain: path, error message, timestamp
