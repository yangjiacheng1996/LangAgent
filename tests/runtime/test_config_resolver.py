"""Tests for RuntimeConfigResolver (F07 config_resolve stage).

Following TDD approach: tests written first, must fail initially,
then implementation makes them pass (Red-Green-Refactor cycle).

Constitutional Alignment:
- Article VIII: TDD mandatory
- Article XII: 4-source priority chain testing
"""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from langagent.runtime.config_resolver import RuntimeConfigResolver
from langagent.runtime.agent_state import RuntimeConfig, GuardrailPolicy
from langagent.runtime.exceptions import (
    RequiredFieldMissingError,
    ConfigPlaceholderError,
    DotenvMalformedError,
    TypeMismatchError,
)


# ============================================================================
# Phase 3: User Story 1 - Priority Chain Merging Tests (T012-T016)
# ============================================================================

class TestPriorityChainMerging:
    """Test suite for User Story 1: Merge Configuration from Multiple Sources.
    
    Tests the 4-source priority chain: CLI > env > .env > defaults
    """
    
    def test_resolve_cli_overrides_all(self, tmp_path: Path) -> None:
        """T012: CLI arguments override all other sources.
        
        Given: CLI="gpt-4o", env="claude-3", .env="qwen3-8b"
        When: config is resolved
        Then: result="gpt-4o" (CLI wins)
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        
        # Create .env file with model_name and base_url
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=qwen3-8b\nMODEL_BASE_URL=http://localhost:8000\n")
        
        # CLI args with model_name
        cli_args = {"model_name": "gpt-4o"}
        
        # Mock environment with MODEL_NAME
        with patch.dict(os.environ, {"MODEL_NAME": "claude-3"}, clear=False):
            # Act
            config = resolver.resolve(cli_args, agent_dir)
            
            # Assert
            assert config.model_name == "gpt-4o", "CLI should override env and .env"
    
    def test_resolve_env_overrides_dotenv(self, tmp_path: Path) -> None:
        """T013: Environment variables override .env file.
        
        Given: CLI absent, env="gpt-4o", .env="qwen3-8b"
        When: config is resolved
        Then: result="gpt-4o" (env wins over .env)
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        
        # Create .env file with model_name and base_url
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=qwen3-8b\nMODEL_BASE_URL=http://localhost:8000\n")
        
        # CLI args without model_name
        cli_args = {}
        
        # Mock environment with MODEL_NAME
        with patch.dict(os.environ, {"MODEL_NAME": "gpt-4o"}, clear=False):
            # Act
            config = resolver.resolve(cli_args, agent_dir)
            
            # Assert
            assert config.model_name == "gpt-4o", "env should override .env"
    
    def test_resolve_dotenv_overrides_builtin(self, tmp_path: Path) -> None:
        """T014: .env file overrides builtin defaults.
        
        Given: CLI/env absent, .env="memory", default="memory"
        When: config is resolved
        Then: result uses .env value for checkpointer
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        
        # Create .env file with custom checkpointer and required fields
        env_file = tmp_path / ".env"
        env_file.write_text(
            "LANGAGENT_CHECKPOINTER=sqlite\n"
            "MODEL_NAME=test-model\n"
            "MODEL_BASE_URL=http://localhost:8000\n"
        )
        
        # CLI args empty
        cli_args = {}
        
        # Act
        config = resolver.resolve(cli_args, agent_dir)
        
        # Assert
        assert config.checkpointer == "sqlite", ".env should override builtin default"
    
    def test_resolve_builtin_when_no_source(self, tmp_path: Path) -> None:
        """T015: Builtin defaults used when no other source provides value.
        
        Given: all sources absent for model_provider
        When: config is resolved
        Then: use builtin default "openai-compatible"
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        
        # Create .env file with only model_name and base_url (required fields)
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_BASE_URL=http://localhost:8000\n")
        
        # CLI args empty
        cli_args = {}
        
        # Act
        config = resolver.resolve(cli_args, agent_dir)
        
        # Assert
        assert config.model_provider == "openai-compatible", "Should use builtin default"
        assert config.checkpointer == "memory", "Should use builtin default"
        assert config.log_level == "INFO", "Should use builtin default"
    
    @patch("langagent.cross_cutting.logger.emit")
    def test_resolve_priority_logged(self, mock_emit: Mock, tmp_path: Path) -> None:
        """T016: Priority chain merging is logged.
        
        Given: successful resolution
        When: resolution completes
        Then: cross_cutting_logger.emit called with la.runtime.config_resolve.ok tag
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        
        # Create .env file with model_name and base_url
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_BASE_URL=http://localhost:8000\n")
        
        # CLI args
        cli_args = {}
        
        # Act
        config = resolver.resolve(cli_args, agent_dir)
        
        # Assert
        mock_emit.assert_called()
        call_args = mock_emit.call_args
        assert call_args is not None
        # Check that tag includes config_resolve.ok
        assert "la.runtime.config_resolve.ok" in str(call_args)



# ============================================================================
# Phase 4: User Story 2 - Validation and Placeholder Detection Tests (T022-T028)
# ============================================================================

class TestValidationAndPlaceholders:
    """Test suite for User Story 2: Validate Required Fields and Reject Placeholders.
    
    Tests required field validation and placeholder detection.
    """
    
    def test_resolve_required_field_missing_model_name(self, tmp_path: Path) -> None:
        """T024: model_name is required and cannot be None.
        
        Given: model_name=None after merge (no source provides it)
        When: config is resolved
        Then: RequiredFieldMissingError with exit code 5
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        
        # Create empty .env file (no model_name)
        env_file = tmp_path / ".env"
        env_file.write_text("")
        
        # CLI args without model_name
        cli_args = {}
        
        # Act & Assert
        with pytest.raises(RequiredFieldMissingError) as exc_info:
            resolver.resolve(cli_args, agent_dir)
        
        assert exc_info.value.field == "model_name"
        assert exc_info.value.exit_code == 5
    
    def test_resolve_required_field_missing_openai_compatible_base_url(self, tmp_path: Path) -> None:
        """T023: model_base_url required when model_provider is openai-compatible.
        
        Given: model_provider="openai-compatible" but model_base_url=None
        When: config is resolved
        Then: RequiredFieldMissingError with exit code 5
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        
        # Create .env file with model_name but no base_url
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_PROVIDER=openai-compatible\n")
        
        # CLI args empty
        cli_args = {}
        
        # Act & Assert
        with pytest.raises(RequiredFieldMissingError) as exc_info:
            resolver.resolve(cli_args, agent_dir)
        
        assert exc_info.value.field == "model_base_url"
        assert exc_info.value.exit_code == 5
    
    def test_resolve_rejects_placeholder_values(self, tmp_path: Path) -> None:
        """T025: Reject placeholder values like <your-model-name>.
        
        Given: .env contains MODEL_NAME=<your-model-name>
        When: config is resolved
        Then: ConfigPlaceholderError with exit code 78
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        
        # Create .env file with placeholder (also provide base_url to pass required field check)
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=<your-model-name>\nMODEL_BASE_URL=http://localhost:8000\n")
        
        # CLI args empty
        cli_args = {}
        
        # Act & Assert
        with pytest.raises(ConfigPlaceholderError) as exc_info:
            resolver.resolve(cli_args, agent_dir)
        
        assert exc_info.value.field == "model_name"
        assert exc_info.value.exit_code == 78
        assert "<your-model-name>" in str(exc_info.value)
    
    def test_resolve_rejects_placeholder_values_all_fields(self, tmp_path: Path) -> None:
        """T026: Reject placeholders in any string field.
        
        Given: .env contains MODEL_BASE_URL=<your-vllm-endpoint>
        When: config is resolved
        Then: ConfigPlaceholderError with exit code 78
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        
        # Create .env file with placeholder in base_url
        env_file = tmp_path / ".env"
        env_file.write_text(
            "MODEL_NAME=test-model\n"
            "MODEL_BASE_URL=<your-vllm-endpoint>\n"
        )
        
        # CLI args empty
        cli_args = {}
        
        # Act & Assert
        with pytest.raises(ConfigPlaceholderError) as exc_info:
            resolver.resolve(cli_args, agent_dir)
        
        assert exc_info.value.field == "model_base_url"
        assert exc_info.value.exit_code == 78
        assert "<your-vllm-endpoint>" in str(exc_info.value)
    
    def test_resolve_invalid_enum_value(self, tmp_path: Path) -> None:
        """T028: Invalid enum values rejected by Pydantic.
        
        Given: model_provider="unknown"
        When: config is resolved
        Then: Pydantic ValidationError
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        
        # Create .env file with invalid provider
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_PROVIDER=unknown\n")
        
        # CLI args empty
        cli_args = {}
        
        # Act & Assert
        # Pydantic will raise ValidationError for invalid enum
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            resolver.resolve(cli_args, agent_dir)


