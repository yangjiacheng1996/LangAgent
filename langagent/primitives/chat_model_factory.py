"""Chat model factory for primitives layer.

This module provides the factory function to instantiate LangChain BaseChatModel
instances based on RuntimeConfig.
"""

import os
import re
import requests
import time
from typing import TYPE_CHECKING

from langagent.primitives.exceptions import (
    ProviderUnsupportedError,
    AuthFailedError,
    EndpointUnreachableError,
    RequiredFieldMissingError,
)

# T086: Import cross_cutting_logger.emit per FR-045
from langagent.cross_cutting.cross_cutting_logger import emit

if TYPE_CHECKING:
    from langagent.primitives.langchain_types import BaseChatModel

# Supported providers
SUPPORTED_PROVIDERS = {
    "openai",
    "anthropic",
    "google",
    "deepseek",
    "zhipu",
    "openai-compatible",
}

# Environment variable mapping
ENV_VAR_MAPPING = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "zhipu": "ZHIPUAI_API_KEY",
    "openai-compatible": "OPENAI_API_KEY",  # Default to OPENAI_API_KEY for generic
}

# RFC1918 private IP pattern (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
PRIVATE_IP_PATTERN = re.compile(r'\b(10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|192\.168\.)')


def create(config) -> "BaseChatModel":
    """Create a chat model instance based on RuntimeConfig.
    
    Args:
        config: RuntimeConfig instance containing model configuration
        
    Returns:
        BaseChatModel instance ready for invocation
        
    Raises:
        ProviderUnsupportedError: model_provider not in supported list
        AuthFailedError: Required API key environment variable missing
        EndpointUnreachableError: Endpoint probe failed
        RequiredFieldMissingError: model_base_url is None or contains forbidden addresses
    """
    # T087: Emit start tag per FR-043
    start_time = time.perf_counter()
    provider = config.model_provider
    emit("la.runtime.model_adapt.start", {"provider": provider})
    
    try:
        # Step 1: Validate provider is supported
        if provider not in SUPPORTED_PROVIDERS:
            raise ProviderUnsupportedError(
                f"Provider '{provider}' is not supported. "
                f"Supported providers: {', '.join(sorted(SUPPORTED_PROVIDERS))}"
            )
        
        # Step 2: Check API key exists
        env_var_name = ENV_VAR_MAPPING[provider]
        api_key = os.environ.get(env_var_name)
        if not api_key:
            raise AuthFailedError(
                f"Required environment variable '{env_var_name}' is not set"
            )
        
        # Step 3: Validate model_base_url for providers that require it
        model_name = config.model_name
        model_base_url = config.model_base_url
        
        if provider in ("deepseek", "zhipu", "openai-compatible"):
            if not model_base_url:
                raise RequiredFieldMissingError(
                    f"model_base_url is required for provider '{provider}'"
                )
            
            # FR-004a: Reject localhost, 127.0.0.1, and RFC1918 private IPs for openai-compatible only
            if provider == "openai-compatible":
                if "localhost" in model_base_url.lower():
                    raise RequiredFieldMissingError(
                        f"Hardcoded localhost/private IPs forbidden in model_base_url per review.md M-1"
                    )
                
                if "127.0.0.1" in model_base_url:
                    raise RequiredFieldMissingError(
                        f"Hardcoded localhost/private IPs forbidden in model_base_url per review.md M-1"
                    )
                
                # Reject RFC1918 private IP addresses (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
                if PRIVATE_IP_PATTERN.search(model_base_url):
                    raise RequiredFieldMissingError(
                        f"Hardcoded localhost/private IPs forbidden in model_base_url per review.md M-1"
                    )
            
            # Step 4: Endpoint probe for providers with custom base_url
            _probe_endpoint(model_base_url)
        
        # Step 5: Instantiate the appropriate model class
        if provider == "openai":
            from langchain_openai import ChatOpenAI
            model = ChatOpenAI(
                model=model_name,
                api_key=api_key,
            )
        
        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            model = ChatAnthropic(
                model=model_name,
                api_key=api_key,
            )
        
        elif provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            model = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
            )
        
        elif provider in ("deepseek", "zhipu", "openai-compatible"):
            from langchain_openai import ChatOpenAI
            model = ChatOpenAI(
                model=model_name,
                api_key=api_key,
                base_url=model_base_url,
            )
        else:
            # Should never reach here due to provider validation above
            raise ProviderUnsupportedError(f"Provider '{provider}' is not supported")
        
        # T087: Emit ok tag with duration per FR-043
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        emit("la.runtime.model_adapt.ok", {"duration_ms": duration_ms})
        
        return model
        
    except Exception as e:
        # T087: Emit fail tag with error details per FR-043
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        emit("la.runtime.model_adapt.fail", {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "duration_ms": duration_ms
        })
        raise


def _probe_endpoint(base_url: str) -> None:
    """Probe endpoint to verify it's reachable.
    
    Args:
        base_url: Base URL to probe (e.g., "http://10.0.0.5:8000/v1")
        
    Raises:
        EndpointUnreachableError: Endpoint probe failed
    """
    # Construct probe URL
    probe_url = f"{base_url.rstrip('/')}/models"
    
    # T087: Emit endpoint_probe tag per FR-043
    emit("la.runtime.model_adapt.endpoint_probe", {"url": probe_url})
    
    try:
        # Send unauthenticated GET request with 5s timeout
        response = requests.get(probe_url, timeout=5)
        
        # Accept 200, 401, 403 as success (endpoint is reachable)
        if response.status_code in (200, 401, 403):
            return
        
        # 404 and 5xx are failures
        if response.status_code == 404 or response.status_code >= 500:
            raise EndpointUnreachableError(
                f"Endpoint probe failed: {probe_url} returned status {response.status_code}"
            )
        
        # Any other status code is also considered success (endpoint is reachable)
        return
        
    except requests.Timeout:
        raise EndpointUnreachableError(
            f"Endpoint probe failed: {probe_url} timed out after 5 seconds"
        )
    except requests.ConnectionError as e:
        raise EndpointUnreachableError(
            f"Endpoint probe failed: {probe_url} - {str(e)}"
        )
    except Exception as e:
        raise EndpointUnreachableError(
            f"Endpoint probe failed: {probe_url} - {str(e)}"
        )
