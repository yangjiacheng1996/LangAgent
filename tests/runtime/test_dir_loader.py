"""Tests for agent directory loading functionality."""

import pytest
from pathlib import Path
from langagent.runtime.dir_loader import (
    RuntimeDirLoader,
    LoadedAgent,
    AgentDirNotFoundError,
    AgentDirNotDirectoryError,
    AgentDirInvalidLayoutError,
    InstructionsReadError,
)


class TestLoadedAgentSchema:
    """Test LoadedAgent dataclass structure."""
    
    def test_loaded_agent_has_exactly_five_fields(self):
        """LoadedAgent must have exactly 5 fields per FR-013."""
        loaded_agent = LoadedAgent(
            agent_dir="/path/to/agent",
            instructions="Test instructions",
            tool_ids=["tool1"],
            skill_names=["skill1"],
            metadata={"schema_version": "0.2.0"}
        )
        
        # Count fields using __dataclass_fields__
        field_count = len(LoadedAgent.__dataclass_fields__)
        assert field_count == 5, f"LoadedAgent must have exactly 5 fields, found {field_count}"
    
    def test_loaded_agent_does_not_have_compiled_graph_field(self):
        """LoadedAgent must not have compiled_graph field per v1.1.0 P0-2 fix."""
        loaded_agent = LoadedAgent(
            agent_dir="/path/to/agent",
            instructions="Test instructions",
            tool_ids=[],
            skill_names=[],
            metadata={"schema_version": "0.2.0"}
        )
        
        assert not hasattr(loaded_agent, 'compiled_graph'), \
            "LoadedAgent must not have compiled_graph field"


class TestDirectoryLoading:
    """Test loading existing agent directories."""
    
    def test_load_full_agent_dir(self):
        """Load a complete agent directory with all components."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_agent"
        
        loaded_agent = RuntimeDirLoader.load(str(fixture_path))
        
        assert loaded_agent is not None
        assert loaded_agent.agent_dir == str(fixture_path.resolve())
        assert len(loaded_agent.instructions) > 0
        assert loaded_agent.metadata['schema_version'] == '0.2.0'
    
    def test_load_reads_instructions(self):
        """Verify instructions.md content is read correctly."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_agent"
        
        loaded_agent = RuntimeDirLoader.load(str(fixture_path))
        
        assert "helpful assistant" in loaded_agent.instructions
        assert len(loaded_agent.instructions) > 0
    
    def test_load_scans_tool_ids(self):
        """Verify tools/ directory is scanned and tool IDs populated."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_agent"
        
        loaded_agent = RuntimeDirLoader.load(str(fixture_path))
        
        assert "calculator" in loaded_agent.tool_ids
        assert len(loaded_agent.tool_ids) > 0
    
    def test_load_scans_skill_names(self):
        """Verify skills/ directory is scanned and skill names populated."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_agent"
        
        loaded_agent = RuntimeDirLoader.load(str(fixture_path))
        
        assert "example_skill" in loaded_agent.skill_names
        assert len(loaded_agent.skill_names) > 0
    
    def test_load_emits_dir_load_ok_log(self):
        """Verify successful load emits la.runtime.dir_load.ok log."""
        # TODO: Implement logging infrastructure and verify log emission
        fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_agent"
        
        loaded_agent = RuntimeDirLoader.load(str(fixture_path))
        
        assert loaded_agent is not None
        # Log verification will be added when logging infrastructure exists
    
    def test_load_emits_dir_load_fail_log(self):
        """Verify failed load emits la.runtime.dir_load.fail log."""
        # TODO: Implement logging infrastructure and verify log emission
        with pytest.raises(AgentDirNotFoundError):
            RuntimeDirLoader.load("/nonexistent/path")
        
        # Log verification will be added when logging infrastructure exists


