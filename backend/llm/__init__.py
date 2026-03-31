"""Local LLM inference module for TradeSense.

This module provides unified interfaces for local LLM inference using Ollama and vLLM,
with automatic GPU detection and CPU fallback with quantization.

Also provides cloud LLM clients for Gemini and Azure OpenAI with intelligent routing.
"""

from .base import (
    BaseLLMClient,
    LLMClient,
    LLMResponse,
    LLMError,
    ModelConfig,
)
from .ollama_client import OllamaClient
from .vllm_client import VLLMClient
from .gemini_client import GeminiClient
from .azure_openai_client import AzureOpenAIClient
from .unified_client import UnifiedLLMClient, LLMProvider

__all__ = [
    "BaseLLMClient",
    "LLMClient",
    "LLMResponse",
    "LLMError",
    "ModelConfig",
    "OllamaClient",
    "VLLMClient",
    "GeminiClient",
    "AzureOpenAIClient",
    "UnifiedLLMClient",
    "LLMProvider",
]
