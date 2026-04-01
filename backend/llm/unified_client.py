"""
Unified LLM Client
Intelligent routing between Gemini (free) → Azure OpenAI (student credits)
with request/response logging and cost tracking
"""

import logging
import time
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from .base import LLMClient, LLMResponse, LLMError
from .gemini_client import GeminiClient
from .azure_openai_client import AzureOpenAIClient
from .cost_optimizer import get_cost_optimizer, ServiceType

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Available LLM providers."""
    GEMINI = "gemini"
    AZURE_OPENAI = "azure_openai"
    GITHUB_COPILOT = "github_copilot"  # Future implementation


@dataclass
class RequestLog:
    """Log entry for an LLM request."""
    timestamp: datetime
    provider: LLMProvider
    prompt: str
    response: LLMResponse
    success: bool
    error: Optional[str] = None
    fallback_used: bool = False


class UnifiedLLMClient:
    """
    Unified LLM client with intelligent routing and fallback.
    
    Routing strategy:
    1. Try Gemini (free tier) first
    2. If Gemini quota exceeded, fallback to Azure OpenAI (student credits)
    3. If Azure budget exceeded, fallback to GitHub Copilot (future)
    
    Features:
    - Automatic fallback on quota/budget limits
    - Request/response logging
    - Cost tracking across providers
    - Quota management
    """
    
    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        azure_api_key: Optional[str] = None,
        azure_endpoint: Optional[str] = None,
        azure_deployment: str = "gpt-35-turbo",
        enable_logging: bool = True,
        max_log_entries: int = 1000,
        enable_cost_optimization: bool = True,
    ):
        """
        Initialize unified LLM client.
        
        Args:
            gemini_api_key: Google Gemini API key
            azure_api_key: Azure OpenAI API key
            azure_endpoint: Azure OpenAI endpoint
            azure_deployment: Azure OpenAI deployment name
            enable_logging: Enable request/response logging
            max_log_entries: Maximum number of log entries to keep
            enable_cost_optimization: Enable cost optimization features
        """
        self.enable_logging = enable_logging
        self.max_log_entries = max_log_entries
        self.request_logs: List[RequestLog] = []
        self.enable_cost_optimization = enable_cost_optimization
        
        # Get cost optimizer
        self.cost_optimizer = get_cost_optimizer() if enable_cost_optimization else None
        
        # Initialize clients
        self.gemini_client: Optional[GeminiClient] = None
        self.azure_client: Optional[AzureOpenAIClient] = None
        
        if gemini_api_key:
            try:
                self.gemini_client = GeminiClient(
                    api_key=gemini_api_key,
                    model_name="gemini-2.5-flash",
                    enable_caching=True
                )
                logger.info("Gemini client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")
        
        if azure_api_key and azure_endpoint:
            try:
                self.azure_client = AzureOpenAIClient(
                    api_key=azure_api_key,
                    endpoint=azure_endpoint,
                    deployment_name=azure_deployment,
                    budget_limit=100.0  # $100 student credit
                )
                logger.info("Azure OpenAI client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Azure OpenAI client: {e}")
        
        if not self.gemini_client and not self.azure_client:
            raise ValueError("At least one LLM provider must be configured")
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.fallback_count = 0
        
        logger.info("Unified LLM client initialized")
    
    def _log_request(
        self,
        provider: LLMProvider,
        prompt: str,
        response: Optional[LLMResponse],
        success: bool,
        error: Optional[str] = None,
        fallback_used: bool = False
    ):
        """Log a request."""
        if not self.enable_logging:
            return
        
        log_entry = RequestLog(
            timestamp=datetime.now(),
            provider=provider,
            prompt=prompt[:200],  # Truncate for storage
            response=response,
            success=success,
            error=error,
            fallback_used=fallback_used
        )
        
        self.request_logs.append(log_entry)
        
        # Trim logs if needed
        if len(self.request_logs) > self.max_log_entries:
            self.request_logs = self.request_logs[-self.max_log_entries:]
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        prefer_provider: Optional[LLMProvider] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text with intelligent routing and fallback.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            prefer_provider: Preferred provider (overrides default routing)
            **kwargs: Additional generation parameters
        
        Returns:
            LLMResponse with generated text and metadata
        
        Raises:
            LLMError: If all providers fail
        """
        self.total_requests += 1
        start_time = time.time()
        
        # Check cache first if cost optimization enabled
        if self.cost_optimizer:
            service = ServiceType.GEMINI if prefer_provider != LLMProvider.AZURE_OPENAI else ServiceType.AZURE_OPENAI
            cached_response = self.cost_optimizer.get_cached_response(
                service=service,
                operation="generate",
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            if cached_response:
                logger.info(f"Returning cached response for {service.value}")
                return cached_response
        
        # Determine provider order
        if prefer_provider == LLMProvider.AZURE_OPENAI:
            providers = [
                (LLMProvider.AZURE_OPENAI, self.azure_client, ServiceType.AZURE_OPENAI),
                (LLMProvider.GEMINI, self.gemini_client, ServiceType.GEMINI),
            ]
        else:
            # Default: Try Gemini first (free), then Azure (student credits)
            providers = [
                (LLMProvider.GEMINI, self.gemini_client, ServiceType.GEMINI),
                (LLMProvider.AZURE_OPENAI, self.azure_client, ServiceType.AZURE_OPENAI),
            ]
        
        # Filter out None clients
        providers = [(p, c, s) for p, c, s in providers if c is not None]
        
        last_error = None
        fallback_used = False
        
        for i, (provider, client, service_type) in enumerate(providers):
            # Check quota if cost optimization enabled
            if self.cost_optimizer:
                within_quota, reason = self.cost_optimizer.check_quota(service_type)
                if not within_quota:
                    logger.warning(f"{provider.value} quota exceeded: {reason}")
                    if i < len(providers) - 1:
                        fallback_used = True
                        self.fallback_count += 1
                        logger.info(f"Falling back to next provider...")
                        continue
                    else:
                        last_error = LLMError(
                            f"Quota exceeded: {reason}",
                            error_type="quota_exceeded"
                        )
                        break
            
            try:
                logger.debug(f"Attempting generation with {provider.value}")
                
                response = client.generate(
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                # Increment quota if cost optimization enabled
                if self.cost_optimizer:
                    self.cost_optimizer.increment_quota(service_type)
                    
                    # Cache response
                    self.cost_optimizer.cache_response(
                        service=service_type,
                        operation="generate",
                        response=response,
                        prompt=prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs
                    )
                
                # Add routing metadata
                response.metadata["provider"] = provider.value
                response.metadata["fallback_used"] = fallback_used
                response.metadata["total_latency"] = time.time() - start_time
                
                # Log success
                self._log_request(
                    provider=provider,
                    prompt=prompt,
                    response=response,
                    success=True,
                    fallback_used=fallback_used
                )
                
                self.successful_requests += 1
                
                logger.info(
                    f"Successfully generated with {provider.value} "
                    f"(fallback: {fallback_used})"
                )
                
                return response
                
            except LLMError as e:
                last_error = e
                logger.warning(
                    f"{provider.value} failed: {e.error_type} - {str(e)}"
                )
                
                # Check if we should try fallback
                if e.error_type in ["rate_limit", "budget_exceeded", "quota_exceeded"]:
                    if i < len(providers) - 1:
                        fallback_used = True
                        self.fallback_count += 1
                        logger.info(f"Falling back to next provider...")
                        continue
                
                # Non-recoverable error or last provider
                break
        
        # All providers failed
        self.failed_requests += 1
        
        error_msg = f"All LLM providers failed. Last error: {str(last_error)}"
        logger.error(error_msg)
        
        self._log_request(
            provider=providers[-1][0] if providers else LLMProvider.GEMINI,
            prompt=prompt,
            response=None,
            success=False,
            error=error_msg,
            fallback_used=fallback_used
        )
        
        raise LLMError(
            error_msg,
            error_type="all_providers_failed",
            details={
                "last_error": str(last_error),
                "providers_tried": [p.value for p, _, _ in providers]
            }
        )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get status of all providers and overall statistics.
        
        Returns:
            Dictionary with status information
        """
        status = {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "fallback_count": self.fallback_count,
            "success_rate": (
                self.successful_requests / self.total_requests * 100
                if self.total_requests > 0 else 0
            ),
            "providers": {}
        }
        
        if self.gemini_client:
            status["providers"]["gemini"] = {
                "available": True,
                **self.gemini_client.get_quota_status()
            }
        
        if self.azure_client:
            status["providers"]["azure_openai"] = {
                "available": True,
                **self.azure_client.get_cost_summary()
            }
        
        return status
    
    def get_request_logs(
        self,
        limit: Optional[int] = None,
        provider: Optional[LLMProvider] = None,
        success_only: bool = False
    ) -> List[RequestLog]:
        """
        Get request logs with optional filtering.
        
        Args:
            limit: Maximum number of logs to return
            provider: Filter by provider
            success_only: Only return successful requests
        
        Returns:
            List of request logs
        """
        logs = self.request_logs
        
        if provider:
            logs = [log for log in logs if log.provider == provider]
        
        if success_only:
            logs = [log for log in logs if log.success]
        
        if limit:
            logs = logs[-limit:]
        
        return logs
    
    def clear_logs(self):
        """Clear all request logs."""
        self.request_logs.clear()
        logger.info("Request logs cleared")
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """
        Get cost summary across all providers.
        
        Returns:
            Dictionary with cost information
        """
        total_cost = 0.0
        
        summary = {
            "total_cost": 0.0,
            "providers": {}
        }
        
        if self.gemini_client:
            # Gemini is free
            summary["providers"]["gemini"] = {
                "cost": 0.0,
                "quota_status": self.gemini_client.get_quota_status()
            }
        
        if self.azure_client:
            azure_summary = self.azure_client.get_cost_summary()
            total_cost += azure_summary["total_cost"]
            summary["providers"]["azure_openai"] = azure_summary
        
        summary["total_cost"] = total_cost
        
        return summary



def create_unified_llm_client() -> UnifiedLLMClient:
    """
    Factory function to create unified LLM client.
    
    Returns:
        Configured UnifiedLLMClient instance
    """
    return UnifiedLLMClient()