class TestLayoutValidation:
    """Test agent directory layout validation."""
    
    def test_validate_layout_full(self):
        """Validate a complete agent directory layout."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_agent"
        
        missing_files = RuntimeDirLoader.validate_layout(str(fixture_path))
        
        assert missing_files == [], f"Expected no missing files, found: {missing_files}"
    
    def test_validate_layout_missing_instructions(self):
        """Detect missing instructions.md file."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "broken_agent"
        
        missing_files = RuntimeDirLoader.validate_layout(str(fixture_path))
        
        assert "instructions.md" in missing_files
    
    def test_validate_layout_missing_agent_py(self):
        """Detect missing agent.py file."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "broken_agent"
        
        missing_files = RuntimeDirLoader.validate_layout(str(fixture_path))
        
        assert "agent.py" in missing_files
    
    def test_validate_layout_missing_pyproject_toml(self):
        """Detect missing pyproject.toml file."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "broken_agent"
        
        missing_files = RuntimeDirLoader.validate_layout(str(fixture_path))
        
        assert "pyproject.toml" in missing_files
    
    def test_validate_layout_missing_skills_dir_returns_ok(self):
        """Missing skills/ directory is acceptable."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "minimal_agent"
        
        missing_files = RuntimeDirLoader.validate_layout(str(fixture_path))
        
        # skills/ is optional, should not be in missing_files
        assert "skills/" not in missing_files
    
    def test_validate_layout_missing_tools_dir_returns_ok(self):
        """Missing tools/ directory is acceptable."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "minimal_agent"
        
        missing_files = RuntimeDirLoader.validate_layout(str(fixture_path))
        
        # tools/ is optional, should not be in missing_files
        assert "tools/" not in missing_files
    
    def test_validate_layout_missing_middleware_dir_returns_ok(self):
        """Missing middleware/ directory is acceptable."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "minimal_agent"
        
        missing_files = RuntimeDirLoader.validate_layout(str(fixture_path))
        
        # middleware/ is optional
        assert "middleware/" not in missing_files
    
    def test_validate_layout_skills_dir_empty_is_valid(self):
        """Empty skills/ directory is valid."""
        # Create temporary agent with empty skills/
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mandatory files
            Path(tmpdir, "instructions.md").write_text("Test")
            Path(tmpdir, "agent.py").write_text("pass")
            Path(tmpdir, "pyproject.toml").write_text("[project]\nname='test'")
            Path(tmpdir, "skills").mkdir()
            
            missing_files = RuntimeDirLoader.validate_layout(tmpdir)
            
            assert missing_files == []
    
    def test_validate_layout_tools_dir_empty_is_valid(self):
        """Empty tools/ directory is valid."""
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "instructions.md").write_text("Test")
            Path(tmpdir, "agent.py").write_text("pass")
            Path(tmpdir, "pyproject.toml").write_text("[project]\nname='test'")
            Path(tmpdir, "tools").mkdir()
            
            missing_files = RuntimeDirLoader.validate_layout(tmpdir)
            
            assert missing_files == []
    
    def test_validate_layout_v1_reserved_optional(self):
        """V1 reserved directories (channels/, identity, memory, sandbox/) are optional."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "minimal_agent"
        
        missing_files = RuntimeDirLoader.validate_layout(str(fixture_path))
        
        # None of the v1 reserved items should be in missing_files
        for item in ["channels/", "identity", "memory", "sandbox/"]:
            assert item not in missing_files
    
    def test_validate_layout_missing_channels_dir_returns_ok(self):
        """Missing channels/ directory is acceptable."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "minimal_agent"
        
        missing_files = RuntimeDirLoader.validate_layout(str(fixture_path))
        
        assert "channels/" not in missing_files
    
    def test_validate_layout_missing_identity_file_returns_ok(self):
        """Missing identity file is acceptable."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "minimal_agent"
        
        missing_files = RuntimeDirLoader.validate_layout(str(fixture_path))
        
        assert "identity" not in missing_files
    
    def test_validate_layout_missing_memory_file_returns_ok(self):
        """Missing memory file is acceptable."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "minimal_agent"
        
        missing_files = RuntimeDirLoader.validate_layout(str(fixture_path))
        
        assert "memory" not in missing_files
    
    def test_validate_layout_missing_sandbox_dir_returns_ok(self):
        """Missing sandbox/ directory is acceptable."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "minimal_agent"
        
        missing_files = RuntimeDirLoader.validate_layout(str(fixture_path))
        
        assert "sandbox/" not in missing_files
    
    def test_validate_layout_minimal_agent_works(self):
        """Agent with only 3 mandatory files is valid."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "minimal_agent"
        
        missing_files = RuntimeDirLoader.validate_layout(str(fixture_path))
        
        assert missing_files == []


class TestErrorHandling:
    """Test error detection and handling."""
    
    def test_load_agent_dir_not_found(self):
        """Raise AgentDirNotFoundError when directory doesn't exist."""
        with pytest.raises(AgentDirNotFoundError):
            RuntimeDirLoader.load("/nonexistent/path/to/agent")
    
    def test_load_agent_dir_not_a_directory(self):
        """Raise AgentDirNotDirectoryError when path is a file."""
        # Use a file that exists in the repo
        file_path = Path(__file__).parent.parent / "fixtures" / "sample_agent" / "instructions.md"
        
        with pytest.raises(AgentDirNotDirectoryError):
            RuntimeDirLoader.load(str(file_path))
    
    def test_load_invalid_layout(self):
        """Raise AgentDirInvalidLayoutError when mandatory files are missing."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "broken_agent"
        
        with pytest.raises(AgentDirInvalidLayoutError) as exc_info:
            RuntimeDirLoader.load(str(fixture_path))
        
        # Verify the exception contains missing file information
        assert len(exc_info.value.missing_files) > 0
    
    def test_load_instructions_permission_denied(self):
        """Raise InstructionsReadError when instructions.md has permission issues."""
        # This test requires creating a file with restricted permissions
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mandatory files
            instructions_path = Path(tmpdir, "instructions.md")
            instructions_path.write_text("Test")
            Path(tmpdir, "agent.py").write_text("pass")
            Path(tmpdir, "pyproject.toml").write_text("[project]\nname='test'")
            
            # Remove read permissions
            os.chmod(instructions_path, 0o000)
            
            try:
                with pytest.raises(InstructionsReadError):
                    RuntimeDirLoader.load(tmpdir)
            finally:
                # Restore permissions for cleanup
                os.chmod(instructions_path, 0o644)


class TestMinimalAgent:
    """Test minimal valid agent support (User Story 5)."""
    
    def test_load_minimal_agent_returns_empty_lists(self):
        """Load minimal agent with only 3 mandatory files returns empty tool/skill lists."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "minimal_agent"
        
        loaded_agent = RuntimeDirLoader.load(str(fixture_path))
        
        assert loaded_agent.tool_ids == []
        assert loaded_agent.skill_names == []
        assert len(loaded_agent.instructions) > 0
    
    def test_validate_layout_minimal_passes(self):
        """Minimal agent with only 3 mandatory files passes validation."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "minimal_agent"
        
        missing_files = RuntimeDirLoader.validate_layout(str(fixture_path))
        
        assert missing_files == []
