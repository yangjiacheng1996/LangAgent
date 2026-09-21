"""
Report Aggregator Module (T027)

Aggregates task results into evaluation report with metrics.
"""

from datetime import datetime
from typing import Any
import uuid
import statistics
from pydantic import BaseModel, Field


class TaskResult(BaseModel, frozen=True):
    """
    Internal runner entity capturing outcome of a single task execution.
    
    Not persisted to disk (aggregated into EvalReport).
    """
    model_config = {"frozen": True}
    
    task_id: str
    passed: bool
    actual_output: str
    expected_output: str | list[str] | dict[str, Any] | None
    grader_used: str
    latency_ms: float = Field(ge=0.0)
    exit_code: int
    error_message: str | None = None
    token_usage: dict[str, dict[str, int]]


class EvalReport(BaseModel, frozen=True):
    """
    Aggregated evaluation report.
    
    Persisted to ~/.local/share/langagent/reports/<agent-name>-<timestamp>.json
    """
    model_config = {"frozen": True}
    
    report_id: str
    generated_at: datetime
    agent_dir: str
    task_results: list[dict[str, Any]]
    pass_rate: float = Field(ge=0.0, le=1.0)
    p50_latency_ms: float = Field(ge=0.0)
    p95_latency_ms: float = Field(ge=0.0)
    token_usage: dict[str, dict[str, int]]
    cost_usd: float = Field(ge=0.0)


def aggregate(task_results: list[TaskResult], agent_dir: str) -> EvalReport:
    """
    Aggregate task results into evaluation report.
    
    Args:
        task_results: List of task execution results
        agent_dir: Path to agent directory
        
    Returns:
        EvalReport with aggregated metrics
    """
    # Handle empty results
    if not task_results:
        return EvalReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(),
            agent_dir=agent_dir,
            task_results=[],
            pass_rate=0.0,
            p50_latency_ms=0.0,
            p95_latency_ms=0.0,
            token_usage={},
            cost_usd=0.0
        )
    
    # Calculate pass rate
    passed_count = sum(1 for task in task_results if task.passed)
    pass_rate = passed_count / len(task_results)
    
    # Calculate latency percentiles
    latencies = sorted([task.latency_ms for task in task_results])
    p50_latency_ms = statistics.median(latencies)
    
    # Calculate 95th percentile using nearest-rank method
    if len(latencies) == 1:
        p95_latency_ms = latencies[0]
    else:
        p95_index = int(0.95 * len(latencies))
        if p95_index >= len(latencies):
            p95_index = len(latencies) - 1
        p95_latency_ms = latencies[p95_index]
    
    # Aggregate token usage by model
    aggregated_tokens: dict[str, dict[str, int]] = {}
    for task in task_results:
        for model_name, tokens in task.token_usage.items():
            if model_name not in aggregated_tokens:
                aggregated_tokens[model_name] = {"input": 0, "output": 0}
            aggregated_tokens[model_name]["input"] += tokens.get("input", 0)
            aggregated_tokens[model_name]["output"] += tokens.get("output", 0)
    
    # Calculate estimated cost (simplified - would use model pricing in real implementation)
    cost_usd = 0.0
    for model_name, tokens in aggregated_tokens.items():
        # Simplified cost calculation: $0.01 per 1000 input tokens, $0.03 per 1000 output tokens
        input_cost = (tokens["input"] / 1000) * 0.01
        output_cost = (tokens["output"] / 1000) * 0.03
        cost_usd += input_cost + output_cost
    
    # Convert TaskResult to dicts for JSON serialization
    task_results_dicts = [task.model_dump() for task in task_results]
    
    return EvalReport(
        report_id=str(uuid.uuid4()),
        generated_at=datetime.now(),
        agent_dir=agent_dir,
        task_results=task_results_dicts,
        pass_rate=pass_rate,
        p50_latency_ms=p50_latency_ms,
        p95_latency_ms=p95_latency_ms,
        token_usage=aggregated_tokens,
        cost_usd=cost_usd
    )


__all__ = ["TaskResult", "EvalReport", "aggregate"]