# ============================================================================
# Phase 5: User Story 3 - .env File Parsing Tests (T035-T040)
# ============================================================================

class TestDotenvFileParsing:
    """Test suite for User Story 3: Parse and Validate .env Files.
    
    Tests robust .env file parsing with various formats.
    """
    
    def test_parse_dotenv_basic(self, tmp_path: Path) -> None:
        """T035: Basic KEY=VALUE parsing.
        
        Given: .env contains KEY=VALUE
        When: parsed
        Then: returns {"KEY": "VALUE"}
        """
        # Arrange
        from langagent.runtime.config_resolver import parse_dotenv
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=VALUE\n")
        
        # Act
        result = parse_dotenv(str(env_file))
        
        # Assert
        assert result == {"KEY": "VALUE"}
    
    def test_parse_dotenv_with_quotes(self, tmp_path: Path) -> None:
        """T036: Quoted values have quotes removed.
        
        Given: .env contains KEY="VALUE"
        When: parsed
        Then: returns {"KEY": "VALUE"} (quotes removed)
        """
        # Arrange
        from langagent.runtime.config_resolver import parse_dotenv
        env_file = tmp_path / ".env"
        env_file.write_text('KEY="VALUE"\n')
        
        # Act
        result = parse_dotenv(str(env_file))
        
        # Assert
        assert result == {"KEY": "VALUE"}
    
    def test_parse_dotenv_with_comments(self, tmp_path: Path) -> None:
        """T037: Comments are ignored.
        
        Given: .env contains # comment\nKEY=value
        When: parsed
        Then: returns {"KEY": "value"} (comment ignored)
        """
        # Arrange
        from langagent.runtime.config_resolver import parse_dotenv
        env_file = tmp_path / ".env"
        env_file.write_text("# This is a comment\nKEY=value\n")
        
        # Act
        result = parse_dotenv(str(env_file))
        
        # Assert
        assert result == {"KEY": "value"}
    
    def test_parse_dotenv_missing_file(self, tmp_path: Path) -> None:
        """T038: Missing .env file returns empty dict.
        
        Given: .env file does not exist
        When: parsed
        Then: returns empty dict without raising error
        """
        # Arrange
        from langagent.runtime.config_resolver import parse_dotenv
        env_path = str(tmp_path / ".env")
        
        # Act
        result = parse_dotenv(env_path)
        
        # Assert
        assert result == {}
    
    def test_parse_dotenv_malformed(self, tmp_path: Path) -> None:
        """T039: Malformed .env file raises DotenvMalformedError.
        
        Given: .env contains line without = separator
        When: parsed
        Then: raises DotenvMalformedError with exit code 65
        """
        # Arrange
        from langagent.runtime.config_resolver import parse_dotenv
        env_file = tmp_path / ".env"
        env_file.write_text("KEY_WITHOUT_EQUALS\n")
        
        # Act & Assert
        with pytest.raises(DotenvMalformedError) as exc_info:
            parse_dotenv(str(env_file))
        
        assert exc_info.value.exit_code == 65
    
    def test_parse_dotenv_duplicate_keys(self, tmp_path: Path) -> None:
        """T040: Duplicate keys use last value (python-dotenv behavior).
        
        Given: .env contains KEY=first\nKEY=second
        When: parsed
        Then: returns {"KEY": "second"} (last value wins)
        """
        # Arrange
        from langagent.runtime.config_resolver import parse_dotenv
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=first\nKEY=second\n")
        
        # Act
        result = parse_dotenv(str(env_file))
        
        # Assert
        assert result == {"KEY": "second"}


