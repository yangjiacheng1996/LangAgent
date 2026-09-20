"""Configuration resolution module for the config_resolve stage (stage 2).

This module implements the RuntimeConfigResolver class that merges configuration
from 4 sources (CLI > env > .env > defaults) following strict priority chain rules,
validates all required fields, detects placeholder values, and produces a frozen
RuntimeConfig instance.

The config_resolve stage is the second of six stages in the LangAgent runtime pipeline:
1. dir_load - Load agent directory structure
2. **config_resolve** - Merge and validate configuration (THIS MODULE)
3. model_adapt - Instantiate chat model
4. graph_compose - Build LangGraph state machine
5. main_loop - Execute agent turns
6. exit_cleanup - Cleanup and finalize

Key Features:
- 4-source priority chain with explicit logging
- Required field validation (model_name always required)
- Placeholder detection to catch common mistakes
- Frozen RuntimeConfig to prevent accidental modification
- GuardrailPolicy resolution with lenient boolean parsing
- CSV list parsing for middleware and skill directories
- Comprehensive error handling with proper exit codes

Constitutional Alignment:
- Article XII: Implements 4-source priority chain and startup logging
- Article IV: Model abstraction with openai-compatible default
- Article X: GuardrailPolicy for security constraints
- Article VIII: TDD approach (tests written first)

Exit Codes:
- 5: RequiredFieldMissingError - Missing required configuration field
- 65: DotenvMalformedError - .env file syntax error
- 78: ConfigPlaceholderError, TypeMismatchError, ValidationError - Invalid configuration

Example Usage:
    >>> from langagent.runtime.config_resolver import RuntimeConfigResolver
    >>> resolver = RuntimeConfigResolver()
    >>> config = resolver.resolve(
    ...     cli_args={"model_name": "gpt-4"},
    ...     agent_dir="/path/to/agent"
    ... )
    >>> print(config.model_name)
    gpt-4
    >>> print(config.model_provider)
    openai-compatible

See Also:
    - langagent.runtime.agent_state: RuntimeConfig and GuardrailPolicy schemas
    - langagent.runtime.defaults: BUILTIN_DEFAULTS configuration
    - langagent.runtime.exceptions: Exception classes with exit codes
"""

import os
import re
from pathlib import Path
from typing import Any

from langagent.runtime.agent_state import RuntimeConfig, GuardrailPolicy
from langagent.runtime.defaults import BUILTIN_DEFAULTS
from langagent.runtime.exceptions import (
    RequiredFieldMissingError,
    ConfigPlaceholderError,
    DotenvMalformedError,
    TypeMismatchError,
)
from langagent.cross_cutting import logger
from langagent.cross_cutting.stage_guard import cross_cutting_stage_guard_decorator
from langagent.primitives.langchain_types import BaseChatModel


# Placeholder detection pattern: matches <your-...>
PLACEHOLDER_PATTERN = re.compile(r"^<your-.+>$")


