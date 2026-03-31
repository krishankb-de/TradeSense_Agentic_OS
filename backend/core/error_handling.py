"""
Error Handling and Recovery Module for TradeSense.

Provides comprehensive error handling and recovery mechanisms:
- Exponential backoff retry logic
- Fallback mechanisms
- Error logging and alerting
- Graceful degradation strategies

**Validates: Requirements 15.1, 15.2, 15.3, 15.5, 15.6, 15.8**
"""

import logging
import time
import asyncio
from typing import Optional, Callable, Any, TypeVar, Dict, List
from dataclasses import dataclass
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    VOICE_PIPELINE = "voice_pipeline"
    API_CALL = "api_call"
    DATABASE = "database"
    PARTS_NOT_FOUND = "parts_not_found"
    SCHEDULING_CONFLICT = "scheduling_conflict"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for an error."""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: float = 0.0
    retry_count: int = 0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 16.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt with exponential backoff.
        
        **Validates: Requirement 15.2**
        
        Args:
            attempt: Retry attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: initial_delay * (base ^ attempt)
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay


class ErrorHandler:
    """
    Centralized error handler with retry logic and fallback mechanisms.
    
    **Validates: Requirements 15.1, 15.2, 15.3, 15.5, 15.6, 15.8**
    """
    
    def __init__(self):
        """Initialize error handler."""
        self.error_log: List[ErrorContext] = []
        self.max_log_size = 1000
        self.alert_callbacks: Dict[ErrorSeverity, List[Callable]] = {
            severity: [] for severity in ErrorSeverity
        }
    
    def log_error(self, error_context: ErrorContext) -> None:
        """
        Log error with context.
        
        Args:
            error_context: Error context information
        """
        self.error_log.append(error_context)
        
        # Trim log if needed
        if len(self.error_log) > self.max_log_size:
            self.error_log = self.error_log[-self.max_log_size:]
        
        # Log to standard logger
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }[error_context.severity]
        
        logger.log(
            log_level,
            f"[{error_context.category.value}] {error_context.message}",
            extra={"details": error_context.details}
        )
        
        # Trigger alerts for high severity errors
        if error_context.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self._trigger_alerts(error_context)
    
    def register_alert_callback(
        self,
        severity: ErrorSeverity,
        callback: Callable[[ErrorContext], None]
    ) -> None:
        """
        Register callback for error alerts.
        
        Args:
            severity: Minimum severity to trigger callback
            callback: Callback function
        """
        self.alert_callbacks[severity].append(callback)
    
    def _trigger_alerts(self, error_context: ErrorContext) -> None:
        """
        Trigger alert callbacks for error.
        
        Args:
            error_context: Error context
        """
        for severity in ErrorSeverity:
            if severity.value >= error_context.severity.value:
                for callback in self.alert_callbacks[severity]:
                    try:
                        callback(error_context)
                    except Exception as e:
                        logger.error(f"Alert callback failed: {e}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """
        Get error statistics.
        
        Returns:
            Dictionary with error statistics
        """
        if not self.error_log:
            return {
                "total_errors": 0,
                "by_category": {},
                "by_severity": {},
            }
        
        by_category = {}
        by_severity = {}
        
        for error in self.error_log:
            # Count by category
            category_key = error.category.value
            by_category[category_key] = by_category.get(category_key, 0) + 1
            
            # Count by severity
            severity_key = error.severity.value
            by_severity[severity_key] = by_severity.get(severity_key, 0) + 1
        
        return {
            "total_errors": len(self.error_log),
            "by_category": by_category,
            "by_severity": by_severity,
        }


# Global error handler instance
_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    return _error_handler


def with_retry(
    config: Optional[RetryConfig] = None,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
):
    """
    Decorator for automatic retry with exponential backoff.
    
    **Validates: Requirement 15.2**
    
    Args:
        config: Retry configuration
        category: Error category
        severity: Error severity
    
    Example:
        @with_retry(RetryConfig(max_retries=3))
        async def my_function():
            # Function that may fail
            pass
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Log error
                    error_context = ErrorContext(
                        category=category,
                        severity=severity,
                        message=f"Attempt {attempt + 1}/{config.max_retries + 1} failed: {str(e)}",
                        details={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "exception_type": type(e).__name__,
                        },
                        retry_count=attempt,
                    )
                    _error_handler.log_error(error_context)
                    
                    # If last attempt, raise exception
                    if attempt == config.max_retries:
                        raise
                    
                    # Wait before retry
                    delay = config.get_delay(attempt)
                    logger.info(
                        f"Retrying {func.__name__} in {delay:.2f}s "
                        f"(attempt {attempt + 1}/{config.max_retries})"
                    )
                    await asyncio.sleep(delay)
            
            # Should never reach here, but just in case
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Log error
                    error_context = ErrorContext(
                        category=category,
                        severity=severity,
                        message=f"Attempt {attempt + 1}/{config.max_retries + 1} failed: {str(e)}",
                        details={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "exception_type": type(e).__name__,
                        },
                        retry_count=attempt,
                    )
                    _error_handler.log_error(error_context)
                    
                    # If last attempt, raise exception
                    if attempt == config.max_retries:
                        raise
                    
                    # Wait before retry
                    delay = config.get_delay(attempt)
                    logger.info(
                        f"Retrying {func.__name__} in {delay:.2f}s "
                        f"(attempt {attempt + 1}/{config.max_retries})"
                    )
                    time.sleep(delay)
            
            # Should never reach here, but just in case
            raise last_exception
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def with_fallback(
    fallback_func: Callable[..., T],
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
):
    """
    Decorator for automatic fallback on error.
    
    **Validates: Requirement 15.1**
    
    Args:
        fallback_func: Fallback function to call on error
        category: Error category
        severity: Error severity
    
    Example:
        def fallback():
            return "default value"
        
        @with_fallback(fallback)
        def my_function():
            # Function that may fail
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Log error
                error_context = ErrorContext(
                    category=category,
                    severity=severity,
                    message=f"Function failed, using fallback: {str(e)}",
                    details={
                        "function": func.__name__,
                        "exception_type": type(e).__name__,
                    },
                )
                _error_handler.log_error(error_context)
                
                # Call fallback
                logger.warning(f"Calling fallback for {func.__name__}")
                if asyncio.iscoroutinefunction(fallback_func):
                    return await fallback_func(*args, **kwargs)
                else:
                    return fallback_func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log error
                error_context = ErrorContext(
                    category=category,
                    severity=severity,
                    message=f"Function failed, using fallback: {str(e)}",
                    details={
                        "function": func.__name__,
                        "exception_type": type(e).__name__,
                    },
                )
                _error_handler.log_error(error_context)
                
                # Call fallback
                logger.warning(f"Calling fallback for {func.__name__}")
                return fallback_func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
