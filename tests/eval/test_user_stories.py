"""
User Story Validation Tests (T088-T093)

Complete validation of all 6 user stories from quickstart.md
"""

import pytest
from pathlib import Path


# ============================================================================
# T088: User Story 1 - Basic Eval Suite
# ============================================================================

def test_user_story_1_basic_eval_suite(tmp_path):
    """
    US1: Basic Eval Suite
    
    Validates quickstart.md Scenario 1: Basic Eval Run
    - Load tasks from YAML
    - Execute agent for each task
    - Grade with exact_match
    - Generate EvalReport with pass rate
    - Return correct exit code
    """
    from langagent.eval.runner import run
    
    # Setup
    agent_dir = tmp_path / "basic-agent"
    agent_dir.mkdir()
    evals_dir = agent_dir / "evals"
    evals_dir.mkdir()
    
    # Create basic eval tasks
    (evals_dir / "greeting.yaml").write_text("""
task_id: greeting-001
input: "Hello, World!"
expected: "Hello, World!"
grader: exact_match
timeout_s: 30
metadata:
  category: greeting
  priority: high
""")
    
    (evals_dir / "farewell.yaml").write_text("""
task_id: farewell-001
input: "Goodbye"
expected: "Goodbye"
grader: exact_match
timeout_s: 30
""")
    
    # Execute
    result = run(str(agent_dir))
    
    # Validate - US1 Success Criteria
    assert result.eval_report is not None
    assert len(result.eval_report.task_results) == 2
    assert result.eval_report.pass_rate == 1.0
    assert result.exit_code == 0
    
    # Validate report structure
    assert result.eval_report.p50_latency_ms >= 0
    assert result.eval_report.p95_latency_ms >= 0
    assert isinstance(result.eval_report.task_results, list)
    
    # Validate task results
    for task in result.eval_report.task_results:
        assert 'task_id' in task
        assert 'passed' in task
        assert 'grader_used' in task
        assert task['passed'] is True  # All should pass


def test_user_story_1_all_tasks_pass_exit_code_zero(tmp_path):
    """
    US1: Validates Scenario 2 - All Tasks Pass
    Exit code should be 0 when all tasks pass
    """
    from langagent.eval.runner import run
    
    agent_dir = tmp_path / "pass-agent"
    agent_dir.mkdir()
    evals_dir = agent_dir / "evals"
    evals_dir.mkdir()
    
    (evals_dir / "task1.yaml").write_text("""
task_id: pass-001
input: "A"
expected: "A"
grader: exact_match
""")
    
    result = run(str(agent_dir))
    
    assert result.eval_report.pass_rate == 1.0
    assert result.exit_code == 0


def test_user_story_1_has_failures_nonzero_exit(tmp_path):
    """
    US1: Exit code should be non-zero when tasks fail
    """
    from langagent.eval.runner import run
    
    agent_dir = tmp_path / "fail-agent"
    agent_dir.mkdir()
    evals_dir = agent_dir / "evals"
    evals_dir.mkdir()
    
    (evals_dir / "fail.yaml").write_text("""
task_id: fail-001
input: "Hello"
expected: "Goodbye"
grader: exact_match
""")
    
    result = run(str(agent_dir))
    
    assert result.eval_report.pass_rate == 0.0
    assert result.exit_code > 0


# ============================================================================
# T089: User Story 2 - LLM Judge (Partial - requires F01)
# ============================================================================

def test_user_story_2_llm_judge_grader_exists(tmp_path):
    """
    US2: LLM Judge
    
    Validates that llm_judge grader exists and can be invoked.
    Full validation requires F01 integration.
    """
    from langagent.eval.graders import get_grader
    
    # Verify llm_judge is registered
    grader = get_grader("llm_judge")
    assert grader is not None
    assert callable(grader)


def test_user_story_2_llm_judge_in_yaml(tmp_path):
    """
    US2: Validates llm_judge can be specified in YAML
    """
    from langagent.eval.task_loader import load_all
    
    agent_dir = tmp_path / "judge-agent"
    agent_dir.mkdir()
    evals_dir = agent_dir / "evals"
    evals_dir.mkdir()
    
    (evals_dir / "judge.yaml").write_text("""
task_id: judge-001
input: "Translate 'Hello' to Spanish"
expected:
  - "Hola"
  - "Buenos días"
grader: llm_judge
timeout_s: 60
""")
    
    tasks = load_all(str(evals_dir))
    
    assert len(tasks) == 1
    assert tasks[0].grader == "llm_judge"
    assert isinstance(tasks[0].expected, list)


