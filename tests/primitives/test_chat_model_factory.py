"""
TDD Tests for ChatModelFactory (Phase 3, User Story 1, T011-T023).

These tests MUST FAIL before implementation (T024-T025).
Tests the non-existent langagent.primitives.chat_model_factory module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pydantic import BaseModel
from typing import Literal, Optional


# ============================================================================
# Stub RuntimeConfig for testing (since implementation doesn't exist yet)
# ============================================================================

class RuntimeConfig(BaseModel, frozen=True):
    """Stub RuntimeConfig matching data-model.md schema."""
    model_provider: Literal["openai", "anthropic", "google", "deepseek", "zhipu", "openai-compatible"]
    model_name: str
    model_base_url: Optional[str] = None


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_env_openai(monkeypatch):
    """Set OPENAI_API_KEY environment variable."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")


@pytest.fixture
def mock_env_anthropic(monkeypatch):
    """Set ANTHROPIC_API_KEY environment variable."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-123")


@pytest.fixture
def mock_env_google(monkeypatch):
    """Set GOOGLE_API_KEY environment variable."""
    monkeypatch.setenv("GOOGLE_API_KEY", "AIza-test-key-123")


@pytest.fixture
def mock_env_deepseek(monkeypatch):
    """Set DEEPSEEK_API_KEY environment variable."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test-key-123")


@pytest.fixture
def mock_env_zhipu(monkeypatch):
    """Set ZHIPUAI_API_KEY environment variable."""
    monkeypatch.setenv("ZHIPUAI_API_KEY", "zhipu-test-key-123")


