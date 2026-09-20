"""Tests for agent template generation functionality."""

import pytest
from pathlib import Path
import tempfile
import shutil
from langagent.runtime.dir_loader import (
    RuntimeDirLoader,
    create_instructions,
    validate_instructions,
    create_agent_py,
    validate_agent_py,
    create_pyproject_toml,
    validate_pyproject_toml,
    create_env_example,
    validate_env_example,
)


class TestTemplateGeneration:
    """Test agent template generation via write_template."""
    
    def test_write_template_creates_full_layout(self):
        """Generate template creates all mandatory and example files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_name = "test-agent"
            
            RuntimeDirLoader.write_template(tmpdir, agent_name)
            
            agent_dir = Path(tmpdir) / agent_name
            
            # Check mandatory files
            assert (agent_dir / "instructions.md").exists()
            assert (agent_dir / "agent.py").exists()
            assert (agent_dir / "pyproject.toml").exists()
            
            # Check example/optional files
            assert (agent_dir / ".env.example").exists()
            assert (agent_dir / "skills").exists()
            assert (agent_dir / "tools").exists()
            assert (agent_dir / "middleware").exists()
    
    def test_write_template_default_model_compatible(self):
        """Generated pyproject.toml includes compatible dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_name = "test-agent"
            
            RuntimeDirLoader.write_template(tmpdir, agent_name)
            
            agent_dir = Path(tmpdir) / agent_name
            pyproject_content = (agent_dir / "pyproject.toml").read_text()
            
            # Verify LangChain/LangGraph dependencies present
            assert "langchain-core" in pyproject_content
            assert "langgraph" in pyproject_content
    
    def test_write_template_dotenv_no_localhost(self):
        """Generated .env.example contains no localhost or internal IPs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_name = "test-agent"
            
            RuntimeDirLoader.write_template(tmpdir, agent_name)
            
            agent_dir = Path(tmpdir) / agent_name
            env_content = (agent_dir / ".env.example").read_text()
            
            # Check for prohibited localhost patterns
            assert "localhost" not in env_content.lower()
            assert "127.0.0.1" not in env_content
            assert "192.168." not in env_content
            assert "10.0." not in env_content
    
    def test_write_template_dotenv_uses_angle_bracket_placeholders(self):
        """Generated .env.example uses <PLACEHOLDER> format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_name = "test-agent"
            
            RuntimeDirLoader.write_template(tmpdir, agent_name)
            
            agent_dir = Path(tmpdir) / agent_name
            env_content = (agent_dir / ".env.example").read_text()
            
            # Verify angle bracket placeholder format
            import re
            placeholders = re.findall(r'<[A-Z_]+>', env_content)
            assert len(placeholders) > 0, "Should have at least one <PLACEHOLDER>"
    
    def test_write_template_instructions_minimal(self):
        """Generated instructions.md is non-empty and minimal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_name = "test-agent"
            
            RuntimeDirLoader.write_template(tmpdir, agent_name)
            
            agent_dir = Path(tmpdir) / agent_name
            instructions_content = (agent_dir / "instructions.md").read_text()
            
            assert len(instructions_content) > 0
            assert len(instructions_content) < 5000  # Reasonable size for template
    
    def test_write_template_idempotent(self):
        """Running write_template twice validates and recreates invalid files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_name = "test-agent"
            
            # First generation
            RuntimeDirLoader.write_template(tmpdir, agent_name)
            
            agent_dir = Path(tmpdir) / agent_name
            
            # Corrupt instructions.md
            (agent_dir / "instructions.md").write_text("INVALID CONTENT")
            
            # Second generation should validate and recreate
            RuntimeDirLoader.write_template(tmpdir, agent_name)
            
            instructions_content = (agent_dir / "instructions.md").read_text()
            assert "INVALID CONTENT" not in instructions_content
            assert len(instructions_content) > 0
    
    def test_write_template_creates_v1_reserved_dirs(self):
        """Generated template includes v1 reserved directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_name = "test-agent"
            
            RuntimeDirLoader.write_template(tmpdir, agent_name)
            
            agent_dir = Path(tmpdir) / agent_name
            
            # Check v1 reserved directories
            assert (agent_dir / "skills").exists()
            assert (agent_dir / "tools").exists()
            assert (agent_dir / "middleware").exists()
            # Optional: channels/, sandbox/ may or may not be created
    
    def test_write_template_emits_lifecycle_init_start_log(self):
        """Template generation emits la.lifecycle.init.start log."""
        # TODO: Implement logging infrastructure and verify log emission
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_name = "test-agent"
            
            RuntimeDirLoader.write_template(tmpdir, agent_name)
            
            # Log verification will be added when logging infrastructure exists
            # For now, just verify the template was created
            agent_dir = Path(tmpdir) / agent_name
            assert agent_dir.exists()
    
    def test_write_template_log_tags_in_whitelist(self):
        """Emitted logs use whitelisted tags."""
        # TODO: Implement logging infrastructure and verify log tags
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_name = "test-agent"
            
            RuntimeDirLoader.write_template(tmpdir, agent_name)
            
            # Log tag verification will be added when logging infrastructure exists
            agent_dir = Path(tmpdir) / agent_name
            assert agent_dir.exists()
    
    def test_write_template_does_not_emit_lifecycle_init_end_log(self):
        """Template generation does NOT emit la.lifecycle.init.end log."""
        # TODO: Implement logging infrastructure and verify no end log
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_name = "test-agent"
            
            RuntimeDirLoader.write_template(tmpdir, agent_name)
            
            # Log verification will be added when logging infrastructure exists
            agent_dir = Path(tmpdir) / agent_name
            assert agent_dir.exists()


class TestTemplateHelpers:
    """Test individual template helper functions."""
    
    def test_create_instructions_returns_valid_content(self):
        """create_instructions returns non-empty markdown content."""
        content = create_instructions()
        
        assert len(content) > 0
        assert isinstance(content, str)
    
    def test_validate_instructions_accepts_valid_content(self):
        """validate_instructions returns True for valid content."""
        valid_content = "You are a helpful assistant."
        
        assert validate_instructions(valid_content) is True
    
    def test_validate_instructions_rejects_empty_string(self):
        """validate_instructions returns False for empty content."""
        assert validate_instructions("") is False
    
    def test_create_agent_py_includes_agent_state(self):
        """create_agent_py includes AgentState TypedDict with 5 fields."""
        content = create_agent_py()
        
        assert "AgentState" in content
        assert "TypedDict" in content
        assert "messages" in content
        assert "todos" in content
        assert "files" in content
        assert "context" in content
        assert "scratchpad" in content
    
    def test_validate_agent_py_accepts_valid_python(self):
        """validate_agent_py uses AST parse to validate Python syntax."""
        valid_content = """
