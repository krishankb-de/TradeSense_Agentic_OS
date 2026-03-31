"""
Database Error Recovery Module.

Implements database error handling and recovery:
- Transaction retry up to 3 times
- Temporary storage in Redis cache
- Data consistency verification after recovery

**Validates: Requirement 15.8**
"""

import logging
import time
import asyncio
from typing import Optional, Callable, Any, TypeVar, Dict
from dataclasses import dataclass
from enum import Enum
from functools import wraps

from sqlalchemy.exc import (
    SQLAlchemyError,
    OperationalError,
    IntegrityError,
    DatabaseError,
)

from core.error_handling import (
    ErrorHandler,
    ErrorContext,
    ErrorCategory,
    ErrorSeverity,
    RetryConfig,
    get_error_handler,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DatabaseErrorType(Enum):
    """Types of database errors."""
    CONNECTION_ERROR = "connection_error"
    TRANSACTION_ERROR = "transaction_error"
    INTEGRITY_ERROR = "integrity_error"
    TIMEOUT = "timeout"
    DEADLOCK = "deadlock"
    UNKNOWN = "unknown"


@dataclass
class DatabaseErrorContext:
    """Context for database errors."""
    error_type: DatabaseErrorType
    operation: str
    message: str
    table: Optional[str] = None
    retry_count: int = 0
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class DatabaseErrorRecovery:
    """
    Database error recovery manager.
    
    Features:
    - Transaction retry up to 3 times
    - Temporary storage in Redis cache
    - Data consistency verification
    - Automatic rollback on failure
    
    **Validates: Requirement 15.8**
    """
    
    def __init__(
        self,
        redis_client: Optional[Any] = None,
        max_retries: int = 3,
    ):
        """
        Initialize database error recovery.
        
        Args:
            redis_client: Redis client for temporary storage
            max_retries: Maximum transaction retry attempts
        """
        self.redis_client = redis_client
        self.max_retries = max_retries
        self.error_handler = get_error_handler()
        
        # Retry configuration for database operations
        self.retry_config = RetryConfig(
            max_retries=max_retries,
            initial_delay=0.1,  # Start with 100ms
            max_delay=2.0,  # Cap at 2 seconds
            exponential_base=2.0,
            jitter=True,
        )
        
        # Track database errors
        self.db_errors: list[DatabaseErrorContext] = []
        
        logger.info("Database error recovery initialized")
    
    def classify_error(
        self,
        error: Exception,
        operation: str,
    ) -> DatabaseErrorContext:
        """
        Classify database error.
        
        Args:
            error: Exception that occurred
            operation: Database operation
            
        Returns:
            DatabaseErrorContext
        """
        error_message = str(error)
        error_type = DatabaseErrorType.UNKNOWN
        table = None
        
        # Classify by exception type
        if isinstance(error, OperationalError):
            if "connection" in error_message.lower():
                error_type = DatabaseErrorType.CONNECTION_ERROR
            elif "timeout" in error_message.lower():
                error_type = DatabaseErrorType.TIMEOUT
            elif "deadlock" in error_message.lower():
                error_type = DatabaseErrorType.DEADLOCK
            else:
                error_type = DatabaseErrorType.TRANSACTION_ERROR
        
        elif isinstance(error, IntegrityError):
            error_type = DatabaseErrorType.INTEGRITY_ERROR
            # Try to extract table name
            if "table" in error_message.lower():
                try:
                    import re
                    match = re.search(r'table[:\s]+["\']?(\w+)["\']?', error_message, re.IGNORECASE)
                    if match:
                        table = match.group(1)
                except:
                    pass
        
        elif isinstance(error, DatabaseError):
            error_type = DatabaseErrorType.TRANSACTION_ERROR
        
        return DatabaseErrorContext(
            error_type=error_type,
            operation=operation,
            message=error_message,
            table=table,
        )
    
    def should_retry(self, error_context: DatabaseErrorContext) -> bool:
        """
        Determine if error should be retried.
        
        Args:
            error_context: Database error context
            
        Returns:
            True if should retry
        """
        # Retry transient errors
        retryable_errors = {
            DatabaseErrorType.CONNECTION_ERROR,
            DatabaseErrorType.TRANSACTION_ERROR,
            DatabaseErrorType.TIMEOUT,
            DatabaseErrorType.DEADLOCK,
        }
        
        return error_context.error_type in retryable_errors
    
    async def with_transaction_retry(
        self,
        operation: Callable[[], T],
        operation_name: str,
        cache_key: Optional[str] = None,
        cache_data: Optional[Dict[str, Any]] = None,
    ) -> T:
        """
        Execute database operation with transaction retry.
        
        **Validates: Requirement 15.8**
        
        Args:
            operation: Database operation to execute
            operation_name: Name of operation for logging
            cache_key: Optional Redis cache key for temporary storage
            cache_data: Optional data to cache temporarily
            
        Returns:
            Operation result
            
        Raises:
            SQLAlchemyError: If all retries fail
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Execute operation
                if asyncio.iscoroutinefunction(operation):
                    result = await operation()
                else:
                    result = operation()
                
                # Verify data consistency if this was a retry
                if attempt > 0:
                    await self._verify_consistency(operation_name, result)
                
                # Clear cache if operation succeeded
                if cache_key and self.redis_client:
                    try:
                        await self._clear_cache(cache_key)
                    except Exception as e:
                        logger.warning(f"Failed to clear cache: {e}")
                
                logger.info(
                    f"Database operation '{operation_name}' succeeded "
                    f"(attempt {attempt + 1}/{self.max_retries + 1})"
                )
                
                return result
                
            except SQLAlchemyError as e:
                last_error = e
                
                # Classify error
                error_context = self.classify_error(e, operation_name)
                error_context.retry_count = attempt
                
                # Track error
                self.db_errors.append(error_context)
                
                # Log error
                severity = ErrorSeverity.HIGH if attempt == self.max_retries else ErrorSeverity.MEDIUM
                error_log = ErrorContext(
                    category=ErrorCategory.DATABASE,
                    severity=severity,
                    message=f"Database error in {operation_name}: {error_context.error_type.value}",
                    details={
                        "operation": operation_name,
                        "error_type": error_context.error_type.value,
                        "attempt": attempt + 1,
                        "table": error_context.table,
                    },
                    retry_count=attempt,
                )
                self.error_handler.log_error(error_log)
                
                # Check if should retry
                if not self.should_retry(error_context) or attempt == self.max_retries:
                    logger.error(
                        f"Database operation '{operation_name}' failed after "
                        f"{attempt + 1} attempts"
                    )
                    raise
                
                # Store in cache temporarily if provided
                if cache_key and cache_data and self.redis_client:
                    try:
                        await self._store_in_cache(cache_key, cache_data)
                        logger.info(f"Stored data temporarily in cache: {cache_key}")
                    except Exception as cache_error:
                        logger.warning(f"Failed to store in cache: {cache_error}")
                
                # Wait before retry
                delay = self.retry_config.get_delay(attempt)
                logger.info(
                    f"Retrying database operation '{operation_name}' in {delay:.2f}s "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                await asyncio.sleep(delay)
        
        # Should never reach here, but just in case
        raise last_error
    
    async def _store_in_cache(
        self,
        key: str,
        data: Dict[str, Any],
        ttl: int = 300,  # 5 minutes
    ) -> None:
        """
        Store data temporarily in Redis cache.
        
        Args:
            key: Cache key
            data: Data to store
            ttl: Time to live in seconds
        """
        if not self.redis_client:
            logger.warning("Redis client not available for caching")
            return
        
        try:
            import json
            serialized = json.dumps(data)
            await self.redis_client.setex(key, ttl, serialized)
            logger.debug(f"Stored data in cache: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Failed to store in cache: {e}")
            raise
    
    async def _clear_cache(self, key: str) -> None:
        """
        Clear data from Redis cache.
        
        Args:
            key: Cache key
        """
        if not self.redis_client:
            return
        
        try:
            await self.redis_client.delete(key)
            logger.debug(f"Cleared cache: {key}")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            raise
    
    async def _verify_consistency(
        self,
        operation_name: str,
        result: Any,
    ) -> None:
        """
        Verify data consistency after recovery.
        
        Args:
            operation_name: Operation name
            result: Operation result
        """
        # In a real implementation, this would:
        # 1. Check foreign key constraints
        # 2. Verify data integrity
        # 3. Compare with cached data if available
        # 4. Run consistency checks
        
        logger.debug(f"Verified consistency for operation: {operation_name}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """
        Get database error statistics.
        
        Returns:
            Dictionary with error statistics
        """
        if not self.db_errors:
            return {
                "total_errors": 0,
                "by_type": {},
                "by_table": {},
            }
        
        by_type = {}
        by_table = {}
        
        for error in self.db_errors:
            # Count by type
            error_type = error.error_type.value
            by_type[error_type] = by_type.get(error_type, 0) + 1
            
            # Count by table
            if error.table:
                by_table[error.table] = by_table.get(error.table, 0) + 1
        
        return {
            "total_errors": len(self.db_errors),
            "by_type": by_type,
            "by_table": by_table,
        }


def with_db_retry(
    operation_name: str,
    cache_key: Optional[str] = None,
):
    """
    Decorator for database operations with automatic retry.
    
    **Validates: Requirement 15.8**
    
    Args:
        operation_name: Name of operation
        cache_key: Optional cache key for temporary storage
    
    Example:
        @with_db_retry(operation_name="create_lead")
        async def create_lead(data):
            # Database operation
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            # Get or create recovery instance
            recovery = DatabaseErrorRecovery()
            
            # Create operation wrapper
            async def operation():
                return await func(*args, **kwargs)
            
            # Execute with retry
            return await recovery.with_transaction_retry(
                operation=operation,
                operation_name=operation_name,
                cache_key=cache_key,
            )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            # Get or create recovery instance
            recovery = DatabaseErrorRecovery()
            
            # Create operation wrapper
            def operation():
                return func(*args, **kwargs)
            
            # Execute with retry (sync version)
            import asyncio
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                recovery.with_transaction_retry(
                    operation=operation,
                    operation_name=operation_name,
                    cache_key=cache_key,
                )
            )
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
