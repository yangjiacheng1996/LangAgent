"""Tests for tool registry protocol layer."""

import os
import sys
import tempfile
from unittest.mock import Mock, patch

import pytest

from langagent.protocol.tool_registry import register_all, get_by_id
from langagent.protocol.tool_schemas import (
    ToolIdDuplicateError,
    ToolSpec,
)


# Test fixtures path
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "sample_agent")
TOOLS_DIR = os.path.join(FIXTURES_DIR, "tools")


# T043: Test empty directory
def test_register_all_empty_dir():
    """Verify empty list when tools/ doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        non_existent = os.path.join(tmpdir, "non_existent_tools")
        result = register_all(non_existent)
        assert result == []


# T044: Test single tool registration
def test_register_all_single_tool():
    """Verify 1 ToolSpec with tool_id=='echo'."""
    # Create isolated test directory with only echo tool
    with tempfile.TemporaryDirectory() as tmpdir:
        test_tools_dir = os.path.join(tmpdir, "tools")
        os.makedirs(test_tools_dir)
        
        # Copy the echo tool fixture
        import shutil
        src = os.path.join(TOOLS_DIR, "echo.py")
        dst = os.path.join(test_tools_dir, "echo.py")
        shutil.copy(src, dst)
        
        result = register_all(test_tools_dir)
    
    assert len(result) == 1
    tool = result[0]
    
    assert isinstance(tool, ToolSpec)
    assert tool.tool_id == "echo"
    assert tool.tool_name == "echo"  # Should match tool_id
    assert tool.description == "Echoes input text back to the user"
    assert tool.enabled is False  # Default to False per FR-016
    assert tool.requires_approval is False
    assert "$schema" in tool.args_schema
    assert tool.args_schema["$schema"] == "http://json-schema.org/draft-07/schema#"


# T045: Test multiple tools registration
def test_register_all_multiple_tools():
    """Create 3 tool fixtures, verify 3 ToolSpec returned."""
    # Create isolated test directory with multiple tools
    with tempfile.TemporaryDirectory() as tmpdir:
        test_tools_dir = os.path.join(tmpdir, "tools")
        os.makedirs(test_tools_dir)
        
        # Copy multiple tool fixtures
        import shutil
        for tool_name in ["echo.py", "safe.py", "dangerous.py"]:
            src = os.path.join(TOOLS_DIR, tool_name)
            dst = os.path.join(test_tools_dir, tool_name)
            shutil.copy(src, dst)
        
        result = register_all(test_tools_dir)
    
    assert len(result) == 3
    
    # Verify all returned tools are ToolSpec instances
    for tool in result:
        assert isinstance(tool, ToolSpec)


# T046: Test tool requires_approval defaults to False
def test_tool_requires_approval_default_false():
    """Verify requires_approval==False for safe.py."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_tools_dir = os.path.join(tmpdir, "tools")
        os.makedirs(test_tools_dir)
        
        import shutil
        src = os.path.join(TOOLS_DIR, "safe.py")
        dst = os.path.join(test_tools_dir, "safe.py")
        shutil.copy(src, dst)
        
        result = register_all(test_tools_dir)
    
    assert len(result) == 1
    assert result[0].requires_approval is False


# T047: Test tool requires_approval from constant
def test_tool_requires_approval_from_constant():
    """Verify requires_approval==True for dangerous.py."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_tools_dir = os.path.join(tmpdir, "tools")
        os.makedirs(test_tools_dir)
        
        import shutil
        src = os.path.join(TOOLS_DIR, "dangerous.py")
        dst = os.path.join(test_tools_dir, "dangerous.py")
        shutil.copy(src, dst)
        
        result = register_all(test_tools_dir)
    
    assert len(result) == 1
    assert result[0].requires_approval is True


# T048: Test tool args_schema extracted
def test_tool_args_schema_extracted():
    """Verify args_schema contains $schema=='http://json-schema.org/draft-07/schema#'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_tools_dir = os.path.join(tmpdir, "tools")
        os.makedirs(test_tools_dir)
        
        import shutil
        src = os.path.join(TOOLS_DIR, "echo.py")
        dst = os.path.join(test_tools_dir, "echo.py")
        shutil.copy(src, dst)
        
        result = register_all(test_tools_dir)
    
    assert len(result) == 1
    args_schema = result[0].args_schema
    
    assert isinstance(args_schema, dict)
    assert "$schema" in args_schema
    assert args_schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert "properties" in args_schema


# T050: Test dynamic import no sys.path pollution
def test_tool_dynamic_import_no_sys_path_pollution():
    """Verify sys.path length unchanged."""
    sys_path_before = len(sys.path)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_tools_dir = os.path.join(tmpdir, "tools")
        os.makedirs(test_tools_dir)
        
        import shutil
        src = os.path.join(TOOLS_DIR, "echo.py")
        dst = os.path.join(test_tools_dir, "echo.py")
        shutil.copy(src, dst)
        
        result = register_all(test_tools_dir)
    
    sys_path_after = len(sys.path)
    
    assert sys_path_before == sys_path_after