# ============================================================================
# T090: User Story 3 - Tool Call Match (Partial - requires F08)
# ============================================================================

def test_user_story_3_tool_call_match_grader_exists(tmp_path):
    """
    US3: Tool Call Verification
    
    Validates that tool_call_match grader exists and validates dict type.
    Full validation requires F08 integration.
    """
    from langagent.eval.graders import get_grader
    from langagent.eval.task_loader import load_all
    from pydantic import ValidationError
    
    # Verify tool_call_match is registered
    grader = get_grader("tool_call_match")
    assert grader is not None
    
    # Verify YAML validation enforces dict for tool_call_match
    agent_dir = tmp_path / "tool-agent"
    agent_dir.mkdir()
    evals_dir = agent_dir / "evals"
    evals_dir.mkdir()
    
    # Valid: dict expected
    (evals_dir / "valid.yaml").write_text("""
task_id: tool-001
input: "Search for Python"
expected:
  tool_id: web_search
  args:
    query: Python
grader: tool_call_match
""")
    
    tasks = load_all(str(evals_dir))
    assert len(tasks) == 1
    assert tasks[0].grader == "tool_call_match"
    assert isinstance(tasks[0].expected, dict)


def test_user_story_3_tool_call_match_rejects_string(tmp_path):
    """
    US3: Validates tool_call_match rejects string expected
    """
    from langagent.eval.task_loader import load_all
    from pydantic import ValidationError
    
    agent_dir = tmp_path / "tool-bad-agent"
    agent_dir.mkdir()
    evals_dir = agent_dir / "evals"
    evals_dir.mkdir()
    
    # Invalid: string expected with tool_call_match
    (evals_dir / "invalid.yaml").write_text("""
task_id: tool-bad-001
input: "Search"
expected: "some string"
grader: tool_call_match
""")
    
    with pytest.raises(ValidationError) as exc_info:
        load_all(str(evals_dir))
    
    assert "dict" in str(exc_info.value).lower() or "tool_call_match" in str(exc_info.value).lower()


# ============================================================================
# T091: User Story 4 - Flexible Matching
# ============================================================================

def test_user_story_4_flexible_matching_contains(tmp_path):
    """
    US4: Flexible Matching with contains grader
    
    Validates quickstart.md Scenario 4
    """
    from langagent.eval.runner import run
    
    agent_dir = tmp_path / "flexible-agent"
    agent_dir.mkdir()
    evals_dir = agent_dir / "evals"
    evals_dir.mkdir()
    
    (evals_dir / "contains.yaml").write_text("""
task_id: contains-001
input: "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"
expected:
  - "def factorial"
  - "return"
grader: contains
""")
    
    result = run(str(agent_dir))
    
    assert result.eval_report.pass_rate == 1.0
    assert result.eval_report.task_results[0]['grader_used'] == "contains"


def test_user_story_4_flexible_matching_regex(tmp_path):
    """
    US4: Flexible Matching with regex grader
    """
    from langagent.eval.runner import run
    
    agent_dir = tmp_path / "regex-agent"
    agent_dir.mkdir()
    evals_dir = agent_dir / "evals"
    evals_dir.mkdir()
    
    (evals_dir / "regex.yaml").write_text("""
task_id: regex-001
input: "Phone: 123-456-7890"
expected: "\\\\d{3}-\\\\d{3}-\\\\d{4}"
grader: regex
""")
    
    result = run(str(agent_dir))
    
    assert result.eval_report.pass_rate == 1.0
    assert result.eval_report.task_results[0]['grader_used'] == "regex"


def test_user_story_4_case_sensitivity(tmp_path):
    """
    US4: Validates case_sensitive parameter for contains/regex
    """
    from langagent.eval.runner import run
    
    agent_dir = tmp_path / "case-agent"
    agent_dir.mkdir()
    evals_dir = agent_dir / "evals"
    evals_dir.mkdir()
    
    # Case-insensitive contains
    (evals_dir / "case_insensitive.yaml").write_text("""
task_id: case-001
input: "Hello World"
expected: "hello"
grader: contains
case_sensitive: false
""")
    
    result = run(str(agent_dir))
    
    assert result.eval_report.pass_rate == 1.0


# ============================================================================
# T092: User Story 5 - Performance Metrics
# ============================================================================

