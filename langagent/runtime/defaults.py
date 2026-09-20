"""Builtin default values for RuntimeConfig fields.

These defaults provide sensible starting values that can be overridden
by .env files, environment variables, or CLI arguments following the
priority chain: CLI > env > .env > defaults.
"""

from typing import Any

# Builtin defaults for RuntimeConfig
# Note: model_name is intentionally None to force users to explicitly configure it
BUILTIN_DEFAULTS: dict[str, Any] = {
    "model_provider": "openai-compatible",
    "model_name": None,  # Required field - user must explicitly configure
    "model_base_url": None,
    "checkpointer": "memory",
    "middleware_ids": [],
    "skill_dirs": [],
    "log_level": "INFO",
    # GuardrailPolicy defaults
    "guardrail_enabled": True,
    "guardrail_mode": "smart",
    "guardrail_redact_pii": True,
    "guardrail_allow_internal_endpoints": True,
    "guardrail_internal_endpoint_patterns": [],
}
