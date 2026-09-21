"""
Eval Runner Module (Phase 3)

Main evaluation orchestration: load tasks, execute, grade, aggregate results.
"""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langagent.eval.task_loader import load_all, EvalTaskSpec
from langagent.eval.report_aggregator import aggregate, TaskResult, EvalReport
from langagent.eval.graders import get_grader


@dataclass(frozen=True)
class EvalRunResult:
    """Runner's return value wrapping EvalReport + exit code."""
    eval_report: EvalReport
    exit_code: int


class EvalTimeoutError(Exception):
    """Raised when task execution exceeds timeout."""
    pass


def run(agent_dir: str, grader_only: str | None = None, task_id: str | None = None) -> EvalRunResult:
    """
    Run evaluation suite for agent.
    
    Args:
        agent_dir: Path to agent directory
        grader_only: Optional filter by grader type
        task_id: Optional specific task ID to run
        
    Returns:
        EvalRunResult with report and exit code
    """
    # Load all eval tasks
    evals_dir = Path(agent_dir) / "evals"
    tasks = load_all(str(evals_dir))
    
    # Apply filters
    if grader_only:
        tasks = [t for t in tasks if t.grader == grader_only]
    
    if task_id:
        tasks = [t for t in tasks if t.task_id == task_id]
    
    # Run each task
    task_results = []
    for task_spec in tasks:
        result = _run_one_task(task_spec, agent_dir)
        task_results.append(result)
    
    # Aggregate results
    report = aggregate(task_results, agent_dir)
    
    # Calculate exit code (worst of all failures)
    exit_codes = [r.exit_code for r in task_results]
    exit_code = max(exit_codes) if exit_codes else 0
    
    return EvalRunResult(eval_report=report, exit_code=exit_code)


def _run_one_task(task_spec: EvalTaskSpec, agent_dir: str) -> TaskResult:
    """
    Execute a single eval task.
    
    This is a simplified implementation that simulates agent execution.
    In a full implementation, this would:
    1. Load agent from agent_dir using F06 dir_loader
    2. Execute agent via F08 main_loop_dispatcher
    3. Extract output from final state
    4. Grade using appropriate grader
    
    For now, we simulate with the input echoed as output for testing.
    """
    start_time = time.perf_counter()
    
    try:
        # Simulate agent execution (in real implementation, use F08)
        # For testing, we echo the input as output
        actual_output = _simulate_agent_execution(task_spec.input, task_spec.timeout_s)
        
        # Grade the output
        grader_func = get_grader(task_spec.grader)
        
        # Prepare grader arguments based on grader type
        if task_spec.grader == "llm_judge":
            # LLM judge needs a judge model - for now, we'll skip it
            # In full implementation, create judge model via F01
            passed = False  # Placeholder
        elif task_spec.grader == "tool_call_match":
            # tool_call_match needs AIMessage with tool_calls
            # For testing, always fail since we're simulating
            passed = False
        else:
            # Standard graders (exact_match, contains, regex)
            kwargs = {}
            if task_spec.grader in ("contains", "regex"):
                kwargs["case_sensitive"] = task_spec.case_sensitive
            
            passed = grader_func(actual_output, task_spec.expected, **kwargs)
        
        # Calculate metrics
        latency_ms = (time.perf_counter() - start_time) * 1000
        exit_code = 0 if passed else 1
        
        return TaskResult(
            task_id=task_spec.task_id,
            passed=passed,
            actual_output=actual_output,
            expected_output=task_spec.expected,
            grader_used=task_spec.grader,
            latency_ms=latency_ms,
            exit_code=exit_code,
            error_message=None,
            token_usage={}
        )
        
    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return TaskResult(
            task_id=task_spec.task_id,
            passed=False,
            actual_output="",
            expected_output=task_spec.expected,
            grader_used=task_spec.grader,
            latency_ms=latency_ms,
            exit_code=70,  # EX_SOFTWARE
            error_message=str(e),
            token_usage={}
        )


def _simulate_agent_execution(input_text: str, timeout_s: int) -> str:
    """
    Simulate agent execution for testing.
    
    In full implementation, this would use F08 main_loop_dispatcher.
    For now, we just echo the input.
    """
    # Simple simulation: echo the input
    return input_text


__all__ = ["run", "EvalRunResult", "EvalTimeoutError"]
