"""AgentState TypedDict and runtime configuration schemas.

This module defines:
1. AgentState - The 5-field state container for LangGraph execution
2. ErrorEntry - Structured error record format for tool failures
3. RuntimeConfig - Frozen configuration container (legacy, to be migrated)
4. GuardrailPolicy - Security and PII redaction policy (legacy)

Constitutional Alignment:
- Article VI: Agent Loop & State Design (AgentState is the authoritative state)
- Article XII: Configuration resolution (RuntimeConfig)
- Article X: Security & Privacy (GuardrailPolicy)
"""

from typing import Any, Annotated, Literal, TypedDict

from pydantic import BaseModel, ConfigDict

from langagent.primitives.langchain_types import BaseChatModel, BaseMessage, add_messages
from langagent.primitives.state_reducers import (
    replace_with_merge,
    merge_dict,
    overwrite_or_merge,
)


# ============================================================================
# Phase 2: Foundational - AgentState TypedDict (T011, T012)
# ============================================================================


class AgentState(TypedDict, total=False):
    """LangAgent main graph state container with 5 annotated fields.
    
    This TypedDict serves as the authoritative state schema for LangGraph execution.
    All fields are optional (total=False) to allow partial initialization.
    
    Reducer functions are imported from primitives.state_reducers (F08 does not define reducers).
    
    Fields:
        messages: Message history with add_messages reducer (append, don't overwrite)
        todos: Task list with replace_with_merge reducer (complete replacement)
        files: File state dict with merge_dict reducer (key-level merge)
        context: Context metadata with overwrite_or_merge reducer (mode-based merge)
        scratchpad: Temporary reasoning data with replace_with_merge reducer
            Special keys:
                - "errors": list[ErrorEntry] - Tool execution error records
    
    Constitutional Alignment:
        - Article VI: Self-defined 5-field TypedDict (not LangGraph MessagesState)
        - Article VIII: TDD rigidity (tests written before implementation)
        - Article XV: Top-level design primacy (aligns with module_schemas.md)
    """
    
    messages: Annotated[list[BaseMessage], add_messages]
    todos: Annotated[list[dict[str, Any]], replace_with_merge]
    files: Annotated[dict[str, dict[str, Any]], merge_dict]
    context: Annotated[dict[str, Any], overwrite_or_merge]
    scratchpad: Annotated[dict[str, Any], replace_with_merge]


class ErrorEntry(TypedDict):
    """Structured tool execution error record.
    
    Stored in state.scratchpad["errors"] as a list of error entries.
    Each entry captures essential debugging information without bloating state.
    
    Fields:
        turn: Turn number when error occurred (1-indexed)
        tool: Tool name (e.g., "echo", "search")
        error: Error message in format "ExceptionClass: message"
        timestamp: ISO8601 UTC timestamp (e.g., "2026-09-20T10:30:45.123456Z")
    
    Example:
        {
            "turn": 3,
            "tool": "echo",
            "error": "TimeoutError: Operation timed out after 5s",
            "timestamp": "2026-09-20T10:30:45.123456Z"
        }
    
    Constitutional Alignment:
        - Article IX: Quality Diagnostics (structured error tracking)
        - Clarification Q4: 4-field format with ISO8601 timestamp
    """
    
    turn: int
    tool: str
    error: str
    timestamp: str


# ============================================================================
# Legacy RuntimeConfig (to be migrated to separate file in future)
# ============================================================================


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
    """Frozen configuration container with 14 fields.
    
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
        
        Runtime configuration (4 fields):
            checkpointer: Checkpoint storage type (memory, sqlite, postgres)
            checkpoint: BaseCheckpointSaver instance (None from config_resolve, populated by runner)
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
    
    # Runtime configuration (4 fields)
    checkpointer: Literal["memory", "sqlite", "postgres"]
    checkpoint: Any | None = None
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
    
    def with_checkpoint(self, checkpoint: Any) -> "RuntimeConfig":
        """Returns new frozen instance with checkpoint field populated.
        
        Used by runner to attach the instantiated checkpoint saver instance
        after checkpoint creation completes.
        
        Args:
            checkpoint: The instantiated checkpoint saver (BaseCheckpointSaver)
            
        Returns:
            New RuntimeConfig instance with updated checkpoint field
        """
        return self.model_copy(update={"checkpoint": checkpoint})


__all__ = [
    "AgentState",
    "ErrorEntry",
    "RuntimeConfig",
    "GuardrailPolicy",
]