def test_user_story_5_performance_metrics(tmp_path):
    """
    US5: Performance Metrics
    
    Validates quickstart.md Scenario 3 - metrics aggregation
    """
    from langagent.eval.runner import run
    
    agent_dir = tmp_path / "metrics-agent"
    agent_dir.mkdir()
    evals_dir = agent_dir / "evals"
    evals_dir.mkdir()
    
    # Create multiple tasks to generate metrics
    for i in range(5):
        (evals_dir / f"task_{i}.yaml").write_text(f"""
task_id: metrics-{i:03d}
input: "Task {i}"
expected: "Task {i}"
grader: exact_match
""")
    
    result = run(str(agent_dir))
    
    # Validate US5 Success Criteria
    assert result.eval_report.pass_rate >= 0.0
    assert result.eval_report.p50_latency_ms >= 0.0
    assert result.eval_report.p95_latency_ms >= result.eval_report.p50_latency_ms
    assert isinstance(result.eval_report.token_usage, dict)
    assert result.eval_report.cost_usd >= 0.0
    
    # Validate all 5 tasks executed
    assert len(result.eval_report.task_results) == 5


# ============================================================================
# T093: User Story 6 - Selective Execution
# ============================================================================

def test_user_story_6_selective_execution_by_grader(tmp_path):
    """
    US6: Selective Execution
    
    Validates quickstart.md Scenario 4 - filter by grader
    """
    from langagent.eval.runner import run
    
    agent_dir = tmp_path / "filter-agent"
    agent_dir.mkdir()
    evals_dir = agent_dir / "evals"
    evals_dir.mkdir()
    
    # Create tasks with different graders
    (evals_dir / "exact.yaml").write_text("""
task_id: exact-001
input: "A"
expected: "A"
grader: exact_match
""")
    
    (evals_dir / "contains.yaml").write_text("""
task_id: contains-001
input: "Hello"
expected: "Hello"
grader: contains
""")
    
    (evals_dir / "regex.yaml").write_text("""
task_id: regex-001
input: "123"
expected: "\\\\d+"
grader: regex
""")
    
    # Run with grader filter
    result = run(str(agent_dir), grader_only="exact_match")
    
    # Validate US6 Success Criteria
    assert len(result.eval_report.task_results) == 1
    assert result.eval_report.task_results[0]['grader_used'] == "exact_match"
    assert result.eval_report.task_results[0]['task_id'] == "exact-001"


def test_user_story_6_selective_execution_by_task_id(tmp_path):
    """
    US6: Selective Execution by task ID
    """
    from langagent.eval.runner import run
    
    agent_dir = tmp_path / "task-filter-agent"
    agent_dir.mkdir()
    evals_dir = agent_dir / "evals"
    evals_dir.mkdir()
    
    (evals_dir / "task1.yaml").write_text("""
task_id: specific-task-001
input: "Test"
expected: "Test"
grader: exact_match
""")
    
    (evals_dir / "task2.yaml").write_text("""
task_id: other-task-002
input: "Other"
expected: "Other"
grader: exact_match
""")
    
    # Run specific task only
    result = run(str(agent_dir), task_id="specific-task-001")
    
    assert len(result.eval_report.task_results) == 1
    assert result.eval_report.task_results[0]['task_id'] == "specific-task-001"


def test_user_story_6_filter_reduces_execution_time(tmp_path):
    """
    US6: Validates that filtering reduces execution scope
    """
    from langagent.eval.runner import run
    
    agent_dir = tmp_path / "speed-agent"
    agent_dir.mkdir()
    evals_dir = agent_dir / "evals"
    evals_dir.mkdir()
    
    # Create 10 tasks
    for i in range(10):
        grader = "exact_match" if i < 5 else "contains"
        (evals_dir / f"task_{i}.yaml").write_text(f"""
task_id: speed-{i:03d}
input: "Task {i}"
expected: "Task {i}"
grader: {grader}
""")
    
    # Run all tasks
    result_all = run(str(agent_dir))
    assert len(result_all.eval_report.task_results) == 10
    
    # Run filtered (should be ~50% of tasks)
    result_filtered = run(str(agent_dir), grader_only="exact_match")
    assert len(result_filtered.eval_report.task_results) == 5
    
    # Validate filter worked correctly
    for task in result_filtered.eval_report.task_results:
        assert task['grader_used'] == "exact_match"
