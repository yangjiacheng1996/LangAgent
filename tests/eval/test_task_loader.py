"""
Tests for task_loader module (T012-T021)

TDD: These tests must FAIL before implementation.
"""

import tempfile
from pathlib import Path
import pytest
from pydantic import ValidationError

# Import will fail until implementation exists - expected for TDD
from langagent.eval.task_loader import load_all


def test_load_all_empty_dir():
    """T012: Load from empty directory returns empty list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evals_dir = Path(tmpdir) / "evals"
        evals_dir.mkdir()
        
        tasks = load_all(str(evals_dir))
        
        assert tasks == []


def test_load_all_single_task():
    """T013: Load single valid YAML task."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evals_dir = Path(tmpdir) / "evals"
        evals_dir.mkdir()
        
        task_file = evals_dir / "task1.yaml"
        task_file.write_text("""
task_id: test-001
input: "Hello"
expected: "World"
grader: exact_match
timeout_s: 30
""")
        
        tasks = load_all(str(evals_dir))
        
        assert len(tasks) == 1
        assert tasks[0].task_id == "test-001"
        assert tasks[0].input == "Hello"
        assert tasks[0].expected == "World"
        assert tasks[0].grader == "exact_match"
        assert tasks[0].timeout_s == 30


def test_load_all_multiple_tasks():
    """T014: Load multiple YAML tasks, sorted by task_id."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evals_dir = Path(tmpdir) / "evals"
        evals_dir.mkdir()
        
        (evals_dir / "task_b.yaml").write_text("""
task_id: task-b
input: "B"
""")
        (evals_dir / "task_a.yaml").write_text("""
task_id: task-a
input: "A"
""")
        
        tasks = load_all(str(evals_dir))
        
        assert len(tasks) == 2
        # Should be sorted by task_id
        assert tasks[0].task_id == "task-a"
        assert tasks[1].task_id == "task-b"


def test_load_yaml_parse_error():
    """T015: Invalid YAML syntax raises error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evals_dir = Path(tmpdir) / "evals"
        evals_dir.mkdir()
        
        task_file = evals_dir / "bad.yaml"
        task_file.write_text("""
task_id: test
input: "Hello
  this is bad yaml
""")
        
        with pytest.raises(Exception) as exc_info:
            load_all(str(evals_dir))
        
        # Should raise YAML parsing error
        assert "yaml" in str(exc_info.value).lower() or "parse" in str(exc_info.value).lower()


def test_load_required_field_missing():
    """T016: Missing required field (task_id or input) raises ValidationError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evals_dir = Path(tmpdir) / "evals"
        evals_dir.mkdir()
        
        task_file = evals_dir / "missing.yaml"
        task_file.write_text("""
task_id: test-001
# Missing required 'input' field
expected: "World"
""")
        
        with pytest.raises(ValidationError) as exc_info:
            load_all(str(evals_dir))
        
        assert "input" in str(exc_info.value).lower()


def test_load_grader_invalid_value():
    """T017: Invalid grader enum value raises ValidationError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evals_dir = Path(tmpdir) / "evals"
        evals_dir.mkdir()
        
        task_file = evals_dir / "bad_grader.yaml"
        task_file.write_text("""
task_id: test-001
input: "Hello"
grader: invalid_grader_name
""")
        
        with pytest.raises(ValidationError) as exc_info:
            load_all(str(evals_dir))
        
        assert "grader" in str(exc_info.value).lower()


def test_load_timeout_s_must_be_positive():
    """T018: timeout_s < 1 raises ValidationError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evals_dir = Path(tmpdir) / "evals"
        evals_dir.mkdir()
        
        task_file = evals_dir / "bad_timeout.yaml"
        task_file.write_text("""
task_id: test-001
input: "Hello"
timeout_s: 0
""")
        
        with pytest.raises(ValidationError) as exc_info:
            load_all(str(evals_dir))
        
        assert "timeout" in str(exc_info.value).lower()


def test_load_expected_can_be_list():
    """T019: expected field can be a list of strings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evals_dir = Path(tmpdir) / "evals"
        evals_dir.mkdir()
        
        task_file = evals_dir / "list_expected.yaml"
        task_file.write_text("""
task_id: test-001
input: "Hello"
expected:
  - "World"
  - "Earth"
grader: contains
""")
        
        tasks = load_all(str(evals_dir))
        
        assert len(tasks) == 1
        assert tasks[0].expected == ["World", "Earth"]


def test_load_metadata_optional():
    """T020: metadata field is optional and defaults to empty dict."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evals_dir = Path(tmpdir) / "evals"
        evals_dir.mkdir()
        
        task_file = evals_dir / "no_metadata.yaml"
        task_file.write_text("""
task_id: test-001
input: "Hello"
""")
        
        tasks = load_all(str(evals_dir))
        
        assert len(tasks) == 1
        assert tasks[0].metadata == {}


def test_load_rejects_tool_call_match_with_string_expected():
    """T021: tool_call_match grader with string expected raises ValidationError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evals_dir = Path(tmpdir) / "evals"
        evals_dir.mkdir()
        
        task_file = evals_dir / "tool_bad.yaml"
        task_file.write_text("""
task_id: test-001
input: "Search"
expected: "some string"
grader: tool_call_match
""")
        
        with pytest.raises(ValidationError) as exc_info:
            load_all(str(evals_dir))
        
        # Should mention tool_call_match requires dict
        assert "dict" in str(exc_info.value).lower() or "tool_call_match" in str(exc_info.value).lower()
