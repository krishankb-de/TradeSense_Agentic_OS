"""Ollama client for local LLM inference."""

import time
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from .base import BaseLLMClient, LLMResponse


class OllamaClient(BaseLLMClient):
    """Client for Ollama local LLM inference.

    Ollama provides Docker-like simplicity with auto-quantization for small shops.
    Supports Llama 4, DeepSeek-V3, Qwen 3, Gemma 3, Command R+ models.
    """

    # Model mappings for TradeSense use cases
    MODEL_MAPPINGS = {
        "llama4-scout": "llama3.2:3b",  # Fast general reasoning
        "llama4-maverick": "llama3.2:8b",  # Balanced reasoning
        "deepseek-v3": "deepseek-r1:8b",  # Complex reasoning (MoE)
        "qwen3-omni": "qwen2.5:7b",  # Multimodal
        "gemma3": "gemma2:9b",  # Vision understanding
        "command-r-plus": "command-r-plus:35b",  # RAG-optimized
    }

    def __init__(self, host: str, default_model: str, use_gpu: bool = True):
        """Initialize Ollama client.

        Args:
            host: Ollama host URL (e.g., http://localhost:11434)
            default_model: Default model to use
            use_gpu: Whether to use GPU acceleration
        """
        super().__init__(host, default_model, use_gpu)
        self.client = httpx.AsyncClient(timeout=120.0)

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate text completion using Ollama.

        Args:
            prompt: Input prompt
            model: Model name (uses default if not specified)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Ollama parameters

        Returns:
            LLMResponse with generated text and metadata
        """
        model_name = self._resolve_model(model or self.default_model)
        start_time = time.time()

        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": kwargs.get("top_p", 0.9),
                "top_k": kwargs.get("top_k", 40),
            },
        }

        # Add GPU/CPU configuration
        if not self.use_gpu:
            payload["options"]["num_gpu"] = 0
            payload["options"]["num_thread"] = kwargs.get("num_threads", 8)

        try:
            response = await self.client.post(
                f"{self.host}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            latency_ms = (time.time() - start_time) * 1000

            return LLMResponse(
                text=data.get("response", ""),
                model=model_name,
                tokens_used=data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
                latency_ms=latency_ms,
                finish_reason=data.get("done_reason", "stop"),
                metadata={
                    "eval_duration": data.get("eval_duration", 0),
                    "load_duration": data.get("load_duration", 0),
                    "prompt_eval_count": data.get("prompt_eval_count", 0),
                    "eval_count": data.get("eval_count", 0),
                },
            )
        except httpx.HTTPError as e:
            raise RuntimeError(f"Ollama generation failed: {e}")

    async def stream_generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Generate text completion with streaming.

        Args:
            prompt: Input prompt
            model: Model name (uses default if not specified)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Ollama parameters

        Yields:
            Chunks of generated text
        """
        model_name = self._resolve_model(model or self.default_model)

        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": kwargs.get("top_p", 0.9),
                "top_k": kwargs.get("top_k", 40),
            },
        }

        if not self.use_gpu:
            payload["options"]["num_gpu"] = 0
            payload["options"]["num_thread"] = kwargs.get("num_threads", 8)

        try:
            async with self.client.stream(
                "POST",
                f"{self.host}/api/generate",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        import json

                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
        except httpx.HTTPError as e:
            raise RuntimeError(f"Ollama streaming failed: {e}")

    async def list_models(self) -> List[str]:
        """List available models in Ollama.

        Returns:
            List of model names
        """
        try:
            response = await self.client.get(f"{self.host}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except httpx.HTTPError as e:
            raise RuntimeError(f"Failed to list Ollama models: {e}")

    async def health_check(self) -> bool:
        """Check if Ollama service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = await self.client.get(f"{self.host}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def pull_model(self, model: str) -> bool:
        """Download and cache a model in Ollama.

        Args:
            model: Model name to pull

        Returns:
            True if successful, False otherwise
        """
        model_name = self._resolve_model(model)

        try:
            response = await self.client.post(
                f"{self.host}/api/pull",
                json={"name": model_name, "stream": False},
                timeout=600.0,  # 10 minutes for large models
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False

    def _resolve_model(self, model: str) -> str:
        """Resolve friendly model name to Ollama model name.

        Args:
            model: Friendly model name or Ollama model name

        Returns:
            Ollama model name
        """
        return self.MODEL_MAPPINGS.get(model, model)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
