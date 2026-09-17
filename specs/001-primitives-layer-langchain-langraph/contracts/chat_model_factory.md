# Contract: chat_model_factory

**Module**: `langagent.primitives.chat_model_factory`  
**Owner**: F01 Primitives Layer  
**Version**: 1.0.0

---

## Overview

The `chat_model_factory` module provides a single factory function to instantiate LangChain `BaseChatModel` instances based on `RuntimeConfig`. This is the sole entry point for model instantiation across LangAgent, enforcing the architectural boundary that only primitives layer may import LangChain provider packages directly (宪法第 II 条).

---

## Public Interface

### `create(config: RuntimeConfig) -> BaseChatModel`

Instantiate a model based on `config.model_provider`.

**Supported Providers** (FR-001):
- `openai`: OpenAI GPT models (GPT-4, GPT-3.5, etc.)
- `anthropic`: Anthropic Claude models
- `google`: Google Gemini models
- `deepseek`: DeepSeek models (via OpenAI-compatible endpoint)
- `zhipu`: Zhipu AI models (via OpenAI-compatible endpoint)
- `openai-compatible`: Generic OpenAI-compatible endpoint (e.g., local vLLM)

**Parameters**:
- `config: RuntimeConfig` - Frozen configuration snapshot containing:
  - `model_provider: str` - One of 6 supported values
  - `model_name: str` - Model identifier (e.g., "gpt-4", "claude-sonnet-4-6")
  - `model_base_url: str | None` - Custom endpoint URL (required for deepseek/zhipu/openai-compatible)

**Returns**:
- `BaseChatModel` - Instantiated model ready for invocation

**Raises**:
- `ProviderUnsupportedError` (exit code 78) - `model_provider` not in 6 supported values (FR-005)
- `AuthFailedError` (exit code 78) - Required API key environment variable missing (FR-006)
- `EndpointUnreachableError` (exit code 70) - Endpoint probe failed; strict enforcement, no degradation to warnings (FR-007, clarification Q1)
- `RequiredFieldMissingError` (exit code 5) - `model_base_url` is None for providers requiring it (FR-008)

**Side Effects**:
- Reads API key from environment variables:
  - `OPENAI_API_KEY` (for openai, openai-compatible)
  - `ANTHROPIC_API_KEY` (for anthropic)
  - `GOOGLE_API_KEY` (for google)
  - `DEEPSEEK_API_KEY` (for deepseek)
  - `ZHIPUAI_API_KEY` (for zhipu)
- Executes endpoint probe (HTTP request to `/models` or equivalent) to verify connectivity (FR-007)
- Emits 4 log tags via `cross_cutting_logger.emit()`:
  - `la.runtime.model_adapt.start` - Function entry
  - `la.runtime.model_adapt.endpoint_probe` - Before/after probe
  - `la.runtime.model_adapt.ok` - Success path
  - `la.runtime.model_adapt.fail` - Error path

**Immutability Guarantee** (FR-009):
- Does NOT modify `config` parameter
- Does NOT call `config.model_copy()` or mutate any fields
- Returns new `BaseChatModel` instance only; config reconstruction is F10's responsibility (review.md S-1)

**Stage Guard** (FR-045):
```python
@cross_cutting_stage_guard_decorator(
    'model_adapt',
    monkeypatch_blacklist=[RuntimeDirLoader.load, RuntimeConfigResolver.resolve]
)
def create(config: RuntimeConfig) -> BaseChatModel:
    ...
```

Decorator raises `StageCapabilityViolationError` if blacklisted operations attempted.

---

## Usage Example

```python
from langagent.primitives.chat_model_factory import create
from langagent.runtime.config import RuntimeConfig

# OpenAI model
config = RuntimeConfig(
    model_provider="openai",
    model_name="gpt-4",
    model_base_url=None,
    ...
)
model = create(config)  # Returns ChatOpenAI instance

# Local vLLM (OpenAI-compatible)
config = RuntimeConfig(
    model_provider="openai-compatible",
    model_name="Qwen/Qwen3.8-27B",
    model_base_url="http://10.0.0.5:8000/v1",
    ...
)
model = create(config)  # Returns ChatOpenAI with custom base_url

# Anthropic model
config = RuntimeConfig(
    model_provider="anthropic",
    model_name="claude-sonnet-4-6",
    model_base_url=None,
    ...
)
model = create(config)  # Returns ChatAnthropic instance
```

