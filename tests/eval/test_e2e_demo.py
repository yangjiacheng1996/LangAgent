"""
End-to-End Demo Test: F11 Eval Subsystem

This test demonstrates the complete evaluation workflow as an automated test.
Originally created as examples/eval_demo.py, now converted to integration test.
"""

import tempfile
from pathlib import Path
import pytest


def test_eval_subsystem_end_to_end_demo():
    """
    Complete end-to-end demonstration of F11 eval subsystem.
    
    Demonstrates:
    1. Creating a demo agent with eval tasks
    2. Running evaluation using the runner
    3. Verifying results
    4. Testing filter functionality
    """
    from langagent.eval.runner import run
    
    with tempfile.TemporaryDirectory() as tmpdir:
        agent_dir = Path(tmpdir) / "demo-agent"
        agent_dir.mkdir()
        
        evals_dir = agent_dir / "evals"
        evals_dir.mkdir()
        
        # Task 1: Exact match (will pass)
        (evals_dir / "greeting.yaml").write_text("""
task_id: greeting-001
input: "Hello, World!"
expected: "Hello, World!"
grader: exact_match
timeout_s: 30
metadata:
  category: basic
  priority: high
""")
        
        # Task 2: Contains (will pass)
        (evals_dir / "code_check.yaml").write_text("""
task_id: code-check-001
input: "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"
expected:
  - "def factorial"
  - "return"
grader: contains
timeout_s: 30
metadata:
  category: code
""")
        
        # Task 3: Regex (will pass)
        (evals_dir / "number_format.yaml").write_text("""
task_id: number-format-001
input: "The answer is 42"
expected: "\\\\d+"
grader: regex
timeout_s: 30
""")
        
        # Task 4: Exact match (will fail - demonstrating failure case)
        (evals_dir / "failing_task.yaml").write_text("""
task_id: failing-001
input: "Hello"
expected: "Goodbye"
grader: exact_match
timeout_s: 30
metadata:
  category: demo
  expected_to_fail: true
""")
        
        # Step 1: Run evaluation
        result = run(str(agent_dir))
        report = result.eval_report
        
        # Step 2: Verify results
        assert len(report.task_results) == 4
        assert report.pass_rate == 0.75  # 3 out of 4 pass
        assert result.exit_code == 1  # Has failures
        
        # Step 3: Verify individual task results
        task_ids = [t['task_id'] for t in report.task_results]
        assert 'greeting-001' in task_ids
        assert 'code-check-001' in task_ids
        assert 'number-format-001' in task_ids
        assert 'failing-001' in task_ids
        
        # Step 4: Verify graders executed correctly
        passed_tasks = [t for t in report.task_results if t['passed']]
        failed_tasks = [t for t in report.task_results if not t['passed']]
        
        assert len(passed_tasks) == 3
        assert len(failed_tasks) == 1
        assert failed_tasks[0]['task_id'] == 'failing-001'
        
        # Step 5: Test filtering by grader
        result_filtered = run(str(agent_dir), grader_only="exact_match")
        assert len(result_filtered.eval_report.task_results) == 2  # greeting + failing
        
        # Verify filter worked
        for task in result_filtered.eval_report.task_results:
            assert task['grader_used'] == "exact_match"
        
        # Step 6: Verify metrics are present
        assert report.p50_latency_ms >= 0
        assert report.p95_latency_ms >= report.p50_latency_ms
        assert isinstance(report.token_usage, dict)
        assert report.cost_usd >= 0


def test_eval_demo_all_grader_types():
    """
    Demonstrate all available grader types.
    """
    from langagent.eval.runner import run
    
    with tempfile.TemporaryDirectory() as tmpdir:
        agent_dir = Path(tmpdir) / "grader-demo"
        agent_dir.mkdir()
        
        evals_dir = agent_dir / "evals"
        evals_dir.mkdir()
        
        # Exact match
        (evals_dir / "exact.yaml").write_text("""
task_id: exact-001
input: "Test"
expected: "Test"
grader: exact_match
""")
        
        # Contains
        (evals_dir / "contains.yaml").write_text("""
task_id: contains-001
input: "Hello World"
expected: "Hello"
grader: contains
""")
        
        # Regex
        (evals_dir / "regex.yaml").write_text("""
task_id: regex-001
input: "Phone: 123-456-7890"
expected: "\\\\d{3}-\\\\d{3}-\\\\d{4}"
grader: regex
""")
        
        # Contains with case_sensitive=false
        (evals_dir / "contains_case.yaml").write_text("""
task_id: contains-case-001
input: "HELLO WORLD"
expected: "hello"
grader: contains
case_sensitive: false
""")
        
        result = run(str(agent_dir))
        
        # All should pass
        assert result.eval_report.pass_rate == 1.0
        assert len(result.eval_report.task_results) == 4
        
        # Verify all grader types used
        graders_used = set(t['grader_used'] for t in result.eval_report.task_results)
        assert 'exact_match' in graders_used
        assert 'contains' in graders_used
        assert 'regex' in graders_used


if __name__ == "__main__":
    """
    This can still be run standalone for manual testing:
    python3 tests/eval/test_e2e_demo.py
    """
    print("="*70)
    print("F11 Eval Subsystem - End-to-End Demo Test")
    print("="*70)
    print()
    
    print("Running test_eval_subsystem_end_to_end_demo...")
    test_eval_subsystem_end_to_end_demo()
    print("✅ PASSED")
    print()
    
    print("Running test_eval_demo_all_grader_types...")
    test_eval_demo_all_grader_types()
    print("✅ PASSED")
    print()
    
    print("="*70)
    print("All demo tests passed successfully!")
    print("="*70)