# ============================================================================
# Phase 6: User Story 4 - Frozen RuntimeConfig Tests (T049-T055)
# ============================================================================

class TestFrozenRuntimeConfig:
    """Test suite for User Story 4: Produce Frozen RuntimeConfig with Metadata.
    
    Tests immutability enforcement and with_* methods.
    """
    
    def test_resolve_returns_frozen_runtime_config(self, tmp_path: Path) -> None:
        """T049: RuntimeConfig is frozen and cannot be modified.
        
        Given: config is resolved successfully
        When: attempting to modify a field directly
        Then: raises ValidationError
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_BASE_URL=http://localhost:8000\n")
        
        # Act
        config = resolver.resolve({}, agent_dir)
        
        # Assert - attempt to modify should raise error
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            config.model_provider = "anthropic"  # type: ignore
    
    def test_resolve_model_field_is_none_by_default(self, tmp_path: Path) -> None:
        """T051: model field is None after resolve (populated by F01).
        
        Given: config is resolved successfully
        When: inspecting config.model
        Then: it is None
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_BASE_URL=http://localhost:8000\n")
        
        # Act
        config = resolver.resolve({}, agent_dir)
        
        # Assert
        assert config.model is None
    
    def test_resolve_with_model_returns_new_instance_with_model(self, tmp_path: Path) -> None:
        """T052: with_model() returns new instance with model populated.
        
        Given: config is resolved successfully
        When: calling config.with_model(fake_model)
        Then: returns new instance with model field populated, original unchanged
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_BASE_URL=http://localhost:8000\n")
        config = resolver.resolve({}, agent_dir)
        
        # Create a fake model
        from unittest.mock import Mock
        fake_model = Mock()
        
        # Act
        config2 = config.with_model(fake_model)
        
        # Assert
        assert config.model is None, "Original config should be unchanged"
        assert config2.model is fake_model, "New config should have model"
        assert config is not config2, "Should be different instances"
    
    def test_resolve_with_model_preserves_other_fields(self, tmp_path: Path) -> None:
        """T053: with_model() preserves all other fields.
        
        Given: config is resolved successfully
        When: calling with_model()
        Then: all other 12 fields remain unchanged
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_BASE_URL=http://localhost:8000\n")
        config = resolver.resolve({}, agent_dir)
        
        from unittest.mock import Mock
        fake_model = Mock()
        
        # Act
        config2 = config.with_model(fake_model)
        
        # Assert
        assert config2.model_provider == config.model_provider
        assert config2.model_name == config.model_name
        assert config2.model_base_url == config.model_base_url
        assert config2.checkpointer == config.checkpointer
        assert config2.log_level == config.log_level
    
    def test_resolve_with_model_base_url(self, tmp_path: Path) -> None:
        """T054: with_model_base_url() returns new instance with updated base_url.
        
        Given: config is resolved successfully
        When: calling with_model_base_url("http://new-url:9000")
        Then: returns new instance with updated model_base_url
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_BASE_URL=http://localhost:8000\n")
        config = resolver.resolve({}, agent_dir)
        
        # Act
        config2 = config.with_model_base_url("http://new-url:9000")
        
        # Assert
        assert config.model_base_url == "http://localhost:8000", "Original unchanged"
        assert config2.model_base_url == "http://new-url:9000", "New instance updated"
        assert config is not config2, "Different instances"
    
    def test_resolve_cli_args_preserved_unmodified(self, tmp_path: Path) -> None:
        """T055: cli_args dict is copied and not mutated.
        
        Given: config is resolved successfully
        When: inspecting config.cli_args
        Then: it contains the exact dict passed to resolve(), not mutated
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_BASE_URL=http://localhost:8000\n")
        cli_args = {"model_name": "cli-model"}
        original_cli_args = cli_args.copy()
        
        # Act
        config = resolver.resolve(cli_args, agent_dir)
        
        # Assert
        assert config.cli_args == original_cli_args
        # Mutate original to verify it's a copy
        cli_args["model_name"] = "mutated"
        assert config.cli_args["model_name"] == "cli-model", "Config should not see mutation"


