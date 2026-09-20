"""Tests for RuntimeConfigSnapshot model.

Tests cover:
- Exclusion of BaseChatModel instances
- Exclusion of secrets (cli_args, env_vars, dotenv_values)
- JSON serialization
- Factory method construction
"""

import pytest
from pydantic import ValidationError

from langagent.runtime.config_snapshot import RuntimeConfigSnapshot
from langagent.runtime.agent_state import RuntimeConfig, GuardrailPolicy


class TestRuntimeConfigSnapshot:
    """T016, T017: Test RuntimeConfigSnapshot model."""
    
    def test_runtime_config_snapshot_excludes_model(self):
        """T016: Verify snapshot does not include model field."""
        snapshot = RuntimeConfigSnapshot(
            model_provider="openai",
            model_name="gpt-4o",
            checkpointer="memory",
            log_level="INFO"
        )
        
        # Verify model field doesn't exist in serialized output
        json_str = snapshot.model_dump_json()
        assert "BaseChatModel" not in json_str
        
        # Verify model is not in dict representation
        snapshot_dict = snapshot.model_dump()
        assert "model" not in snapshot_dict
    
    def test_runtime_config_snapshot_excludes_secrets(self):
        """T017: Verify snapshot excludes cli_args, env_vars, dotenv_values."""
        snapshot = RuntimeConfigSnapshot(
            model_provider="openai",
            model_name="gpt-4o",
            checkpointer="memory",
            log_level="INFO"
        )
        
        json_str = snapshot.model_dump_json()
        snapshot_dict = snapshot.model_dump()
        
        # Verify secrets not in JSON
        assert "cli_args" not in json_str
        assert "env_vars" not in json_str
        assert "dotenv_values" not in json_str
        assert "builtin_defaults" not in json_str
        assert "API_KEY" not in json_str
        assert "sk-" not in json_str
        
        # Verify secrets not in dict
        assert "cli_args" not in snapshot_dict
        assert "env_vars" not in snapshot_dict
        assert "dotenv_values" not in snapshot_dict
        assert "builtin_defaults" not in snapshot_dict
    
    def test_runtime_config_snapshot_json_serializable(self):
        """Verify snapshot is fully JSON-serializable."""
        snapshot = RuntimeConfigSnapshot(
            model_provider="openai",
            model_name="gpt-4o",
            model_base_url="https://api.openai.com/v1",
            checkpointer="sqlite",
            middleware_ids=["retry", "timeout"],
            skill_dirs=["skills/web", "skills/file"],
            log_level="DEBUG",
            guardrail_allow_internal_endpoints=False
        )
        
        # Should not raise exception
        json_str = snapshot.model_dump_json()
        assert len(json_str) > 0
        
        # Verify key fields present
        assert "openai" in json_str
        assert "gpt-4o" in json_str
        assert "sqlite" in json_str
    
    def test_from_runtime_config_factory(self):
        """Test factory method creates snapshot from RuntimeConfig."""
        config = RuntimeConfig(
            cli_args={"api_key": "sk-secret"},
            env_vars={"OPENAI_API_KEY": "sk-secret"},
            dotenv_values={},
            builtin_defaults={},
            model=None,
            model_provider="openai",
            model_name="gpt-4o",
            model_base_url=None,
            checkpointer="memory",
            middleware_ids=["retry"],
            skill_dirs=["skills"],
            log_level="INFO",
            guardrail_policy=GuardrailPolicy(allow_internal_endpoints=False)
        )
        
        snapshot = RuntimeConfigSnapshot.from_runtime_config(config)
        
        # Verify safe fields copied
        assert snapshot.model_provider == "openai"
        assert snapshot.model_name == "gpt-4o"
        assert snapshot.checkpointer == "memory"
        assert snapshot.middleware_ids == ["retry"]
        assert snapshot.skill_dirs == ["skills"]
        assert snapshot.log_level == "INFO"
        assert snapshot.guardrail_allow_internal_endpoints is False
        
        # Verify secrets excluded
        snapshot_dict = snapshot.model_dump()
        assert "cli_args" not in snapshot_dict
        assert "api_key" not in str(snapshot_dict)
        assert "sk-secret" not in snapshot.model_dump_json()
    
    def test_snapshot_frozen(self):
        """Verify snapshot is immutable."""
        snapshot = RuntimeConfigSnapshot(
            model_provider="openai",
            model_name="gpt-4o",
            checkpointer="memory",
            log_level="INFO"
        )
        
        with pytest.raises(ValidationError):
            snapshot.model_name = "gpt-3.5"
    
    def test_snapshot_schema_version(self):
        """Verify schema_version defaults to v0.2.0."""
        snapshot = RuntimeConfigSnapshot(
            model_provider="openai",
            model_name="gpt-4o",
            checkpointer="memory",
            log_level="INFO"
        )
        
        assert snapshot.schema_version == "v0.2.0"
