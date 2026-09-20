"""Report schemas for diagnostic outputs.

Defines:
- DoctorReport: Self-check diagnostic report
- EvalReport: Evaluation task aggregation report
- MetricsSnapshot: Re-exported from metrics_collector

Constitutional alignment: Article IX (Quality Diagnostics Matrix)
"""

from typing import Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
import uuid

from langagent.runtime.doctor_check import DoctorCheckResult
from langagent.runtime.config_snapshot import RuntimeConfigSnapshot


class DoctorReport(BaseModel):
    """Doctor self-check report with 6 fields."""
    
    model_config = ConfigDict(frozen=True)
    
    report_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique report ID (UUID4)"
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Report generation timestamp (UTC)"
    )
    checks: list[DoctorCheckResult] = Field(
        ..., description="4 check results (model, checkpointer, skills, instructions)"
    )
    overall: str = Field(..., description="Overall status: ok/warn/error")
    agent_dir: str | None = Field(None, description="Path to checked agent directory")
    runtime: RuntimeConfigSnapshot = Field(..., description="Runtime config snapshot")


class EvalReport(BaseModel):
    """Evaluation task aggregation report with 9 fields."""
    
    model_config = ConfigDict(frozen=True)
    
    report_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique report ID (UUID4)"
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Report generation timestamp (UTC)"
    )
    agent_dir: str = Field(..., description="Path to evaluated agent directory")
    task_results: list[dict[str, Any]] = Field(
        ..., description="Per-task results (task_id, passed, actual, expected)"
    )
    pass_rate: float = Field(..., ge=0.0, le=1.0, description="Pass rate (0.0-1.0)")
    p50_latency_ms: float = Field(..., ge=0.0, description="P50 latency in milliseconds")
    p95_latency_ms: float = Field(..., ge=0.0, description="P95 latency in milliseconds")
    token_usage: dict[str, int] = Field(..., description="Token usage by model")
    cost_usd: float = Field(..., ge=0.0, description="Estimated cost in USD")