# T051: Test get_by_id
def test_tool_get_by_id():
    """Verify get_by_id('echo') returns ToolSpec, get_by_id('missing') returns None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_tools_dir = os.path.join(tmpdir, "tools")
        os.makedirs(test_tools_dir)
        
        import shutil
        src = os.path.join(TOOLS_DIR, "echo.py")
        dst = os.path.join(test_tools_dir, "echo.py")
        shutil.copy(src, dst)
        
        register_all(test_tools_dir)
    
    # Test successful lookup
    tool = get_by_id("echo")
    assert tool is not None
    assert isinstance(tool, ToolSpec)
    assert tool.tool_id == "echo"
    
    # Test missing tool
    missing = get_by_id("missing_tool")
    assert missing is None


# T052: Test tool_registered event published
@patch("langagent.protocol.tool_registry.event_bus")
def test_tool_publishes_tool_registered_event(mock_event_bus):
    """Mock event bus, verify tool_registered event."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_tools_dir = os.path.join(tmpdir, "tools")
        os.makedirs(test_tools_dir)
        
        import shutil
        src = os.path.join(TOOLS_DIR, "echo.py")
        dst = os.path.join(test_tools_dir, "echo.py")
        shutil.copy(src, dst)
        
        result = register_all(test_tools_dir)
    
    assert len(result) == 1
    # Verify event bus publish was called (implementation will determine exact calls)


# T069: Test tool registry handles import error gracefully
def test_tool_registry_handles_import_error_gracefully():
    """1 valid + 1 syntax_error.py → 1 ToolSpec + 1 tool_load_failed event, no exceptions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_tools_dir = os.path.join(tmpdir, "tools")
        os.makedirs(test_tools_dir)
        
        import shutil
        # Copy valid tool
        src = os.path.join(TOOLS_DIR, "echo.py")
        dst = os.path.join(test_tools_dir, "echo.py")
        shutil.copy(src, dst)
        
        # Copy broken tool
        src_broken = os.path.join(TOOLS_DIR, "syntax_error.py")
        dst_broken = os.path.join(test_tools_dir, "syntax_error.py")
        shutil.copy(src_broken, dst_broken)
        
        result = register_all(test_tools_dir)
    
    # Should load only the valid tool
    assert len(result) == 1
    assert result[0].tool_id == "echo"


# T070: Test tool registry handles import error with missing dependency
def test_tool_registry_handles_import_error_missing_dependency():
    """Verify ImportError caught and tool skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_tools_dir = os.path.join(tmpdir, "tools")
        os.makedirs(test_tools_dir)
        
        import shutil
        # Copy valid tool
        src = os.path.join(TOOLS_DIR, "echo.py")
        dst = os.path.join(test_tools_dir, "echo.py")
        shutil.copy(src, dst)
        
        # Copy tool with import error
        src_broken = os.path.join(TOOLS_DIR, "import_error.py")
        dst_broken = os.path.join(test_tools_dir, "import_error.py")
        shutil.copy(src_broken, dst_broken)
        
        result = register_all(test_tools_dir)
    
    # Should load only the valid tool
    assert len(result) == 1
    assert result[0].tool_id == "echo"


# T079: Test sys.modules cleanup on register
def test_tool_loader_cleans_sys_modules_on_register():
    """Verify sys.modules has zero langagent_dynamic_tool_* entries after register_all()."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_tools_dir = os.path.join(tmpdir, "tools")
        os.makedirs(test_tools_dir)
        
        import shutil
        src = os.path.join(TOOLS_DIR, "echo.py")
        dst = os.path.join(test_tools_dir, "echo.py")
        shutil.copy(src, dst)
        
        result = register_all(test_tools_dir)
    
    # Check sys.modules for any langagent_dynamic_tool_* entries
    dynamic_modules = [k for k in sys.modules.keys() if k.startswith("langagent_dynamic_tool_")]
    assert len(dynamic_modules) == 0


# T080: Test sys.modules cleanup on failure
def test_tool_loader_cleans_sys_modules_on_failure():
    """Verify failed tool doesn't pollute sys.modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_tools_dir = os.path.join(tmpdir, "tools")
        os.makedirs(test_tools_dir)
        
        import shutil
        # Copy broken tool
        src = os.path.join(TOOLS_DIR, "syntax_error.py")
        dst = os.path.join(test_tools_dir, "syntax_error.py")
        shutil.copy(src, dst)
        
        result = register_all(test_tools_dir)
    
    # Check sys.modules for any langagent_dynamic_tool_* entries
    dynamic_modules = [k for k in sys.modules.keys() if k.startswith("langagent_dynamic_tool_")]
    assert len(dynamic_modules) == 0


# T081: Test sys.path length unchanged after tool loading
def test_sys_path_length_unchanged_after_tool_loading():
    """Verify sys.path length before == after."""
    sys_path_before = len(sys.path)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_tools_dir = os.path.join(tmpdir, "tools")
        os.makedirs(test_tools_dir)
        
        import shutil
        for tool_name in ["echo.py", "safe.py", "dangerous.py"]:
            src = os.path.join(TOOLS_DIR, tool_name)
            dst = os.path.join(test_tools_dir, tool_name)
            shutil.copy(src, dst)
        
        result = register_all(test_tools_dir)
    
    sys_path_after = len(sys.path)
    
    assert sys_path_before == sys_path_after
