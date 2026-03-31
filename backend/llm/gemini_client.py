"""
Google Gemini API Client
Implements free tier support with rate limiting and quota management
"""

import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from .base import LLMClient, LLMResponse, LLMError

logger = logging.getLogger(__name__)


class GeminiClient(LLMClient):
    """
    Google Gemini API client with free tier support (1500 requests/day).
    Implements rate limiting, quota management, and request/response caching.
    """
    
    # Free tier limits
    FREE_TIER_DAILY_LIMIT = 1500
    FREE_TIER_RPM = 60  # Requests per minute
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash",
        enable_caching: bool = True,
        cache_ttl: int = 3600,  # 1 hour
    ):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google API key
            model_name: Model to use (gemini-2.5-flash, gemini-2.5-pro, gemini-flash-latest)
            enable_caching: Enable response caching
            cache_ttl: Cache time-to-live in seconds
        """
        super().__init__(model_name=model_name)
        
        if not api_key:
            raise ValueError("Google API key is required")
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        # Rate limiting
        self.requests_today = 0
        self.requests_this_minute = 0
        self.last_request_time = None
        self.minute_start_time = datetime.now()
        self.day_start_time = datetime.now()
        
        # Caching
        self.enable_caching = enable_caching
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, tuple[LLMResponse, datetime]] = {}
        
        logger.info(f"Initialized Gemini client with model: {model_name}")
    
    def _check_rate_limits(self) -> bool:
        """
        Check if we're within rate limits.
        
        Returns:
            True if request can proceed, False if rate limited
        """
        now = datetime.now()
        
        # Reset daily counter
        if (now - self.day_start_time) > timedelta(days=1):
            self.requests_today = 0
            self.day_start_time = now
            logger.info("Daily request counter reset")
        
        # Reset minute counter
        if (now - self.minute_start_time) > timedelta(minutes=1):
            self.requests_this_minute = 0
            self.minute_start_time = now
        
        # Check limits
        if self.requests_today >= self.FREE_TIER_DAILY_LIMIT:
            logger.warning(f"Daily limit reached: {self.requests_today}/{self.FREE_TIER_DAILY_LIMIT}")
            return False
        
        if self.requests_this_minute >= self.FREE_TIER_RPM:
            logger.warning(f"Per-minute limit reached: {self.requests_this_minute}/{self.FREE_TIER_RPM}")
            return False
        
        return True
    
    def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limits."""
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            min_interval = 60.0 / self.FREE_TIER_RPM
            
            if elapsed < min_interval:
                wait_time = min_interval - elapsed
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
                time.sleep(wait_time)
    
    def _get_cache_key(self, prompt: str, **kwargs) -> str:
        """Generate cache key from prompt and parameters."""
        params_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return f"{prompt}_{params_str}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[LLMResponse]:
        """Get response from cache if available and not expired."""
        if not self.enable_caching:
            return None
        
        if cache_key in self.cache:
            response, timestamp = self.cache[cache_key]
            age = (datetime.now() - timestamp).total_seconds()
            
            if age < self.cache_ttl:
                logger.debug(f"Cache hit for key: {cache_key[:50]}...")
                return response
            else:
                # Expired, remove from cache
                del self.cache[cache_key]
                logger.debug(f"Cache expired for key: {cache_key[:50]}...")
        
        return None
    
    def _add_to_cache(self, cache_key: str, response: LLMResponse):
        """Add response to cache."""
        if self.enable_caching:
            self.cache[cache_key] = (response, datetime.now())
            logger.debug(f"Cached response for key: {cache_key[:50]}...")
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text using Gemini API.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional generation parameters
        
        Returns:
            LLMResponse with generated text and metadata
        
        Raises:
            LLMError: If generation fails or rate limits exceeded
        """
        # Check cache first
        cache_key = self._get_cache_key(prompt, temperature=temperature, max_tokens=max_tokens, **kwargs)
        cached_response = self._get_from_cache(cache_key)
        if cached_response:
            return cached_response
        
        # Check rate limits
        if not self._check_rate_limits():
            raise LLMError(
                "Rate limit exceeded",
                error_type="rate_limit",
                details={
                    "requests_today": self.requests_today,
                    "daily_limit": self.FREE_TIER_DAILY_LIMIT,
                    "requests_this_minute": self.requests_this_minute,
                    "minute_limit": self.FREE_TIER_RPM,
                }
            )
        
        # Wait for rate limit if needed
        self._wait_for_rate_limit()
        
        try:
            # Configure generation
            generation_config = GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                **kwargs
            )
            
            # Generate
            start_time = time.time()
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            latency = time.time() - start_time
            
            # Update counters
            self.requests_today += 1
            self.requests_this_minute += 1
            self.last_request_time = time.time()
            
            # Extract response
            text = response.text if response.text else ""
            
            # Create response object
            llm_response = LLMResponse(
                text=text,
                model=self.model_name,
                prompt_tokens=response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                completion_tokens=response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0,
                total_tokens=response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0,
                latency=latency,
                metadata={
                    "finish_reason": response.candidates[0].finish_reason.name if response.candidates else None,
                    "safety_ratings": [
                        {
                            "category": rating.category.name,
                            "probability": rating.probability.name
                        }
                        for rating in response.candidates[0].safety_ratings
                    ] if response.candidates else [],
                    "requests_today": self.requests_today,
                    "requests_remaining": self.FREE_TIER_DAILY_LIMIT - self.requests_today,
                }
            )
            
            # Cache response
            self._add_to_cache(cache_key, llm_response)
            
            logger.info(
                f"Generated {llm_response.completion_tokens} tokens in {latency:.2f}s "
                f"({self.requests_today}/{self.FREE_TIER_DAILY_LIMIT} requests today)"
            )
            
            return llm_response
            
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            raise LLMError(
                f"Gemini generation failed: {str(e)}",
                error_type="api_error",
                details={"original_error": str(e)}
            )
    
    def get_quota_status(self) -> Dict[str, Any]:
        """
        Get current quota status.
        
        Returns:
            Dictionary with quota information
        """
        now = datetime.now()
        time_until_reset = timedelta(days=1) - (now - self.day_start_time)
        
        return {
            "requests_today": self.requests_today,
            "daily_limit": self.FREE_TIER_DAILY_LIMIT,
            "requests_remaining": self.FREE_TIER_DAILY_LIMIT - self.requests_today,
            "requests_this_minute": self.requests_this_minute,
            "minute_limit": self.FREE_TIER_RPM,
            "time_until_reset": str(time_until_reset),
            "cache_size": len(self.cache),
        }
    
    def clear_cache(self):
        """Clear the response cache."""
        self.cache.clear()
        logger.info("Response cache cleared")
    
    async def generate_with_image(
        self,
        prompt: str,
        image_data: str,
        image_format: str = "jpeg",
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate text using Gemini Vision API with image input.
        
        Args:
            prompt: Text prompt
            image_data: Base64-encoded image data
            image_format: Image format (jpeg, png, etc.)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional generation parameters
        
        Returns:
            Generated text response
        
        Raises:
            LLMError: If generation fails
        """
        import base64
        from PIL import Image
        import io
        
        # Check rate limits
        if not self._check_rate_limits():
            raise LLMError(
                "Rate limit exceeded",
                error_type="rate_limit",
                details={
                    "requests_today": self.requests_today,
                    "daily_limit": self.FREE_TIER_DAILY_LIMIT,
                }
            )
        
        # Wait for rate limit if needed
        self._wait_for_rate_limit()
        
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Configure generation
            generation_config = GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                **kwargs
            )
            
            # Generate with image
            start_time = time.time()
            response = self.model.generate_content(
                [prompt, image],
                generation_config=generation_config
            )
            latency = time.time() - start_time
            
            # Update counters
            self.requests_today += 1
            self.requests_this_minute += 1
            self.last_request_time = time.time()
            
            # Extract text
            text = response.text if response.text else ""
            
            logger.info(
                f"Generated vision response in {latency:.2f}s "
                f"({self.requests_today}/{self.FREE_TIER_DAILY_LIMIT} requests today)"
            )
            
            return text
            
        except Exception as e:
            logger.error(f"Gemini Vision API error: {str(e)}")
            raise LLMError(
                f"Gemini vision generation failed: {str(e)}",
                error_type="api_error",
                details={"original_error": str(e)}
            )
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate text embedding using Gemini.
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector
        
        Raises:
            LLMError: If embedding generation fails
        """
        # Check rate limits
        if not self._check_rate_limits():
            raise LLMError(
                "Rate limit exceeded",
                error_type="rate_limit",
                details={
                    "requests_today": self.requests_today,
                    "daily_limit": self.FREE_TIER_DAILY_LIMIT,
                }
            )
        
        try:
            # Use Gemini embedding model
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            
            # Update counters
            self.requests_today += 1
            self.requests_this_minute += 1
            self.last_request_time = time.time()
            
            return result['embedding']
            
        except Exception as e:
            logger.error(f"Gemini embedding error: {str(e)}")
            raise LLMError(
                f"Gemini embedding failed: {str(e)}",
                error_type="api_error",
                details={"original_error": str(e)}
            )
    
    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate chat response using Gemini.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional generation parameters
        
        Returns:
            Generated response text
        
        Raises:
            LLMError: If generation fails
        """
        # Check rate limits
        if not self._check_rate_limits():
            raise LLMError(
                "Rate limit exceeded",
                error_type="rate_limit",
                details={
                    "requests_today": self.requests_today,
                    "daily_limit": self.FREE_TIER_DAILY_LIMIT,
                }
            )
        
        # Wait for rate limit if needed
        self._wait_for_rate_limit()
        
        try:
            # Start chat session
            chat = self.model.start_chat(history=[])
            
            # Configure generation
            generation_config = GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                **kwargs
            )
            
            # Build conversation
            response_text = ""
            for msg in messages:
                if msg['role'] == 'user':
                    response = chat.send_message(
                        msg['content'],
                        generation_config=generation_config
                    )
                    response_text = response.text
            
            # Update counters
            self.requests_today += 1
            self.requests_this_minute += 1
            self.last_request_time = time.time()
            
            return response_text
            
        except Exception as e:
            logger.error(f"Gemini chat error: {str(e)}")
            raise LLMError(
                f"Gemini chat failed: {str(e)}",
                error_type="api_error",
                details={"original_error": str(e)}
            )
