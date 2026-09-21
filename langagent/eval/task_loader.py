"""
Task Loader Module (T022)

Loads EvalTaskSpec from YAML files in agent's evals/ directory.
"""

from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal


class EvalTaskSpec(BaseModel, frozen=True):
    """
    A single evaluation task specification.
    
    Loaded from <agent-dir>/evals/*.yaml files.
    """
    model_config = {"frozen": True}
    
    task_id: str
    input: str
    expected: str | list[str] | dict[str, Any] | None = None
    grader: Literal['exact_match', 'contains', 'regex', 'llm_judge', 'tool_call_match'] = 'exact_match'
    timeout_s: int = Field(default=60, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    grader_extensibility: list[str] = Field(default_factory=list)
    case_sensitive: bool = True
    
    @model_validator(mode='after')
    def validate_grader_compatibility(self) -> 'EvalTaskSpec':
        """Validate grader-specific requirements."""
        # Check tool_call_match requires dict expected
        if self.grader == 'tool_call_match' and self.expected is not None and not isinstance(self.expected, dict):
            raise ValueError(
                f"tool_call_match grader requires expected as dict (got {type(self.expected).__name__})"
            )
        
        # Check exact_match doesn't support case_sensitive=False
        if self.grader == 'exact_match' and self.case_sensitive is False:
            raise ValueError(
                "exact_match grader does not support case_sensitive=false (always case-sensitive)"
            )
        
        return self


def load_all(evals_dir: str) -> list[EvalTaskSpec]:
    """
    Load all evaluation tasks from YAML files in evals directory.
    
    Args:
        evals_dir: Path to directory containing *.yaml files
        
    Returns:
        List of EvalTaskSpec, sorted by task_id
        
    Raises:
        yaml.YAMLError: If YAML parsing fails
        pydantic.ValidationError: If task spec validation fails
    """
    evals_path = Path(evals_dir)
    
    # Return empty list if directory doesn't exist
    if not evals_path.exists():
        return []
    
    tasks = []
    
    # Load all .yaml and .yml files
    for yaml_file in sorted(evals_path.glob("*.yaml")) + sorted(evals_path.glob("*.yml")):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            if data is None:
                continue
                
            # Validate and create EvalTaskSpec
            task_spec = EvalTaskSpec.model_validate(data)
            tasks.append(task_spec)
            
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"YAML parse error in {yaml_file}: {e}")
    
    # Sort by task_id for deterministic ordering
    tasks.sort(key=lambda t: t.task_id)
    
    return tasks


__all__ = ["EvalTaskSpec", "load_all"]