from typing import TypedDict

class AgentState(TypedDict):
    messages: list
"""
        
        assert validate_agent_py(valid_content) is True
    
    def test_validate_agent_py_rejects_invalid_syntax(self):
        """validate_agent_py returns False for invalid Python syntax."""
        invalid_content = "def broken syntax here("
        
        assert validate_agent_py(invalid_content) is False
    
    def test_create_pyproject_toml_includes_project_section(self):
        """create_pyproject_toml includes [project] section."""
        content = create_pyproject_toml("test-agent")
        
        assert "[project]" in content
        assert "name" in content
        assert "test-agent" in content
    
    def test_validate_pyproject_toml_accepts_valid_toml(self):
        """validate_pyproject_toml uses TOML parse to validate."""
        valid_content = """
[project]
name = "test"
version = "0.1.0"
"""
        
        assert validate_pyproject_toml(valid_content) is True
    
    def test_validate_pyproject_toml_rejects_invalid_toml(self):
        """validate_pyproject_toml returns False for invalid TOML."""
        invalid_content = "[project\nbroken"
        
        assert validate_pyproject_toml(invalid_content) is False
    
    def test_create_env_example_has_placeholders(self):
        """create_env_example includes angle bracket placeholders."""
        content = create_env_example()
        
        import re
        placeholders = re.findall(r'<[A-Z_]+>', content)
        assert len(placeholders) > 0
    
    def test_validate_env_example_accepts_valid_format(self):
        """validate_env_example checks for placeholder format."""
        valid_content = "API_KEY=<YOUR_API_KEY>\nMODEL=<MODEL_NAME>"
        
        assert validate_env_example(valid_content) is True
    
    def test_validate_env_example_rejects_localhost(self):
        """validate_env_example returns False if localhost found."""
        invalid_content = "BASE_URL=http://localhost:8000"
        
        assert validate_env_example(invalid_content) is False
