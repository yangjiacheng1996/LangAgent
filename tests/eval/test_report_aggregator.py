"""
Tests for report_aggregator module (T023-T026)

TDD: These tests must FAIL before implementation.
"""

from datetime import datetime
import pytest
from pydantic import BaseModel

# Import will fail until implementation exists - expected for TDD
from langagent.eval.report_aggregator import aggregate, TaskResult, EvalReport


def test_aggregate_returns_eval_report():
    """T023: Aggregate returns EvalReport with correct structure."""
    task_results = [
        TaskResult(
            task_id="task-1",
            passed=True,
            actual_output="Hello",
            expected_output="Hello",
            grader_used="exact_match",
            latency_ms=100.0,
            exit_code=0,
            error_message=None,
            token_usage={"gpt-4o": {"input": 50, "output": 10}}
        ),
        TaskResult(
            task_id="task-2",
            passed=False,
            actual_output="Goodbye",
            expected_output="Hello",
            grader_used="exact_match",
            latency_ms=200.0,
            exit_code=1,
            error_message=None,
            token_usage={"gpt-4o": {"input": 60, "output": 15}}
        ),
    ]
    
    report = aggregate(task_results, agent_dir="/test/agent")
    
    assert isinstance(report, EvalReport)
    assert report.agent_dir == "/test/agent"
    assert len(report.task_results) == 2
    assert isinstance(report.generated_at, datetime)
    assert len(report.report_id) > 0


def test_aggregate_pass_rate():
    """T024: Aggregate calculates correct pass rate."""
    task_results = [
        TaskResult(
            task_id="task-1",
            passed=True,
            actual_output="A",
            expected_output="A",
            grader_used="exact_match",
            latency_ms=100.0,
            exit_code=0,
            error_message=None,
            token_usage={}
        ),
        TaskResult(
            task_id="task-2",
            passed=True,
            actual_output="B",
            expected_output="B",
            grader_used="exact_match",
            latency_ms=150.0,
            exit_code=0,
            error_message=None,
            token_usage={}
        ),
        TaskResult(
            task_id="task-3",
            passed=False,
            actual_output="C",
            expected_output="D",
            grader_used="exact_match",
            latency_ms=200.0,
            exit_code=1,
            error_message=None,
            token_usage={}
        ),
    ]
    
    report = aggregate(task_results, agent_dir="/test/agent")
    
    # 2 passed out of 3 = 0.666...
    assert abs(report.pass_rate - 0.6666666666666666) < 0.0001
    
    # Check percentiles
    assert report.p50_latency_ms == 150.0  # Median
    assert report.p95_latency_ms == 200.0  # 95th percentile


def test_aggregate_handles_empty_results():
    """T025: Aggregate handles empty task results gracefully."""
    task_results = []
    
    report = aggregate(task_results, agent_dir="/test/agent")
    
    assert report.pass_rate == 0.0
    assert report.p50_latency_ms == 0.0
    assert report.p95_latency_ms == 0.0
    assert report.token_usage == {}
    assert report.cost_usd == 0.0
    assert report.task_results == []


def test_aggregate_frozen_instance():
    """T026: EvalReport is frozen (immutable)."""
    task_results = [
        TaskResult(
            task_id="task-1",
            passed=True,
            actual_output="A",
            expected_output="A",
            grader_used="exact_match",
            latency_ms=100.0,
            exit_code=0,
            error_message=None,
            token_usage={}
        ),
    ]
    
    report = aggregate(task_results, agent_dir="/test/agent")
    
    # Attempt to modify should raise error (Pydantic raises ValidationError for frozen models)
    with pytest.raises(Exception):  # Accept ValidationError, AttributeError, or TypeError
        report.pass_rate = 0.5
