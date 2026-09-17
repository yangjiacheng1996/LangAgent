"""Primitives layer exceptions with exit codes."""


class ProviderUnsupportedError(Exception):
    """FR-005: model_provider not in 6 supported values."""
    exit_code = 78


class AuthFailedError(Exception):
    """FR-006: Required API key env var missing."""
    exit_code = 78


class EndpointUnreachableError(Exception):
    """FR-007: model_base_url cannot be reached (strict enforcement)."""
    exit_code = 70


class RequiredFieldMissingError(Exception):
    """FR-008: model_base_url is None for providers requiring it."""
    exit_code = 5


class GraphCompileError(Exception):
    """FR-021: LangGraph compilation failed OR SQLite corruption repair failed."""
    exit_code = 70


class ToolBindingError(Exception):
    """FR-022: Tool binding to model failed."""
    exit_code = 70


class CheckpointTypeUnsupportedError(Exception):
    """FR-028: checkpointer not in 3 supported values."""
    exit_code = 78


class StageCapabilityViolationError(Exception):
    """FR-047/FR-048: Capability violated during stage execution (stage guard)."""
    exit_code = 70
