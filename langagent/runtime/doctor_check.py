"""Doctor self-check functionality for LangAgent.

Implements 4 diagnostic checks:
- model: Test model endpoint connectivity
- checkpointer: Verify checkpointer initialization
- skills: Validate skill frontmatter
- instructions: Check instructions format

Constitutional alignment: Articles VIII (TDD), IX (diagnostics)
"""

from typing import Literal, Callable, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone


class DoctorCheckResult(BaseModel):
    """Single doctor check result."""
    
    model_config = ConfigDict(frozen=True)
    
    check_name: Literal["model", "checkpointer", "skills", "instructions"] = Field(
        ..., description="Name of check"
    )
    status: Literal["ok", "warn", "error", "skipped"] = Field(
        ..., description="Check status"
    )
    detail: str = Field(..., description="Human-readable details or error message")


def check_model(
    config: Any,
    loaded: Any,
    *,
    model_probe_fn: Callable[[], bool] | None = None
) -> DoctorCheckResult:
    """Check model endpoint connectivity.
    
    Args:
        config: Runtime configuration
        loaded: Loaded agent directory data
        model_probe_fn: Optional probe function to test connectivity
        
    Returns:
        DoctorCheckResult with status ok/error/skipped
    """
    if model_probe_fn is None:
        return DoctorCheckResult(
            check_name="model",
            status="skipped",
            detail="model_probe_fn not provided"
        )
    
    try:
        is_reachable = model_probe_fn()
        if is_reachable:
            provider = getattr(config, 'model_provider', 'unknown')
            model_name = getattr(config, 'model_name', 'unknown')
            return DoctorCheckResult(
                check_name="model",
                status="ok",
                detail=f"Connected to {provider} {model_name} endpoint successfully"
            )
        else:
            return DoctorCheckResult(
                check_name="model",
                status="error",
                detail="Model endpoint unreachable"
            )
    except Exception as e:
        return DoctorCheckResult(
            check_name="model",
            status="error",
            detail=f"Model check failed: {str(e)}"
        )


def check_checkpointer(
    config: Any,
    *,
    checkpoint_probe_fn: Callable[[], bool] | None = None
) -> DoctorCheckResult:
    """Check checkpointer initialization.
    
    Args:
        config: Runtime configuration
        checkpoint_probe_fn: Optional probe function to test checkpointer
        
    Returns:
        DoctorCheckResult with status ok/error/skipped
    """
    if checkpoint_probe_fn is None:
        # No probe function, check basic config
        checkpointer_type = getattr(config, 'checkpointer', 'unknown')
        return DoctorCheckResult(
            check_name="checkpointer",
            status="ok",
            detail=f"{checkpointer_type} checkpointer configured"
        )
    
    try:
        is_working = checkpoint_probe_fn()
        if is_working:
            checkpointer_type = getattr(config, 'checkpointer', 'unknown')
            return DoctorCheckResult(
                check_name="checkpointer",
                status="ok",
                detail=f"{checkpointer_type} checkpointer initialized successfully"
            )
        else:
            return DoctorCheckResult(
                check_name="checkpointer",
                status="error",
                detail="Checkpointer initialization failed"
            )
    except Exception as e:
        return DoctorCheckResult(
            check_name="checkpointer",
            status="error",
            detail=f"Checkpointer check failed: {str(e)}"
        )


def check_skills(loaded: Any) -> DoctorCheckResult:
    """Check skills frontmatter validity.
    
    Args:
        loaded: Loaded agent directory data
        
    Returns:
        DoctorCheckResult with status ok/warn/error
    """
    if not hasattr(loaded, 'skills') or not loaded.skills:
        return DoctorCheckResult(
            check_name="skills",
            status="ok",
            detail="No skills configured"
        )
    
    skills = loaded.skills
    malformed_skills = []
    valid_skills = []
    
    for skill in skills:
        skill_name = getattr(skill, 'name', 'unknown')
        # Check if skill has required fields
        if not hasattr(skill, 'name') or not hasattr(skill, 'version'):
            malformed_skills.append(skill_name)
        else:
            valid_skills.append(skill_name)
    
    if malformed_skills and not valid_skills:
        # All skills are malformed - error
        return DoctorCheckResult(
            check_name="skills",
            status="error",
            detail=f"All skills have malformed frontmatter: {', '.join(malformed_skills)}"
        )
    elif malformed_skills:
        # Some skills malformed - warning
        return DoctorCheckResult(
            check_name="skills",
            status="warn",
            detail=f"Malformed skills: {', '.join(malformed_skills)}"
        )
    else:
        # All valid
        return DoctorCheckResult(
            check_name="skills",
            status="ok",
            detail=f"Found {len(valid_skills)} valid skill(s): {', '.join(valid_skills)}"
        )


def check_instructions(loaded: Any) -> DoctorCheckResult:
    """Check instructions format and content.
    
    Args:
        loaded: Loaded agent directory data
        
    Returns:
        DoctorCheckResult with status ok/warn
    """
    if not hasattr(loaded, 'instructions') or not loaded.instructions:
        return DoctorCheckResult(
            check_name="instructions",
            status="warn",
            detail="No instructions found"
        )
    
    instructions = loaded.instructions
    instruction_length = len(instructions)
    
    # Heuristic: length > 10 AND contains keyword
    keywords = ["you", "你", "应该"]
    has_keyword = any(keyword in instructions.lower() for keyword in keywords)
    
    if instruction_length <= 10:
        return DoctorCheckResult(
            check_name="instructions",
            status="warn",
            detail=f"Instructions too short ({instruction_length} characters)"
        )
    elif not has_keyword:
        return DoctorCheckResult(
            check_name="instructions",
            status="warn",
            detail=f"Instructions missing expected keywords (len={instruction_length})"
        )
    else:
        return DoctorCheckResult(
            check_name="instructions",
            status="ok",
            detail=f"Instructions valid ({instruction_length} characters)"
        )


def run_doctor_checks(
    config: Any,
    loaded: Any,
    *,
    model_probe_fn: Callable[[], bool] | None = None,
    checkpoint_probe_fn: Callable[[], bool] | None = None
) -> tuple[list[DoctorCheckResult], Literal["ok", "warn", "error"]]:
    """Run all 4 doctor checks and aggregate results.
    
    Args:
        config: Runtime configuration
        loaded: Loaded agent directory data
        model_probe_fn: Optional probe function for model connectivity
        checkpoint_probe_fn: Optional probe function for checkpointer
        
    Returns:
        Tuple of (check results list, overall status)
    """
    checks = [
        check_model(config, loaded, model_probe_fn=model_probe_fn),
        check_checkpointer(config, checkpoint_probe_fn=checkpoint_probe_fn),
        check_skills(loaded),
        check_instructions(loaded),
    ]
    
    # Aggregate overall status
    has_error = any(check.status == "error" for check in checks)
    has_warn = any(check.status == "warn" for check in checks)
    
    if has_error:
        overall = "error"
    elif has_warn:
        overall = "warn"
    else:
        overall = "ok"
    
    return checks, overall