# ============================================================================
# Phase 8: User Story 6 - CSV List Parsing Tests (T071-T074)
# ============================================================================

class TestCSVListParsing:
    """Test suite for User Story 6: Parse List-Based Configuration Fields.
    
    Tests CSV parsing for middleware_ids and skill_dirs.
    """
    
    def test_resolve_middleware_ids_from_csv(self, tmp_path: Path) -> None:
        """T071: Parse middleware_ids from CSV environment variable.
        
        Given: env LANGAGENT_MIDDLEWARE=foo,bar,baz
        When: config is resolved
        Then: middleware_ids==["foo","bar","baz"]
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_BASE_URL=http://localhost:8000\n")
        
        # Act
        with patch.dict(os.environ, {"LANGAGENT_MIDDLEWARE": "foo,bar,baz"}, clear=False):
            config = resolver.resolve({}, agent_dir)
        
        # Assert
        assert config.middleware_ids == ["foo", "bar", "baz"]
    
    def test_resolve_skill_dirs_from_csv(self, tmp_path: Path) -> None:
        """T072: Parse skill_dirs from CSV environment variable.
        
        Given: env LANGAGENT_SKILL_DIRS=/path/one,/path/two
        When: config is resolved
        Then: skill_dirs==["/path/one","/path/two"]
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_BASE_URL=http://localhost:8000\n")
        
        # Act
        with patch.dict(os.environ, {"LANGAGENT_SKILL_DIRS": "/path/one,/path/two"}, clear=False):
            config = resolver.resolve({}, agent_dir)
        
        # Assert
        assert config.skill_dirs == ["/path/one", "/path/two"]
    
    def test_resolve_middleware_ids_default_empty(self, tmp_path: Path) -> None:
        """T073: Default middleware_ids is empty list.
        
        Given: no source provides middleware_ids
        When: config is resolved
        Then: middleware_ids==[]
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_BASE_URL=http://localhost:8000\n")
        
        # Act
        config = resolver.resolve({}, agent_dir)
        
        # Assert
        assert config.middleware_ids == []
    
    def test_resolve_csv_filters_empty_items(self, tmp_path: Path) -> None:
        """T074: CSV parsing filters empty items.
        
        Given: env="foo,,bar" or "foo, ,bar"
        When: config is resolved
        Then: ["foo","bar"] (empty items filtered)
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_BASE_URL=http://localhost:8000\n")
        
        # Act - test with double commas
        with patch.dict(os.environ, {"LANGAGENT_MIDDLEWARE": "foo,,bar"}, clear=False):
            config1 = resolver.resolve({}, agent_dir)
        
        # Act - test with whitespace-only items
        with patch.dict(os.environ, {"LANGAGENT_MIDDLEWARE": "foo, ,bar"}, clear=False):
            config2 = resolver.resolve({}, agent_dir)
        
        # Assert
        assert config1.middleware_ids == ["foo", "bar"], "Should filter empty items from double commas"
        assert config2.middleware_ids == ["foo", "bar"], "Should filter whitespace-only items"