def parse_dotenv(env_path: str) -> dict[str, str]:
    """Parse .env file with simple implementation.
    
    Supports:
    - KEY=VALUE syntax
    - Quoted values: KEY="VALUE" (quotes removed)
    - Comments: lines starting with #
    - Blank lines ignored
    - Last value wins for duplicate keys
    
    Args:
        env_path: Path to .env file
        
    Returns:
        Dictionary of parsed key-value pairs, empty dict if file doesn't exist
        
    Raises:
        DotenvMalformedError: If .env file contains malformed syntax
    """
    env_file = Path(env_path)
    if not env_file.exists():
        return {}
    
    try:
        result: dict[str, str] = {}
        with open(env_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                # Strip whitespace
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                
                # Parse KEY=VALUE
                if "=" not in line:
                    raise DotenvMalformedError(
                        env_path, 
                        f"Line {line_num}: Missing '=' separator: {line}"
                    )
                
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                
                # Check for malformed syntax (e.g., KEY==)
                if not key or "=" in key:
                    raise DotenvMalformedError(
                        env_path,
                        f"Line {line_num}: Malformed key: {line}"
                    )
                
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                # Last value wins for duplicate keys
                result[key] = value
        
        return result
    except DotenvMalformedError:
        raise
    except Exception as e:
        raise DotenvMalformedError(env_path, str(e))


def validate_required_fields(merged_config: dict[str, Any]) -> None:
    """Validate that all required configuration fields are present.
    
    Required fields:
    - model_name: Always required
    - model_base_url: Required for openai-compatible, deepseek, zhipu providers
    
    Args:
        merged_config: Merged configuration dict
        
    Raises:
        RequiredFieldMissingError: If a required field is missing (exit code 5)
    """
    # model_name is always required
    if merged_config.get("model_name") is None:
        raise RequiredFieldMissingError(
            field="model_name",
            message="model_name is required - cannot run agent without specifying a model"
        )
    
    # model_base_url is required for certain providers
    model_provider = merged_config.get("model_provider", "openai-compatible")
    requires_base_url = model_provider in ["openai-compatible", "deepseek", "zhipu"]
    
    if requires_base_url and merged_config.get("model_base_url") is None:
        raise RequiredFieldMissingError(
            field="model_base_url",
            message=f"model_base_url is required for provider '{model_provider}'"
        )


def validate_no_placeholders(merged_config: dict[str, Any]) -> None:
    """Scan all string values for placeholder patterns like <your-...>.
    
    Args:
        merged_config: Merged configuration dict
        
    Raises:
        ConfigPlaceholderError: If any field contains a placeholder (exit code 78)
    """
    for field, value in merged_config.items():
        if isinstance(value, str) and PLACEHOLDER_PATTERN.match(value):
            raise ConfigPlaceholderError(field=field, value=value)


def parse_csv_list(value: str) -> list[str]:
    """Parse comma-separated list, filtering empty items.
    
    Args:
        value: CSV string
        
    Returns:
        List of non-empty strings with whitespace trimmed
    """
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


# Lenient boolean parsing tables (clarification Q1)
_TRUE_VALUES = frozenset({"true", "1", "yes", "on"})
_FALSE_VALUES = frozenset({"false", "0", "no", "off"})


def parse_bool(value: str, field: str = "boolean") -> bool:
    """Parse boolean from environment variable with lenient matching.
    
    Accepts (case-insensitive):
    - True: "true", "1", "yes", "on"
    - False: "false", "0", "no", "off"
    
    Args:
        value: String value to parse
        field: Field name for error reporting
        
    Returns:
        Parsed boolean value
        
    Raises:
        TypeMismatchError: If value is not a recognized boolean (exit code 78)
    """
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise TypeMismatchError(
        field=field,
        expected_type='bool (one of "true"/"1"/"yes"/"on" or "false"/"0"/"no"/"off")',
        actual_value=value,
    )


def parse_guardrail_policy(
    env_vars: dict[str, str],
    dotenv_values_dict: dict[str, str],
    builtin_defaults: dict[str, Any],
) -> GuardrailPolicy:
    """Resolve GuardrailPolicy from environment variables.
    
    Reads (priority: env > .env > defaults):
    - LANGAGENT_GUARDRAIL_MODE: "all" | "smart" | "strict"
    - LANGAGENT_GUARDRAIL_ALLOW_INTERNAL_ENDPOINTS: lenient boolean
    - LANGAGENT_INTERNAL_ENDPOINTS: CSV of glob patterns / CIDR ranges
    
    Note: enabled and redact_pii have no environment override in v1 (always True
    per spec FR-5).
    
    Args:
        env_vars: Environment variables snapshot
        dotenv_values_dict: Parsed .env file
        builtin_defaults: Builtin default values
        
    Returns:
        GuardrailPolicy instance
        
    Raises:
        TypeMismatchError: Invalid boolean value (exit code 78)
        ValidationError: Invalid mode enum value (exit code 78)
    """
    def lookup(env_var: str) -> str | None:
        if env_var in env_vars:
            return env_vars[env_var]
        if env_var in dotenv_values_dict:
            return dotenv_values_dict[env_var]
        return None

    # mode: validated by Pydantic Literal on GuardrailPolicy
    mode = lookup("LANGAGENT_GUARDRAIL_MODE")
    if mode is None:
        mode = builtin_defaults.get("guardrail_mode", "smart")

    # allow_internal_endpoints: lenient boolean parsing
    raw_allow = lookup("LANGAGENT_GUARDRAIL_ALLOW_INTERNAL_ENDPOINTS")
    if raw_allow is None:
        allow_internal_endpoints = bool(
            builtin_defaults.get("guardrail_allow_internal_endpoints", True)
        )
    else:
        allow_internal_endpoints = parse_bool(
            raw_allow, field="LANGAGENT_GUARDRAIL_ALLOW_INTERNAL_ENDPOINTS"
        )

    # internal_endpoint_patterns: CSV with empty item filtering
    raw_patterns = lookup("LANGAGENT_INTERNAL_ENDPOINTS")
    if raw_patterns is None:
        internal_endpoint_patterns = list(
            builtin_defaults.get("guardrail_internal_endpoint_patterns", [])
        )
    else:
        internal_endpoint_patterns = parse_csv_list(raw_patterns)

    return GuardrailPolicy(
        enabled=bool(builtin_defaults.get("guardrail_enabled", True)),
        mode=mode,  # type: ignore[arg-type]  # validated by Pydantic Literal
        redact_pii=bool(builtin_defaults.get("guardrail_redact_pii", True)),
        allow_internal_endpoints=allow_internal_endpoints,
        internal_endpoint_patterns=internal_endpoint_patterns,
    )


def merge_priority_chain(
    cli_args: dict[str, Any],
    env_vars: dict[str, str],
    dotenv_values_dict: dict[str, str],
    builtin_defaults: dict[str, Any],
) -> dict[str, Any]:
    """Merge configuration from all 4 sources following priority chain.
    
    Priority: CLI > env > .env > defaults
    For each field, use the value from the highest-priority source that provides
    a non-None value.
    
    Args:
        cli_args: CLI arguments dict
        env_vars: Environment variables snapshot
        dotenv_values_dict: Parsed .env file
        builtin_defaults: Builtin default values
        
    Returns:
        Merged configuration dict
    """
    merged: dict[str, Any] = {}
    
    # Define field mappings: config_field -> env_var_name
    field_mappings = {
        "model_provider": "MODEL_PROVIDER",
        "model_name": "MODEL_NAME",
        "model_base_url": "MODEL_BASE_URL",
        "checkpointer": "LANGAGENT_CHECKPOINTER",
        "middleware_ids": "LANGAGENT_MIDDLEWARE",
        "skill_dirs": "LANGAGENT_SKILL_DIRS",
        "log_level": "LANGAGENT_LOG_LEVEL",
    }
    
    # Define which fields need CSV parsing
    csv_fields = {"middleware_ids", "skill_dirs"}
    
    for config_field, env_var_name in field_mappings.items():
        # Priority chain: CLI > env > .env > defaults
        value = None
        
        # Check CLI args first (highest priority)
        if config_field in cli_args and cli_args[config_field] is not None:
            value = cli_args[config_field]
        # Check environment variables
        elif env_var_name in env_vars:
            value = env_vars[env_var_name]
            # Parse CSV if needed
            if config_field in csv_fields and isinstance(value, str):
                value = parse_csv_list(value)
        # Check .env file
        elif env_var_name in dotenv_values_dict:
            value = dotenv_values_dict[env_var_name]
            # Parse CSV if needed
            if config_field in csv_fields and isinstance(value, str):
                value = parse_csv_list(value)
        # Fall back to builtin defaults
        elif config_field in builtin_defaults:
            value = builtin_defaults[config_field]
        
        if value is not None:
            merged[config_field] = value
    
    return merged


class RuntimeConfigResolver:
    """Resolves runtime configuration from multiple sources.
    
    This class implements the config_resolve stage (stage 2 of 6) which merges
    configuration from CLI arguments, environment variables, .env files, and
    builtin defaults according to the priority chain: CLI > env > .env > defaults.
    """
    
    @cross_cutting_stage_guard_decorator(
        'config_resolve',
        monkeypatch_blacklist=[BaseChatModel],
    )
    def resolve(self, cli_args: dict[str, Any], agent_dir: str) -> RuntimeConfig:
        """Resolve runtime configuration from all sources.
        
        This method:
        1. Snapshots os.environ
        2. Parses .env file from agent_dir
        3. Merges all sources according to priority chain
        4. Validates required fields and detects placeholders
        5. Constructs frozen RuntimeConfig instance
        6. Emits startup logging
        
        Args:
            cli_args: Command-line arguments as parsed dict
            agent_dir: Path to agent directory
            
        Returns:
            Frozen RuntimeConfig instance with all 13 fields populated
            
        Raises:
            RequiredFieldMissingError: Required field missing (exit code 5)
            ConfigPlaceholderError: Placeholder value detected (exit code 78)
            DotenvMalformedError: .env file parsing failed (exit code 65)
            ValidationError: Invalid enum or type (exit code 78)
        """
        try:
            # 1. Snapshot os.environ
            env_vars = dict(os.environ)
            
            # 2. Parse .env file
            env_path = os.path.join(agent_dir, ".env")
            dotenv_dict = parse_dotenv(env_path)
            
            # 3. Merge all sources according to priority chain
            merged_config = merge_priority_chain(
                cli_args=cli_args,
                env_vars=env_vars,
                dotenv_values_dict=dotenv_dict,
                builtin_defaults=BUILTIN_DEFAULTS,
            )
            
            # 4. Validate required fields
            validate_required_fields(merged_config)
            
            # 5. Validate no placeholders
            validate_no_placeholders(merged_config)
            
            # 6. Construct GuardrailPolicy from environment variables
            guardrail_policy = parse_guardrail_policy(
                env_vars=env_vars,
                dotenv_values_dict=dotenv_dict,
                builtin_defaults=BUILTIN_DEFAULTS,
            )
            
            # 7. Construct frozen RuntimeConfig instance
            config = RuntimeConfig(
                # Source metadata
                cli_args=cli_args.copy(),  # Copy to prevent mutation
                env_vars=env_vars,
                dotenv_values=dotenv_dict,
                builtin_defaults=BUILTIN_DEFAULTS,
                # Model configuration
                model=None,  # Always None from config_resolve stage
                model_provider=merged_config.get("model_provider", "openai-compatible"),
                model_name=merged_config.get("model_name"),
                model_base_url=merged_config.get("model_base_url"),
                # Runtime configuration
                checkpointer=merged_config.get("checkpointer", "memory"),
                middleware_ids=merged_config.get("middleware_ids", []),
                skill_dirs=merged_config.get("skill_dirs", []),
                # Miscellaneous
                log_level=merged_config.get("log_level", "INFO"),
                # Guardrail configuration
                guardrail_policy=guardrail_policy,
            )
            
            # 8. Emit startup logging
            logger.emit("la.runtime.config_resolve.ok", {
                "message": "Configuration resolved successfully",
                "model_provider": config.model_provider,
                "model_name": config.model_name,
                "checkpointer": config.checkpointer,
            })
            
            return config
        
        except (RequiredFieldMissingError, ConfigPlaceholderError, DotenvMalformedError) as e:
            # Emit error logging
            logger.emit("la.runtime.config_resolve.fail", {
                "message": f"Configuration resolution failed: {str(e)}",
                "error_type": type(e).__name__,
            })
            raise
