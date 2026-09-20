"""RuntimeConfig and GuardrailPolicy schemas for configuration resolution.

This module defines the Pydantic models used to represent runtime configuration
after the config_resolve stage (stage 2) completes. RuntimeConfig is frozen to
prevent accidental modification during runtime.

Constitutional Alignment:
- Article XII: Implements 4-source priority chain (CLI > env > .env > defaults)
- Article IV: Model abstraction with openai-compatible default provider
- Article X: GuardrailPolicy for security constraints
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from langagent.primitives.langchain_types import BaseChatModel


class GuardrailPolicy(BaseModel):
    """Configuration object controlling guardrail behavior.
    
    Attributes:
        enabled: Whether guardrails are active (always True in v1)
        mode: Evaluation mode - "all" (check everything), "smart" (selective), or "strict" (maximum security)
        redact_pii: Whether to redact personally identifiable information (always True in v1)
        allow_internal_endpoints: Whether to allow connections to internal networks
        internal_endpoint_patterns: List of glob patterns or CIDR ranges for internal endpoints
    """
    
    model_config = ConfigDict(frozen=True)
    
    enabled: bool = True
    mode: Literal["all", "smart", "strict"] = "smart"
    redact_pii: bool = True
    allow_internal_endpoints: bool = True
    internal_endpoint_patterns: list[str] = []


class RuntimeConfig(BaseModel):
    """Frozen configuration container with 13 fields.
    
    This represents the fully resolved agent runtime configuration after merging
    4 sources: CLI args > environment variables > .env file > builtin defaults.
    
    The frozen constraint prevents accidental modification. Use with_* methods
    to create modified copies for stage-specific updates.
    
    Attributes:
        Source metadata (4 fields):
            cli_args: Exact dict passed to resolve(), unmodified
            env_vars: Snapshot of os.environ at resolution start
            dotenv_values: Parsed .env file contents
            builtin_defaults: Builtin default values from defaults.py
        
        Model configuration (4 fields):
            model: BaseChatModel instance (None from config_resolve, populated by model_adapt)
            model_provider: Provider name (openai, anthropic, google, deepseek, zhipu, openai-compatible)
            model_name: Model identifier (required, cannot be None)
            model_base_url: Base URL for API calls (required for openai-compatible, deepseek, zhipu)
        
        Runtime configuration (3 fields):
            checkpointer: Checkpoint storage type (memory, sqlite, postgres)
            middleware_ids: List of middleware identifiers to load
            skill_dirs: List of skill directory paths
        
        Miscellaneous (1 field):
            log_level: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
        Guardrail configuration (1 field):
            guardrail_policy: Security and PII redaction policy
    """
    
    model_config = ConfigDict(frozen=True)
    
    # Source metadata (4 fields)
    cli_args: dict[str, Any]
    env_vars: dict[str, str]
    dotenv_values: dict[str, str]
    builtin_defaults: dict[str, Any]
    
    # Model configuration (4 fields)
    model: BaseChatModel | None = None
    model_provider: Literal["openai", "anthropic", "google", "deepseek", "zhipu", "openai-compatible"]
    model_name: str | None
    model_base_url: str | None
    
    # Runtime configuration (3 fields)
    checkpointer: Literal["memory", "sqlite", "postgres"]
    middleware_ids: list[str]
    skill_dirs: list[str]
    
    # Miscellaneous (1 field)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    # Guardrail configuration (1 field)
    guardrail_policy: GuardrailPolicy | None = None
    
    def with_model(self, model: BaseChatModel) -> "RuntimeConfig":
        """Returns new frozen instance with model field populated.
        
        Used by F01 model_adapt stage to attach the instantiated BaseChatModel
        after configuration resolution completes.
        
        Args:
            model: The instantiated chat model
            
        Returns:
            New RuntimeConfig instance with updated model field
        """
        return self.model_copy(update={"model": model})
    
    def with_model_base_url(self, base_url: str) -> "RuntimeConfig":
        """Returns new frozen instance with model_base_url updated.
        
        Args:
            base_url: The new base URL for API calls
            
        Returns:
            New RuntimeConfig instance with updated model_base_url field
        """
        return self.model_copy(update={"model_base_url": base_url})
    
    def with_guardrail_policy(self, policy: GuardrailPolicy) -> "RuntimeConfig":
        """Returns new frozen instance with guardrail_policy updated.
        
        Args:
            policy: The new guardrail policy
            
        Returns:
            New RuntimeConfig instance with updated guardrail_policy field
        """
        return self.model_copy(update={"guardrail_policy": policy})
