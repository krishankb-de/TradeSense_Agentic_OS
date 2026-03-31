"""
Azure OpenAI API Client
Implements integration with Azure OpenAI using GitHub Student credits
"""

import time
import logging
from typing import Optional, Dict, Any
from openai import AzureOpenAI
from openai.types.chat import ChatCompletion
from .base import LLMClient, LLMResponse, LLMError

logger = logging.getLogger(__name__)


class AzureOpenAIClient(LLMClient):
    """
    Azure OpenAI API client using GitHub Student credits.
    Supports GPT-4 and GPT-3.5-turbo with cost tracking and budget alerts.
    """
    
    # Approximate costs per 1K tokens (as of 2024)
    COSTS_PER_1K_TOKENS = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-32k": {"input": 0.06, "output": 0.12},
        "gpt-35-turbo": {"input": 0.0015, "output": 0.002},
        "gpt-35-turbo-16k": {"input": 0.003, "output": 0.004},
    }
    
    def __init__(
        self,
        api_key: str,
        endpoint: str,
        api_version: str = "2024-02-15-preview",
        deployment_name: str = "gpt-35-turbo",
        budget_limit: float = 100.0,  # $100 student credit
        alert_threshold: float = 0.8,  # Alert at 80% budget
    ):
        """
        Initialize Azure OpenAI client.
        
        Args:
            api_key: Azure OpenAI API key
            endpoint: Azure OpenAI endpoint URL
            api_version: API version to use
            deployment_name: Deployment name (gpt-4, gpt-35-turbo)
            budget_limit: Maximum budget in USD
            alert_threshold: Threshold for budget alerts (0.0-1.0)
        """
        super().__init__(model_name=deployment_name)
        
        if not api_key or not endpoint:
            raise ValueError("Azure OpenAI API key and endpoint are required")
        
        # Initialize client
        self.client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint
        )
        
        self.deployment_name = deployment_name
        self.api_version = api_version
        
        # Cost tracking
        self.total_cost = 0.0
        self.budget_limit = budget_limit
        self.alert_threshold = alert_threshold
        self.budget_alert_sent = False
        
        # Request tracking
        self.total_requests = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        
        logger.info(
            f"Initialized Azure OpenAI client with deployment: {deployment_name}, "
            f"budget: ${budget_limit:.2f}"
        )
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for a request.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        
        Returns:
            Cost in USD
        """
        # Get cost rates for the model
        model_key = self.deployment_name.lower()
        if model_key not in self.COSTS_PER_1K_TOKENS:
            # Default to gpt-35-turbo rates
            model_key = "gpt-35-turbo"
        
        rates = self.COSTS_PER_1K_TOKENS[model_key]
        
        input_cost = (input_tokens / 1000) * rates["input"]
        output_cost = (output_tokens / 1000) * rates["output"]
        
        return input_cost + output_cost
    
    def _check_budget(self, estimated_cost: float) -> bool:
        """
        Check if request would exceed budget.
        
        Args:
            estimated_cost: Estimated cost of the request
        
        Returns:
            True if within budget, False otherwise
        """
        projected_cost = self.total_cost + estimated_cost
        
        if projected_cost > self.budget_limit:
            logger.error(
                f"Budget limit exceeded: ${projected_cost:.4f} > ${self.budget_limit:.2f}"
            )
            return False
        
        # Check for budget alert
        if not self.budget_alert_sent:
            budget_used_pct = projected_cost / self.budget_limit
            if budget_used_pct >= self.alert_threshold:
                logger.warning(
                    f"Budget alert: {budget_used_pct*100:.1f}% of budget used "
                    f"(${projected_cost:.2f}/${self.budget_limit:.2f})"
                )
                self.budget_alert_sent = True
        
        return True
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text using Azure OpenAI API.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional generation parameters
        
        Returns:
            LLMResponse with generated text and metadata
        
        Raises:
            LLMError: If generation fails or budget exceeded
        """
        # Estimate cost (rough estimate based on prompt length)
        estimated_input_tokens = len(prompt.split()) * 1.3  # Rough estimate
        estimated_output_tokens = max_tokens if max_tokens else 500
        estimated_cost = self._calculate_cost(
            int(estimated_input_tokens),
            int(estimated_output_tokens)
        )
        
        # Check budget
        if not self._check_budget(estimated_cost):
            raise LLMError(
                "Budget limit exceeded",
                error_type="budget_exceeded",
                details={
                    "total_cost": self.total_cost,
                    "budget_limit": self.budget_limit,
                    "estimated_cost": estimated_cost,
                }
            )
        
        try:
            # Generate
            start_time = time.time()
            
            response: ChatCompletion = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            latency = time.time() - start_time
            
            # Extract response
            text = response.choices[0].message.content if response.choices else ""
            finish_reason = response.choices[0].finish_reason if response.choices else "unknown"
            
            # Get token usage
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0
            total_tokens = response.usage.total_tokens if response.usage else 0
            
            # Calculate actual cost
            actual_cost = self._calculate_cost(input_tokens, output_tokens)
            self.total_cost += actual_cost
            self.total_requests += 1
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            
            # Create response object
            llm_response = LLMResponse(
                text=text,
                model=self.deployment_name,
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                total_tokens=total_tokens,
                latency=latency,
                finish_reason=finish_reason,
                metadata={
                    "cost": actual_cost,
                    "total_cost": self.total_cost,
                    "budget_remaining": self.budget_limit - self.total_cost,
                    "budget_used_pct": (self.total_cost / self.budget_limit) * 100,
                    "response_id": response.id,
                    "model": response.model,
                }
            )
            
            logger.info(
                f"Generated {output_tokens} tokens in {latency:.2f}s, "
                f"cost: ${actual_cost:.4f}, total: ${self.total_cost:.2f}/${self.budget_limit:.2f}"
            )
            
            return llm_response
            
        except Exception as e:
            logger.error(f"Azure OpenAI API error: {str(e)}")
            raise LLMError(
                f"Azure OpenAI generation failed: {str(e)}",
                error_type="api_error",
                details={"original_error": str(e)}
            )
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """
        Get cost and usage summary.
        
        Returns:
            Dictionary with cost and usage information
        """
        return {
            "total_cost": self.total_cost,
            "budget_limit": self.budget_limit,
            "budget_remaining": self.budget_limit - self.total_cost,
            "budget_used_pct": (self.total_cost / self.budget_limit) * 100,
            "total_requests": self.total_requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "avg_cost_per_request": self.total_cost / self.total_requests if self.total_requests > 0 else 0,
        }
    
    def reset_budget_alert(self):
        """Reset the budget alert flag."""
        self.budget_alert_sent = False
        logger.info("Budget alert flag reset")
