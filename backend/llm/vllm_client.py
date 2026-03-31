"""vLLM client for high-performance local LLM inference."""

import time
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from .base import BaseLLMClient, LLMResponse


class VLLMClient(BaseLLMClient):
    """Client for vLLM high-performance local LLM inference.

    vLLM provides 19x faster inference than Ollama using PagedAttention.
    Optimized for larger deployments with high throughput requirements.
    """

    # Model mappings for TradeSense use cases
    MODEL_MAPPINGS = {
        "llama4-scout": "meta-llama/Llama-3.2-3B-Instruct",
        "llama4-maverick": "meta-llama/Llama-3.2-8B-Instruct",
        "deepseek-v3": "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
        "qwen3-omni": "Qwen/Qwen2.5-7B-Instruct",
        "gemma3": "google/gemma-2-9b-it",
        "command-r-plus": "CohereForAI/c4ai-command-r-plus-08-2024",
    }

    def __init__(self, host: str, default_model: str, use_gpu: bool = True):
        """Initialize vLLM client.

        Args:
            host: vLLM host URL (e.g., http://localhost:8000)
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
        """Generate text completion using vLLM.

        Args:
            prompt: Input prompt
            model: Model name (uses default if not specified)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional vLLM parameters

        Returns:
            LLMResponse with generated text and metadata
        """
        model_name = self._resolve_model(model or self.default_model)
        start_time = time.time()

        payload = {
            "model": model_name,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": kwargs.get("top_p", 0.9),
            "top_k": kwargs.get("top_k", 40),
            "stream": False,
        }

        try:
            response = await self.client.post(
                f"{self.host}/v1/completions",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            latency_ms = (time.time() - start_time) * 1000

            choice = data["choices"][0]
            usage = data.get("usage", {})

            return LLMResponse(
                text=choice["text"],
                model=data.get("model", model_name),
                tokens_used=usage.get("total_tokens", 0),
                latency_ms=latency_ms,
                finish_reason=choice.get("finish_reason", "stop"),
                metadata={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "id": data.get("id", ""),
                },
            )
        except httpx.HTTPError as e:
            raise RuntimeError(f"vLLM generation failed: {e}")

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
            **kwargs: Additional vLLM parameters

        Yields:
            Chunks of generated text
        """
        model_name = self._resolve_model(model or self.default_model)

        payload = {
            "model": model_name,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": kwargs.get("top_p", 0.9),
            "top_k": kwargs.get("top_k", 40),
            "stream": True,
        }

        try:
            async with self.client.stream(
                "POST",
                f"{self.host}/v1/completions",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        line = line[6:]  # Remove "data: " prefix
                        if line.strip() == "[DONE]":
                            break
                        try:
                            import json

                            data = json.loads(line)
                            if "choices" in data and len(data["choices"]) > 0:
                                text = data["choices"][0].get("text", "")
                                if text:
                                    yield text
                        except json.JSONDecodeError:
                            continue
        except httpx.HTTPError as e:
            raise RuntimeError(f"vLLM streaming failed: {e}")

    async def list_models(self) -> List[str]:
        """List available models in vLLM.

        Returns:
            List of model names
        """
        try:
            response = await self.client.get(f"{self.host}/v1/models")
            response.raise_for_status()
            data = response.json()
            return [model["id"] for model in data.get("data", [])]
        except httpx.HTTPError as e:
            raise RuntimeError(f"Failed to list vLLM models: {e}")

    async def health_check(self) -> bool:
        """Check if vLLM service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = await self.client.get(f"{self.host}/health")
            return response.status_code == 200
        except Exception:
            return False

    async def pull_model(self, model: str) -> bool:
        """vLLM loads models at startup, so this is a no-op.

        Args:
            model: Model name (ignored)

        Returns:
            True (models are pre-loaded)
        """
        # vLLM loads models at container startup via command args
        # No runtime model pulling supported
        return True

    def _resolve_model(self, model: str) -> str:
        """Resolve friendly model name to HuggingFace model name.

        Args:
            model: Friendly model name or HuggingFace model name

        Returns:
            HuggingFace model name
        """
        return self.MODEL_MAPPINGS.get(model, model)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
