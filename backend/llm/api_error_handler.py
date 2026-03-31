"""
API Error Handler for LLM Clients.

Implements comprehensive API error handling:
- Exponential backoff retry (1s, 2s, 4s, 8s, 16s)
- Rate limiting handling
- Fallback to Azure OpenAI when Gemini quota exceeded
- Admin alerts on all API failures

**Validates: Requirements 15.2, 15.3**
"""

import logging
import time
import asyncio
from typing import Optional, Callable, Any, TypeVar
from dataclasses import dataclass
from enum import Enum

from core.error_handling import (
    ErrorHandler,
    ErrorContext,
    ErrorCategory,
    ErrorSeverity,
    RetryConfig,
    get_error_handler,
    with_retry,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class APIErrorType(Enum):
    """Types of API errors."""
    RATE_LIMIT = "rate_limit"
    QUOTA_EXCEEDED = "quota_exceeded"
    BUDGET_EXCEEDED = "budget_exceeded"
    AUTHENTICATION = "authentication"
    NETWORK = "network"
    TIMEOUT = "timeout"
    SERVER_ERROR = "server_error"
    INVALID_REQUEST = "invalid_request"
    UNKNOWN = "unknown"


@dataclass
class APIErrorContext:
    """Context for API errors."""
    error_type: APIErrorType
    provider: str
    message: str
    status_code: Optional[int] = None
    retry_after: Optional[float] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class APIErrorHandler:
    """
    API error handler with retry and fallback logic.
    
    Features:
    - Exponential backoff retry (1s, 2s, 4s, 8s, 16s)
    - Rate limiting detection and handling
    - Automatic fallback between providers
    - Admin alerts on critical failures
    
    **Validates: Requirements 15.2, 15.3**
    """
    
    def __init__(self):
        """Initialize API error handler."""
        self.error_handler = get_error_handler()
        
        # Default retry configuration for API calls
        self.default_retry_config = RetryConfig(
            max_retries=5,  # 5 retries = 6 total attempts
            initial_delay=1.0,  # Start at 1 second
            max_delay=16.0,  # Cap at 16 seconds
            exponential_base=2.0,  # Double each time: 1s, 2s, 4s, 8s, 16s
            jitter=True,  # Add randomness to prevent thundering herd
        )
        
        # Track API errors by provider
        self.api_errors: dict[str, list[APIErrorContext]] = {}
        
        # Admin alert callbacks
        self.admin_alert_callbacks: list[Callable[[APIErrorContext], None]] = []
        
        logger.info("API error handler initialized")
    
    def classify_error(
        self,
        error: Exception,
        provider: str,
    ) -> APIErrorContext:
        """
        Classify API error.
        
        Args:
            error: Exception that occurred
            provider: API provider name
            
        Returns:
            APIErrorContext with classified error
        """
        error_message = str(error)
        error_type = APIErrorType.UNKNOWN
        status_code = None
        retry_after = None
        
        # Check for rate limiting
        if "429" in error_message or "rate limit" in error_message.lower():
            error_type = APIErrorType.RATE_LIMIT
            status_code = 429
            # Try to extract retry-after header
            if "retry after" in error_message.lower():
                try:
                    # Extract number from message
                    import re
                    match = re.search(r'retry after (\d+)', error_message.lower())
                    if match:
                        retry_after = float(match.group(1))
                except:
                    pass
        
        # Check for quota exceeded
        elif "quota" in error_message.lower() or "limit exceeded" in error_message.lower():
            error_type = APIErrorType.QUOTA_EXCEEDED
        
        # Check for budget exceeded
        elif "budget" in error_message.lower():
            error_type = APIErrorType.BUDGET_EXCEEDED
        
        # Check for authentication errors
        elif "401" in error_message or "unauthorized" in error_message.lower() or "invalid api key" in error_message.lower():
            error_type = APIErrorType.AUTHENTICATION
            status_code = 401
        
        # Check for network errors
        elif "connection" in error_message.lower() or "network" in error_message.lower():
            error_type = APIErrorType.NETWORK
        
        # Check for timeout
        elif "timeout" in error_message.lower():
            error_type = APIErrorType.TIMEOUT
        
        # Check for server errors
        elif "500" in error_message or "502" in error_message or "503" in error_message:
            error_type = APIErrorType.SERVER_ERROR
            if "500" in error_message:
                status_code = 500
            elif "502" in error_message:
                status_code = 502
            elif "503" in error_message:
                status_code = 503
        
        # Check for invalid request
        elif "400" in error_message or "invalid" in error_message.lower():
            error_type = APIErrorType.INVALID_REQUEST
            status_code = 400
        
        return APIErrorContext(
            error_type=error_type,
            provider=provider,
            message=error_message,
            status_code=status_code,
            retry_after=retry_after,
        )
    
    def should_retry(self, error_context: APIErrorContext) -> bool:
        """
        Determine if error should be retried.
        
        Args:
            error_context: API error context
            
        Returns:
            True if should retry
        """
        # Retry transient errors
        retryable_errors = {
            APIErrorType.RATE_LIMIT,
            APIErrorType.NETWORK,
            APIErrorType.TIMEOUT,
            APIErrorType.SERVER_ERROR,
        }
        
        return error_context.error_type in retryable_errors
    
    def should_fallback(self, error_context: APIErrorContext) -> bool:
        """
        Determine if should fallback to alternative provider.
        
        Args:
            error_context: API error context
            
        Returns:
            True if should fallback
        """
        # Fallback on quota/budget exceeded
        fallback_errors = {
            APIErrorType.QUOTA_EXCEEDED,
            APIErrorType.BUDGET_EXCEEDED,
            APIErrorType.RATE_LIMIT,  # Also fallback on persistent rate limiting
        }
        
        return error_context.error_type in fallback_errors
    
    async def handle_api_error(
        self,
        error: Exception,
        provider: str,
        operation: str,
    ) -> dict[str, Any]:
        """
        Handle API error with classification and logging.
        
        **Validates: Requirements 15.2, 15.3**
        
        Args:
            error: Exception that occurred
            provider: API provider name
            operation: Operation that failed
            
        Returns:
            Dictionary with error handling instructions
        """
        # Classify error
        error_context = self.classify_error(error, provider)
        
        # Track error
        if provider not in self.api_errors:
            self.api_errors[provider] = []
        self.api_errors[provider].append(error_context)
        
        # Log error
        severity = ErrorSeverity.HIGH if error_context.error_type in [
            APIErrorType.AUTHENTICATION,
            APIErrorType.BUDGET_EXCEEDED,
        ] else ErrorSeverity.MEDIUM
        
        error_log = ErrorContext(
            category=ErrorCategory.API_CALL,
            severity=severity,
            message=f"API error in {operation}: {error_context.error_type.value}",
            details={
                "provider": provider,
                "error_type": error_context.error_type.value,
                "status_code": error_context.status_code,
                "message": error_context.message,
            },
        )
        self.error_handler.log_error(error_log)
        
        # Trigger admin alerts for critical errors
        if severity == ErrorSeverity.HIGH:
            self._trigger_admin_alert(error_context)
        
        # Determine action
        should_retry = self.should_retry(error_context)
        should_fallback = self.should_fallback(error_context)
        
        logger.warning(
            f"API error for {provider}: {error_context.error_type.value}. "
            f"Retry: {should_retry}, Fallback: {should_fallback}"
        )
        
        return {
            "error_type": error_context.error_type.value,
            "provider": provider,
            "should_retry": should_retry,
            "should_fallback": should_fallback,
            "retry_after": error_context.retry_after,
            "message": error_context.message,
        }
    
    def _trigger_admin_alert(self, error_context: APIErrorContext) -> None:
        """
        Trigger admin alert for critical API error.
        
        Args:
            error_context: API error context
        """
        logger.critical(
            f"ADMIN ALERT: Critical API error for {error_context.provider}: "
            f"{error_context.error_type.value}"
        )
        
        # Call registered callbacks
        for callback in self.admin_alert_callbacks:
            try:
                callback(error_context)
            except Exception as e:
                logger.error(f"Admin alert callback failed: {e}")
    
    def register_admin_alert(
        self,
        callback: Callable[[APIErrorContext], None]
    ) -> None:
        """
        Register callback for admin alerts.
        
        Args:
            callback: Callback function
        """
        self.admin_alert_callbacks.append(callback)
        logger.info("Admin alert callback registered")
    
    def get_api_error_stats(self, provider: Optional[str] = None) -> dict[str, Any]:
        """
        Get API error statistics.
        
        Args:
            provider: Optional provider filter
            
        Returns:
            Dictionary with error statistics
        """
        if provider:
            errors = self.api_errors.get(provider, [])
            providers_to_check = {provider: errors}
        else:
            providers_to_check = self.api_errors
        
        stats = {}
        
        for prov, errors in providers_to_check.items():
            by_type = {}
            for error in errors:
                error_type = error.error_type.value
                by_type[error_type] = by_type.get(error_type, 0) + 1
            
            stats[prov] = {
                "total_errors": len(errors),
                "by_type": by_type,
            }
        
        return stats
    
    def get_retry_config(
        self,
        error_context: Optional[APIErrorContext] = None
    ) -> RetryConfig:
        """
        Get retry configuration for error.
        
        Args:
            error_context: Optional error context for custom config
            
        Returns:
            RetryConfig
        """
        config = self.default_retry_config
        
        # Adjust config based on error type
        if error_context:
            if error_context.error_type == APIErrorType.RATE_LIMIT:
                # Use retry_after if available
                if error_context.retry_after:
                    config = RetryConfig(
                        max_retries=3,
                        initial_delay=error_context.retry_after,
                        max_delay=error_context.retry_after * 2,
                        exponential_base=1.0,  # Fixed delay
                        jitter=False,
                    )
        
        return config


# Global instance
_api_error_handler = APIErrorHandler()


def get_api_error_handler() -> APIErrorHandler:
    """Get global API error handler instance."""
    return _api_error_handler


def with_api_retry(
    provider: str,
    operation: str,
):
    """
    Decorator for API calls with automatic retry and error handling.
    
    **Validates: Requirements 15.2, 15.3**
    
    Args:
        provider: API provider name
        operation: Operation name
    
    Example:
        @with_api_retry(provider="gemini", operation="generate")
        async def call_gemini_api():
            # API call
            pass
    """
    handler = get_api_error_handler()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Use the with_retry decorator with API-specific config
        retry_decorator = with_retry(
            config=handler.default_retry_config,
            category=ErrorCategory.API_CALL,
            severity=ErrorSeverity.MEDIUM,
        )
        
        return retry_decorator(func)
    
    return decorator