---

## Implementation Notes

### Provider Mapping (from research.md Decision 1)

| config.model_provider | LangChain Class | Required Env Var | base_url Required? |
|----------------------|-----------------|------------------|-------------------|
| `openai` | `langchain_openai.ChatOpenAI` | `OPENAI_API_KEY` | No |
| `anthropic` | `langchain_anthropic.ChatAnthropic` | `ANTHROPIC_API_KEY` | No |
| `google` | `langchain_google_genai.ChatGoogleGenerativeAI` | `GOOGLE_API_KEY` | No |
| `deepseek` | `langchain_openai.ChatOpenAI` | `DEEPSEEK_API_KEY` | Yes |
| `zhipu` | `langchain_openai.ChatOpenAI` | `ZHIPUAI_API_KEY` | Yes |
| `openai-compatible` | `langchain_openai.ChatOpenAI` | Provider-specific | Yes |

### Endpoint Probe Logic (clarification Q1)

Per research.md Decision 1 and clarification Q1:
- Probe executes HTTP GET to `{base_url}/models` (or provider equivalent)
- Timeout: 5 seconds
- **On failure**: Immediately raise `EndpointUnreachableError` (exit code 70)
- **No degradation**: Cannot bypass probe with warnings; strict quality enforcement

### Constructor Parameters

All providers support common parameters:
- `model: str` - Model name from `config.model_name`
- `temperature: float | None` - From config (optional)
- `max_tokens: int | None` - From config (optional)
- `timeout: float` - Default 30s
- `max_retries: int` - Default 6

OpenAI-compatible providers add:
- `base_url: str` - From `config.model_base_url`
- `api_key: str` - From environment variable

### Error Handling Precedence

1. Validate `model_provider` in allowed list → `ProviderUnsupportedError`
2. Check required env var present → `AuthFailedError`
3. Validate `model_base_url` present for providers requiring it → `RequiredFieldMissingError`
4. Execute endpoint probe → `EndpointUnreachableError` on failure
5. Instantiate model class → Propagate LangChain exceptions as-is

---

## Testing Contract

### Unit Tests

1. `test_create_openai_default` - OpenAI with valid key, default parameters
2. `test_create_anthropic_default` - Anthropic with valid key
3. `test_create_google_default` - Google with valid key
4. `test_create_deepseek_with_base_url` - DeepSeek with custom base_url
5. `test_create_zhipu_with_base_url` - Zhipu with custom base_url
6. `test_create_openai_compatible_local` - Local vLLM at http://10.0.0.5:8000/v1
7. `test_create_unsupported_provider` - Raises `ProviderUnsupportedError`
8. `test_create_missing_api_key` - Raises `AuthFailedError`
9. `test_create_missing_base_url` - Raises `RequiredFieldMissingError`
10. `test_create_endpoint_unreachable` - Raises `EndpointUnreachableError`
11. `test_create_config_immutability` - Verify config instance ID unchanged
12. `test_create_emits_start_tag` - Mock logger, verify start tag emitted
13. `test_create_emits_ok_tag` - Mock logger, verify ok tag emitted

### Integration Tests

1. `test_create_invoke_openai` - Create OpenAI model, invoke with test prompt
2. `test_create_invoke_local_vllm` - Create local vLLM model, invoke (skip if unreachable)

---

## Dependencies

**Imports**:
```python
from langagent.runtime.config import RuntimeConfig
from langagent.primitives.langchain_types import BaseChatModel
from langagent.primitives.exceptions import (
    ProviderUnsupportedError,
    AuthFailedError,
    EndpointUnreachableError,
    RequiredFieldMissingError,
)
from langagent.cross_cutting.logger import emit
from langagent.cross_cutting.stage_guard import cross_cutting_stage_guard_decorator

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
```

**No Dependencies On** (宪法第 II 条):
- `langagent.runtime` layers (except config schema)
- `langagent.protocol` layers
- `langagent.cli` layers

---

## Version History

- **1.0.0** (2026-09-17): Initial contract definition
