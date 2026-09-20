"""RuntimeConfigSnapshot for diagnostic reports.

Provides a serializable subset of RuntimeConfig that:
- Excludes BaseChatModel instances (not JSON-serializable)
- Excludes secrets (cli_args, env_vars, dotenv_values, builtin_defaults)
- Includes 9 safe diagnostic fields

Constitutional alignment: Article X (Security & Privacy)
"""

from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class RuntimeConfigSnapshot(BaseModel):
    """Serializable subset of RuntimeConfig for embedding in DoctorReport.
    
    Excludes:
        - model: BaseChatModel instance (not JSON-serializable)
        - cli_args, env_vars, dotenv_values, builtin_defaults: May contain secrets
    
    Includes:
        9 fields needed for doctor/eval report diagnostics
    """
    
    model_config = ConfigDict(frozen=True)
    
    schema_version: str = Field(default="v0.2.0", description="Snapshot schema version")
    model_provider: Literal["openai", "anthropic", "google", "deepseek", "zhipu", "openai-compatible"] = Field(
        ..., description="Model provider name"
    )
    model_name: str | None = Field(None, description="Model name (if specified)")
    model_base_url: str | None = Field(None, description="Base URL for OpenAI-compatible providers")
    checkpointer: Literal["memory", "sqlite", "postgres"] = Field(..., description="Checkpointer type")
    middleware_ids: list[str] = Field(default_factory=list, description="Enabled middleware IDs")
    skill_dirs: list[str] = Field(default_factory=list, description="Skill directory names")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Log level"
    )
    guardrail_allow_internal_endpoints: bool = Field(
        default=True, description="Guardrail internal endpoint allow flag"
    )
    
    @classmethod
    def from_runtime_config(cls, config: "RuntimeConfig") -> "RuntimeConfigSnapshot":
        """Factory method to create snapshot from RuntimeConfig.
        
        Args:
            config: Full RuntimeConfig instance with all 13 fields
            
        Returns:
            RuntimeConfigSnapshot with 9 safe fields (excludes model and secrets)
            
        Example:
            >>> config = RuntimeConfig(...)
            >>> snapshot = RuntimeConfigSnapshot.from_runtime_config(config)
            >>> json_str = snapshot.model_dump_json()  # JSON-serializable
        """
        # Extract guardrail_allow_internal_endpoints from nested policy
        guardrail_allow_internal = True
        if config.guardrail_policy is not None:
            guardrail_allow_internal = config.guardrail_policy.allow_internal_endpoints
        
        return cls(
            schema_version="v0.2.0",
            model_provider=config.model_provider,
            model_name=config.model_name,
            model_base_url=config.model_base_url,
            checkpointer=config.checkpointer,
            middleware_ids=list(config.middleware_ids),  # Defensive copy
            skill_dirs=list(config.skill_dirs),
            log_level=config.log_level,
            guardrail_allow_internal_endpoints=guardrail_allow_internal,
        )
