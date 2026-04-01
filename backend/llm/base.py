"""Base classes for LLM clients."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ModelConfig:
    """Configuration for LLM model."""

    name: str
    context_length: int
    use_gpu: bool
    quantization: Optional[str] = None  # e.g., "int8", "int4", "float16"
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.9
    top_k: int = 40


@dataclass
class LLMResponse:
    """Response from LLM inference."""

    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    tokens_used: int = 0  # Deprecated, use total_tokens
    latency: float = 0.0
    latency_ms: float = 0.0  # Deprecated, use latency
    finish_reason: str = ""
    metadata: Dict[str, Any] = None
    usage: Optional[Dict[str, int]] = None  # Alternative way to pass token counts
    
    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}
        
        # Handle usage dict if provided
        if self.usage is not None:
            if self.prompt_tokens == 0 and "prompt_tokens" in self.usage:
                self.prompt_tokens = self.usage["prompt_tokens"]
            if self.completion_tokens == 0 and "completion_tokens" in self.usage:
                self.completion_tokens = self.usage["completion_tokens"]
            if self.total_tokens == 0 and "total_tokens" in self.usage:
                self.total_tokens = self.usage["total_tokens"]
        
        # Calculate total_tokens if not provided
        if self.total_tokens == 0 and (self.prompt_tokens > 0 or self.completion_tokens > 0):
            self.total_tokens = self.prompt_tokens + self.completion_tokens
        
        # Backward compatibility
        if self.tokens_used == 0 and self.total_tokens > 0:
            self.tokens_used = self.total_tokens
        if self.latency_ms == 0.0 and self.latency > 0.0:
            self.latency_ms = self.latency * 1000


class LLMError(Exception):
    """Exception raised for LLM-related errors."""
    
    def __init__(self, message: str, error_type: str = "unknown", details: Dict[str, Any] = None):
        """
        Initialize LLM error.
        
        Args:
            message: Error message
            error_type: Type of error (rate_limit, api_error, etc.)
            details: Additional error details
        """
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}


class LLMClient(ABC):
    """Abstract base class for cloud LLM clients."""
    
    def __init__(self, model_name: str):
        """
        Initialize LLM client.
        
        Args:
            model_name: Name of the model to use
        """
        self.model_name = model_name
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text completion.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model-specific parameters
        
        Returns:
            LLMResponse with generated text and metadata
        """
        pass


class BaseLLMClient(ABC):
    """Abstract base class for local LLM clients (Ollama/vLLM)."""

    def __init__(self, host: str, default_model: str, use_gpu: bool = True):
        """Initialize LLM client.

        Args:
            host: Host URL for the LLM service
            default_model: Default model to use
            use_gpu: Whether to use GPU acceleration
        """
        self.host = host
        self.default_model = default_model
        self.use_gpu = use_gpu

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate text completion.

        Args:
            prompt: Input prompt
            model: Model name (uses default if not specified)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model-specific parameters

        Returns:
            LLMResponse with generated text and metadata
        """
        pass

    @abstractmethod
    async def stream_generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> Any:
        """Generate text completion with streaming.

        Args:
            prompt: Input prompt
            model: Model name (uses default if not specified)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model-specific parameters

        Yields:
            Chunks of generated text
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """List available models.

        Returns:
            List of model names
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        pass

    @abstractmethod
    async def pull_model(self, model: str) -> bool:
        """Download and cache a model.

        Args:
            model: Model name to pull

        Returns:
            True if successful, False otherwise
        """
        pass