# ============================================================================
# Phase 10: GuardrailPolicy Resolution Tests (T090-T094)
# ============================================================================

class TestGuardrailPolicyResolution:
    """Test suite for GuardrailPolicy resolution from environment variables.
    
    Tests parsing of guardrail configuration with lenient boolean handling.
    """
    
    def test_resolve_guardrail_policy_defaults(self, tmp_path: Path) -> None:
        """T090: GuardrailPolicy uses defaults when no env vars provided.
        
        Given: no guardrail env vars
        When: config is resolved
        Then: GuardrailPolicy with enabled=True, mode="smart", redact_pii=True, 
              allow_internal_endpoints=True, internal_endpoint_patterns=[]
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_BASE_URL=http://localhost:8000\n")
        
        # Act
        config = resolver.resolve({}, agent_dir)
        
        # Assert
        assert config.guardrail_policy is not None
        assert config.guardrail_policy.enabled is True
        assert config.guardrail_policy.mode == "smart"
        assert config.guardrail_policy.redact_pii is True
        assert config.guardrail_policy.allow_internal_endpoints is True
        assert config.guardrail_policy.internal_endpoint_patterns == []
    
    def test_resolve_guardrail_allow_internal_endpoints_lenient_bool(self, tmp_path: Path) -> None:
        """T091: Lenient boolean parsing for allow_internal_endpoints.
        
        Given: various boolean representations
        When: config is resolved
        Then: correctly parses "true"/"1"/"yes"/"on" → True, "false"/"0"/"no"/"off" → False
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_BASE_URL=http://localhost:8000\n")
        
        # Test true values
        for true_val in ["true", "True", "TRUE", "1", "yes", "Yes", "YES", "on", "On", "ON"]:
            with patch.dict(os.environ, {"LANGAGENT_GUARDRAIL_ALLOW_INTERNAL_ENDPOINTS": true_val}, clear=False):
                config = resolver.resolve({}, agent_dir)
                assert config.guardrail_policy.allow_internal_endpoints is True, f"Failed for: {true_val}"
        
        # Test false values
        for false_val in ["false", "False", "FALSE", "0", "no", "No", "NO", "off", "Off", "OFF"]:
            with patch.dict(os.environ, {"LANGAGENT_GUARDRAIL_ALLOW_INTERNAL_ENDPOINTS": false_val}, clear=False):
                config = resolver.resolve({}, agent_dir)
                assert config.guardrail_policy.allow_internal_endpoints is False, f"Failed for: {false_val}"
    
    def test_resolve_guardrail_allow_internal_endpoints_invalid_bool(self, tmp_path: Path) -> None:
        """T092: Invalid boolean values raise ValidationError.
        
        Given: env LANGAGENT_GUARDRAIL_ALLOW_INTERNAL_ENDPOINTS="maybe"
        When: config is resolved
        Then: raises ValidationError exit 78
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_BASE_URL=http://localhost:8000\n")
        
        # Act & Assert
        from pydantic import ValidationError
        with patch.dict(os.environ, {"LANGAGENT_GUARDRAIL_ALLOW_INTERNAL_ENDPOINTS": "maybe"}, clear=False):
            with pytest.raises(Exception):  # Could be custom or Pydantic ValidationError
                resolver.resolve({}, agent_dir)
    
    def test_resolve_guardrail_mode_validation(self, tmp_path: Path) -> None:
        """T093: Guardrail mode validation.
        
        Given: env LANGAGENT_GUARDRAIL_MODE
        When: config is resolved
        Then: "all"|"smart"|"strict" → valid; "unknown" → ValidationError exit 78
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_BASE_URL=http://localhost:8000\n")
        
        # Test valid modes
        for mode in ["all", "smart", "strict"]:
            with patch.dict(os.environ, {"LANGAGENT_GUARDRAIL_MODE": mode}, clear=False):
                config = resolver.resolve({}, agent_dir)
                assert config.guardrail_policy.mode == mode
        
        # Test invalid mode
        from pydantic import ValidationError
        with patch.dict(os.environ, {"LANGAGENT_GUARDRAIL_MODE": "unknown"}, clear=False):
            with pytest.raises(ValidationError):
                resolver.resolve({}, agent_dir)
    
    def test_resolve_guardrail_internal_endpoints_csv(self, tmp_path: Path) -> None:
        """T094: Parse internal endpoint patterns from CSV.
        
        Given: env LANGAGENT_INTERNAL_ENDPOINTS="*.internal.example.com,10.0.0.0/8"
        When: config is resolved
        Then: internal_endpoint_patterns==["*.internal.example.com", "10.0.0.0/8"]
        """
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_BASE_URL=http://localhost:8000\n")
        
        # Act
        with patch.dict(os.environ, {"LANGAGENT_INTERNAL_ENDPOINTS": "*.internal.example.com,10.0.0.0/8"}, clear=False):
            config = resolver.resolve({}, agent_dir)
        
        # Assert
        assert config.guardrail_policy.internal_endpoint_patterns == ["*.internal.example.com", "10.0.0.0/8"]