@pytest.fixture
def mock_endpoint_probe_success():
    """Mock successful endpoint probe."""
    with patch("langagent.primitives.chat_model_factory.requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "model-1"}]}
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_endpoint_probe_failure():
    """Mock failed endpoint probe."""
    with patch("langagent.primitives.chat_model_factory.requests.get") as mock_get:
        mock_get.side_effect = Exception("Connection refused")
        yield mock_get


# ============================================================================
# T011: test_create_openai_default
# ============================================================================

def test_create_openai_default(mock_env_openai, mock_endpoint_probe_success):
    """
    T011: Test OpenAI provider instantiation with default parameters.
    
    Expected behavior:
    - Returns ChatOpenAI instance
    - model_name from config is passed to ChatOpenAI
    - Uses OPENAI_API_KEY from environment
    - No custom base_url
    """
    from langagent.primitives.chat_model_factory import create
    from langchain_openai import ChatOpenAI
    
    config = RuntimeConfig(
        model_provider="openai",
        model_name="gpt-4",
        model_base_url=None
    )
    
    model = create(config)
    
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "gpt-4"


# ============================================================================
# T012: test_create_anthropic_default
# ============================================================================

def test_create_anthropic_default(mock_env_anthropic, mock_endpoint_probe_success):
    """
    T012: Test Anthropic provider instantiation.
    
    Expected behavior:
    - Returns ChatAnthropic instance
    - model_name from config is passed to ChatAnthropic
    - Uses ANTHROPIC_API_KEY from environment
    """
    from langagent.primitives.chat_model_factory import create
    from langchain_anthropic import ChatAnthropic
    
    config = RuntimeConfig(
        model_provider="anthropic",
        model_name="claude-sonnet-4-6",
        model_base_url=None
    )
    
    model = create(config)
    
    assert isinstance(model, ChatAnthropic)
    assert model.model == "claude-sonnet-4-6"


# ============================================================================
# T013: test_create_google_default
# ============================================================================

def test_create_google_default(mock_env_google, mock_endpoint_probe_success):
    """
    T013: Test Google provider instantiation.
    
    Expected behavior:
    - Returns ChatGoogleGenerativeAI instance
    - model_name from config is passed to ChatGoogleGenerativeAI
    - Uses GOOGLE_API_KEY from environment
    """
    from langagent.primitives.chat_model_factory import create
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    config = RuntimeConfig(
        model_provider="google",
        model_name="gemini-pro",
        model_base_url=None
    )
    
    model = create(config)
    
    assert isinstance(model, ChatGoogleGenerativeAI)
    assert model.model == "gemini-pro"


# ============================================================================
# T014: test_create_deepseek_default
# ============================================================================

def test_create_deepseek_default(mock_env_deepseek, mock_endpoint_probe_success):
    """
    T014: Test DeepSeek provider instantiation.
    
    Expected behavior:
    - Returns ChatOpenAI instance (DeepSeek uses OpenAI-compatible endpoint)
    - model_name from config is passed
    - Uses DEEPSEEK_API_KEY from environment
    - Custom base_url is set
    """
    from langagent.primitives.chat_model_factory import create
    from langchain_openai import ChatOpenAI
    
    config = RuntimeConfig(
        model_provider="deepseek",
        model_name="deepseek-chat",
        model_base_url="https://api.deepseek.com/v1"
    )
    
    model = create(config)
    
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "deepseek-chat"
    assert model.openai_api_base == "https://api.deepseek.com/v1"


# ============================================================================
# T015: test_create_zhipu_default
# ============================================================================

def test_create_zhipu_default(mock_env_zhipu, mock_endpoint_probe_success):
    """
    T015: Test Zhipu provider instantiation.
    
    Expected behavior:
    - Returns ChatOpenAI instance (Zhipu uses OpenAI-compatible endpoint)
    - model_name from config is passed
    - Uses ZHIPUAI_API_KEY from environment
    - Custom base_url is set
    """
    from langagent.primitives.chat_model_factory import create
    from langchain_openai import ChatOpenAI
    
    config = RuntimeConfig(
        model_provider="zhipu",
        model_name="glm-4",
        model_base_url="https://open.bigmodel.cn/api/paas/v4"
    )
    
    model = create(config)
    
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "glm-4"
    assert model.openai_api_base == "https://open.bigmodel.cn/api/paas/v4"


# ============================================================================
# T016: test_create_openai_compatible_local
# ============================================================================

def test_create_openai_compatible_local(mock_env_openai, mock_endpoint_probe_success):
    """
    T016: Test OpenAI-compatible local vLLM instantiation.
    
    Expected behavior:
    - Returns ChatOpenAI instance
    - Uses custom base_url (http://10.0.0.5:8000/v1)
    - Uses OPENAI_API_KEY from environment
    """
    from langagent.primitives.chat_model_factory import create
    from langchain_openai import ChatOpenAI
    
    config = RuntimeConfig(
        model_provider="openai-compatible",
        model_name="Qwen/Qwen3.8-27B",
        model_base_url="http://10.0.0.5:8000/v1"
    )
    
    model = create(config)
    
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "Qwen/Qwen3.8-27B"
    assert model.openai_api_base == "http://10.0.0.5:8000/v1"


# ============================================================================
# T017: test_reject_localhost_in_model_base_url
# ============================================================================

def test_reject_localhost_in_model_base_url(mock_env_openai):
    """
    T017: Test localhost rejection in model_base_url (SC-011).
    
    Expected behavior:
    - Raises RequiredFieldMissingError
    - exit_code = 5
    """
    from langagent.primitives.chat_model_factory import create
    from langagent.primitives.exceptions import RequiredFieldMissingError
    
    config = RuntimeConfig(
        model_provider="openai-compatible",
        model_name="local-model",
        model_base_url="http://localhost:8000/v1"
    )
    
    with pytest.raises(RequiredFieldMissingError) as exc_info:
        create(config)
    
    assert exc_info.value.exit_code == 5
    assert "localhost" in str(exc_info.value).lower()


# ============================================================================
# T018: test_reject_127_0_0_1_in_model_base_url
# ============================================================================

def test_reject_127_0_0_1_in_model_base_url(mock_env_openai):
    """
    T018: Test 127.0.0.1 rejection in model_base_url (SC-011).
    
    Expected behavior:
    - Raises RequiredFieldMissingError
    - exit_code = 5
    """
    from langagent.primitives.chat_model_factory import create
    from langagent.primitives.exceptions import RequiredFieldMissingError
    
    config = RuntimeConfig(
        model_provider="openai-compatible",
        model_name="local-model",
        model_base_url="http://127.0.0.1:8000/v1"
    )
    
    with pytest.raises(RequiredFieldMissingError) as exc_info:
        create(config)
    
    assert exc_info.value.exit_code == 5
    assert "127.0.0.1" in str(exc_info.value)


# ============================================================================
# T019: test_reject_rfc1918_private_ips
# ============================================================================

@pytest.mark.parametrize("base_url,ip_pattern", [
    ("http://10.0.0.1:8000/v1", "10.0.0.0/8"),
    ("http://10.255.255.255:8000/v1", "10.0.0.0/8"),
    ("http://172.16.0.1:8000/v1", "172.16.0.0/12"),
    ("http://172.31.255.255:8000/v1", "172.16.0.0/12"),
    ("http://192.168.0.1:8000/v1", "192.168.0.0/16"),
    ("http://192.168.255.255:8000/v1", "192.168.0.0/16"),
])
def test_reject_rfc1918_private_ips(mock_env_openai, base_url, ip_pattern):
    """
    T019: Test RFC1918 private IP rejection (SC-011, FR-004a).
    
    Tests rejection of:
    - 10.0.0.0/8
    - 172.16.0.0/12
    - 192.168.0.0/16
    
    Uses regex pattern: \b(10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|192\.168\.)
    
    Expected behavior:
    - Raises RequiredFieldMissingError
    - exit_code = 5
    """
    from langagent.primitives.chat_model_factory import create
    from langagent.primitives.exceptions import RequiredFieldMissingError
    
    config = RuntimeConfig(
        model_provider="openai-compatible",
        model_name="local-model",
        model_base_url=base_url
    )
    
    with pytest.raises(RequiredFieldMissingError) as exc_info:
        create(config)
    
    assert exc_info.value.exit_code == 5


# ============================================================================
# T020: test_create_unsupported_provider
# ============================================================================

def test_create_unsupported_provider(mock_env_openai):
    """
    T020: Test unsupported provider error (FR-005).
    
    Expected behavior:
    - Raises ProviderUnsupportedError
    - exit_code = 78
    """
    from langagent.primitives.chat_model_factory import create
    from langagent.primitives.exceptions import ProviderUnsupportedError
    
    # Create config with invalid provider using dict and model_validate
    # since Pydantic will validate the Literal at construction time
    config_dict = {
        "model_provider": "unsupported-provider",
        "model_name": "test-model",
        "model_base_url": None
    }
    
    # We need to bypass Pydantic validation for this test
    # In real implementation, validation happens in create() function
    with patch.object(RuntimeConfig, 'model_provider', "unsupported-provider"):
        config = RuntimeConfig.model_construct(**config_dict)
        
        with pytest.raises(ProviderUnsupportedError) as exc_info:
            create(config)
        
        assert exc_info.value.exit_code == 78


# ============================================================================
# T021: test_create_missing_api_key
# ============================================================================

def test_create_missing_api_key(monkeypatch):
    """
    T021: Test missing API key error (FR-006).
    
    Expected behavior:
    - Raises AuthFailedError when required env var is missing
    - exit_code = 78
    """
    from langagent.primitives.chat_model_factory import create
    from langagent.primitives.exceptions import AuthFailedError
    
    # Ensure OPENAI_API_KEY is not set
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    
    config = RuntimeConfig(
        model_provider="openai",
        model_name="gpt-4",
        model_base_url=None
    )
    
    with pytest.raises(AuthFailedError) as exc_info:
        create(config)
    
    assert exc_info.value.exit_code == 78
    assert "OPENAI_API_KEY" in str(exc_info.value)


# ============================================================================
# T022: test_create_endpoint_unreachable
# ============================================================================

def test_create_endpoint_unreachable(mock_env_openai, mock_endpoint_probe_failure):
    """
    T022: Test endpoint unreachable error (FR-007).
    
    Expected behavior:
    - Raises EndpointUnreachableError when endpoint probe fails
    - exit_code = 70
    - Strict enforcement (no degradation to warnings)
    """
    from langagent.primitives.chat_model_factory import create
    from langagent.primitives.exceptions import EndpointUnreachableError
    
    config = RuntimeConfig(
        model_provider="openai-compatible",
        model_name="local-model",
        model_base_url="http://10.0.0.5:8000/v1"
    )
    
    with pytest.raises(EndpointUnreachableError) as exc_info:
        create(config)
    
    assert exc_info.value.exit_code == 70


# ============================================================================
# T023: test_create_preserves_config_immutability
# ============================================================================

def test_create_preserves_config_immutability(mock_env_openai, mock_endpoint_probe_success):
    """
    T023: Test RuntimeConfig immutability guarantee (FR-009).
    
    Expected behavior:
    - config instance ID unchanged after create()
    - No calls to config.model_copy()
    - No field mutations
    """
    from langagent.primitives.chat_model_factory import create
    
    config = RuntimeConfig(
        model_provider="openai",
        model_name="gpt-4",
        model_base_url=None
    )
    
    # Capture original config ID and all field values
    original_id = id(config)
    original_provider = config.model_provider
    original_name = config.model_name
    original_base_url = config.model_base_url
    
    # Create model
    model = create(config)
    
    # Verify config unchanged
    assert id(config) == original_id
    assert config.model_provider == original_provider
    assert config.model_name == original_name
    assert config.model_base_url == original_base_url
    
    # Verify model was created (not None)
    assert model is not None


# ============================================================================
# Additional Test: Verify all 13 tests are present
# ============================================================================

def test_all_thirteen_tests_present():
    """
    Meta-test to verify all 13 required tests (T011-T023) are present.
    """
    import inspect
    import sys
    
    current_module = sys.modules[__name__]
    test_functions = [
        name for name, obj in inspect.getmembers(current_module)
        if inspect.isfunction(obj) and name.startswith("test_")
    ]
    
    required_tests = [
        "test_create_openai_default",
        "test_create_anthropic_default",
        "test_create_google_default",
        "test_create_deepseek_default",
        "test_create_zhipu_default",
        "test_create_openai_compatible_local",
        "test_reject_localhost_in_model_base_url",
        "test_reject_127_0_0_1_in_model_base_url",
        "test_reject_rfc1918_private_ips",
        "test_create_unsupported_provider",
        "test_create_missing_api_key",
        "test_create_endpoint_unreachable",
        "test_create_preserves_config_immutability",
    ]
    
    for test_name in required_tests:
        assert test_name in test_functions, f"Required test '{test_name}' is missing!"


# ============================================================================
# Phase 7: User Story 5 - Stage Logging Integration Tests (T074-T077)
# ============================================================================

def test_create_emits_start_tag(mock_env_openai, mock_endpoint_probe_success):
    """
    T074: Test model_adapt start tag emission.
    
    Expected behavior:
    - Emits la.runtime.model_adapt.start with provider payload
    - MUST FAIL before T087 implementation
    """
    from langagent.primitives.chat_model_factory import create
    
    config = RuntimeConfig(
        model_provider="openai",
        model_name="gpt-4",
        model_base_url=None
    )
    
    with patch("langagent.primitives.chat_model_factory.emit") as mock_emit:
        model = create(config)
        
        # Verify start tag was emitted
        start_calls = [call for call in mock_emit.call_args_list 
                      if call[0][0] == "la.runtime.model_adapt.start"]
        assert len(start_calls) >= 1, "Expected la.runtime.model_adapt.start tag to be emitted"
        
        # Verify payload contains provider
        start_payload = start_calls[0][0][1] if len(start_calls[0][0]) > 1 else {}
        assert "provider" in start_payload, "Start tag payload should contain provider"
        assert start_payload["provider"] == "openai"


def test_create_emits_endpoint_probe_tag(mock_env_openai):
    """
    T075: Test model_adapt endpoint_probe tag emission.
    
    Expected behavior:
    - Emits la.runtime.model_adapt.endpoint_probe with url payload
    - MUST FAIL before T087 implementation
    """
    from langagent.primitives.chat_model_factory import create
    
    config = RuntimeConfig(
        model_provider="openai-compatible",
        model_name="test-model",
        model_base_url="http://10.0.0.5:8000/v1"
    )
    
    with patch("langagent.primitives.chat_model_factory.emit") as mock_emit:
        with patch("langagent.primitives.chat_model_factory.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            model = create(config)
            
            # Verify endpoint_probe tag was emitted
            probe_calls = [call for call in mock_emit.call_args_list 
                          if call[0][0] == "la.runtime.model_adapt.endpoint_probe"]
            assert len(probe_calls) >= 1, "Expected la.runtime.model_adapt.endpoint_probe tag to be emitted"
            
            # Verify payload contains url
            probe_payload = probe_calls[0][0][1] if len(probe_calls[0][0]) > 1 else {}
            assert "url" in probe_payload, "Endpoint probe tag payload should contain url"


def test_create_emits_ok_tag(mock_env_openai, mock_endpoint_probe_success):
    """
    T076: Test model_adapt ok tag emission.
    
    Expected behavior:
    - Emits la.runtime.model_adapt.ok with duration_ms payload
    - MUST FAIL before T087 implementation
    """
    from langagent.primitives.chat_model_factory import create
    
    config = RuntimeConfig(
        model_provider="openai",
        model_name="gpt-4",
        model_base_url=None
    )
    
    with patch("langagent.primitives.chat_model_factory.emit") as mock_emit:
        model = create(config)
        
        # Verify ok tag was emitted
        ok_calls = [call for call in mock_emit.call_args_list 
                   if call[0][0] == "la.runtime.model_adapt.ok"]
        assert len(ok_calls) >= 1, "Expected la.runtime.model_adapt.ok tag to be emitted"
        
        # Verify payload contains duration_ms
        ok_payload = ok_calls[0][0][1] if len(ok_calls[0][0]) > 1 else {}
        assert "duration_ms" in ok_payload, "Ok tag payload should contain duration_ms"
        assert isinstance(ok_payload["duration_ms"], (int, float)), "duration_ms should be numeric"


def test_create_emits_fail_tag(monkeypatch):
    """
    T077: Test model_adapt fail tag emission.
    
    Expected behavior:
    - On AuthFailedError, emits la.runtime.model_adapt.fail 
      with error_type and error_message payload
    - MUST FAIL before T087 implementation
    """
    from langagent.primitives.chat_model_factory import create
    from langagent.primitives.exceptions import AuthFailedError
    
    # Ensure API key is missing to trigger AuthFailedError
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    
    config = RuntimeConfig(
        model_provider="openai",
        model_name="gpt-4",
        model_base_url=None
    )
    
    with patch("langagent.primitives.chat_model_factory.emit") as mock_emit:
        with pytest.raises(AuthFailedError):
            create(config)
        
        # Verify fail tag was emitted
        fail_calls = [call for call in mock_emit.call_args_list 
                     if call[0][0] == "la.runtime.model_adapt.fail"]
        assert len(fail_calls) >= 1, "Expected la.runtime.model_adapt.fail tag to be emitted"
        
        # Verify payload contains error_type and error_message
        fail_payload = fail_calls[0][0][1] if len(fail_calls[0][0]) > 1 else {}
        assert "error_type" in fail_payload, "Fail tag payload should contain error_type"
        assert "error_message" in fail_payload, "Fail tag payload should contain error_message"
