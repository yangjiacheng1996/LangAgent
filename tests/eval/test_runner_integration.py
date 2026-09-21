"""
Integration tests for eval runner (Phase 3)

Simplified tests that verify the runner orchestration without full F01-F10 integration.
"""

import pytest
from pathlib import Path

from langagent.eval.runner import run, EvalRunResult


def test_run_basic_eval_suite(tmp_path):
    """Test basic eval suite execution with exact_match grader."""
    # Create test agent directory
    agent_dir = tmp_path / "test-agent"
    agent_dir.mkdir()
    
    evals_dir = agent_dir / "evals"
    evals_dir.mkdir()
    
    # Create test task that will pass (input == expected)
    task_file = evals_dir / "task1.yaml"
    task_file.write_text("""
task_id: test-001
input: "Hello, World!"
expected: "Hello, World!"
grader: exact_match
timeout_s: 30
""")
    
    # Run eval
    result = run(str(agent_dir))
    
    # Verify result structure
    assert isinstance(result, EvalRunResult)
    assert result.exit_code == 0  # All passed
    assert result.eval_report.pass_rate == 1.0
    assert len(result.eval_report.task_results) == 1


def test_run_with_grader_filter(tmp_path):
    """Test filtering tasks by grader type."""
    agent_dir = tmp_path / "test-agent"
    agent_dir.mkdir()
    
    evals_dir = agent_dir / "evals"
    evals_dir.mkdir()
    
    # Create tasks with different graders
    (evals_dir / "task1.yaml").write_text("""
task_id: exact-001
input: "Hello"
expected: "Hello"
grader: exact_match
""")
    
    (evals_dir / "task2.yaml").write_text("""
task_id: contains-001
input: "Hello World"
expected: "Hello"
grader: contains
""")
    
    # Run with filter
    result = run(str(agent_dir), grader_only="exact_match")
    
    # Should only run exact_match task
    assert len(result.eval_report.task_results) == 1
    assert result.eval_report.task_results[0]["task_id"] == "exact-001"


def test_run_with_failing_task(tmp_path):
    """Test that failing tasks result in non-zero exit code."""
    agent_dir = tmp_path / "test-agent"
    agent_dir.mkdir()
    
    evals_dir = agent_dir / "evals"
    evals_dir.mkdir()
    
    # Create task that will fail (input != expected)
    task_file = evals_dir / "task1.yaml"
    task_file.write_text("""
task_id: test-001
input: "Hello"
expected: "Goodbye"
grader: exact_match
""")
    
    # Run eval
    result = run(str(agent_dir))
    
    # Should fail
    assert result.exit_code == 1  # Failed task
    assert result.eval_report.pass_rate == 0.0


def test_run_empty_evals_dir(tmp_path):
    """Test handling of empty evals directory."""
    agent_dir = tmp_path / "test-agent"
    agent_dir.mkdir()
    
    evals_dir = agent_dir / "evals"
    evals_dir.mkdir()
    
    # Run eval on empty directory
    result = run(str(agent_dir))
    
    # Should return empty report
    assert result.exit_code == 0
    assert result.eval_report.pass_rate == 0.0
    assert len(result.eval_report.task_results) == 0


def test_run_aggregates_multiple_tasks(tmp_path):
    """Test aggregation of multiple task results."""
    agent_dir = tmp_path / "test-agent"
    agent_dir.mkdir()
    
    evals_dir = agent_dir / "evals"
    evals_dir.mkdir()
    
    # Create 3 tasks: 2 pass, 1 fail
    (evals_dir / "task1.yaml").write_text("""
task_id: pass-001
input: "A"
expected: "A"
grader: exact_match
""")
    
    (evals_dir / "task2.yaml").write_text("""
task_id: pass-002
input: "B"
expected: "B"
grader: exact_match
""")
    
    (evals_dir / "task3.yaml").write_text("""
task_id: fail-001
input: "C"
expected: "D"
grader: exact_match
""")
    
    # Run eval
    result = run(str(agent_dir))
    
    # Check aggregation
    assert len(result.eval_report.task_results) == 3
    assert abs(result.eval_report.pass_rate - 0.6666666666666666) < 0.0001
    assert result.exit_code == 1  # At least one failure