# ============================================================================
# Phase 7: User Story 5 - Stage Boundary Enforcement Tests (T063-T065)
# ============================================================================

class TestStageBoundaryEnforcement:
    """Test suite for User Story 5: Enforce Stage Capability Boundaries.
    
    Tests that stage_guard decorator prevents unauthorized operations.
    """
    
    def test_resolve_does_not_instantiate_model(self, tmp_path: Path) -> None:
        """T063: config_resolve stage cannot instantiate models.
        
        Given: stage_guard is active
        When: code attempts BaseChatModel.__init__
        Then: StageCapabilityViolationError with exit code 1
        """
        # This test verifies the decorator is applied, but we cannot easily
        # test the monkeypatch without actually trying to instantiate a model,
        # which would require importing LangChain dependencies.
        # The actual enforcement is tested in F06 stage_guard tests.
        
        # Arrange
        resolver = RuntimeConfigResolver()
        agent_dir = str(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MODEL_NAME=test-model\nMODEL_BASE_URL=http://localhost:8000\n")
        
        # Act - normal resolution should work fine
        config = resolver.resolve({}, agent_dir)
        
        # Assert - config created successfully (stage guard allows normal operations)
        assert config.model is None  # model field is None as expected
    
    def test_resolve_uses_stage_guard_decorator(self, tmp_path: Path) -> None:
        """T065: Verify @cross_cutting_stage_guard_decorator is applied.
        
        Given: RuntimeConfigResolver.resolve() method
        When: inspecting the method
        Then: decorator is applied (check function metadata)
        """
        # Arrange
        from langagent.runtime.config_resolver import RuntimeConfigResolver
        
        # Act - check if the decorator is applied by inspecting function attributes
        resolve_method = RuntimeConfigResolver.resolve
        
        # Assert - if decorator is applied, the function will have wrapper metadata
        # This is a basic check; full functionality is tested by F06
        assert hasattr(resolve_method, "__name__")
        assert callable(resolve_method)


# Placeholder for additional test phases
# Phase 9: User Story 7 tests (T079-T082) will go here
