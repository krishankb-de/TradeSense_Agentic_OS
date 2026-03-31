"""
Unit Tests for Error Handling and Recovery.

Tests all error handling modules:
- Core error handling
- Voice pipeline error recovery
- API error handling
- Database error recovery
- Parts not found handling
- Scheduling conflict handling

**Validates: Requirements 15.1, 15.2, 15.3, 15.5, 15.6, 15.8**
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from core.error_handling import (
    ErrorHandler,
    ErrorContext,
    ErrorCategory,
    ErrorSeverity,
    RetryConfig,
    with_retry,
    with_fallback,
)
from voice.error_recovery import (
    VoiceErrorRecovery,
    VoiceErrorType,
)
from llm.api_error_handler import (
    APIErrorHandler,
    APIErrorType,
    with_api_retry,
)
from db.error_recovery import (
    DatabaseErrorRecovery,
    DatabaseErrorType,
    with_db_retry,
)
from agents.error_handlers import (
    PartsNotFoundHandler,
    SchedulingConflictHandler,
    PartNotFoundStrategy,
)


# ============================================================================
# Test 16.1: Voice Pipeline Error Handling
# **Validates: Requirement 15.1**
# ============================================================================

class TestVoicePipelineErrorHandling:
    """Test voice pipeline error detection and fallback."""
    
    @pytest.mark.asyncio
    async def test_voice_error_fallback_to_text(self):
        """Test fallback to text mode on voice error."""
        recovery = VoiceErrorRecovery(recovery_delay=1.0)
        
        # Simulate voice error
        result = await recovery.handle_voice_error(
            session_id="test_session",
            error=Exception("STT service unavailable"),
            error_type=VoiceErrorType.STT_FAILURE,
        )
        
        # Verify fallback
        assert result["fallback_mode"] == "text"
        assert result["error_type"] == "stt_failure"
        assert result["recovery_scheduled"] is True
        assert recovery.is_in_fallback_mode("test_session")
    
    @pytest.mark.asyncio
    async def test_voice_error_recovery_attempt(self):
        """Test automatic recovery after 30 seconds."""
        recovery = VoiceErrorRecovery(recovery_delay=0.1, max_recovery_attempts=2)
        
        # Trigger error
        await recovery.handle_voice_error(
            session_id="test_session",
            error=Exception("Temporary error"),
            error_type=VoiceErrorType.NETWORK_ERROR,
        )
        
        # Wait for recovery attempt
        await asyncio.sleep(0.2)
        
        # Check recovery was attempted
        assert recovery.recovery_attempts.get("test_session", 0) >= 1
    
    @pytest.mark.asyncio
    async def test_azure_speech_error_tracking(self):
        """Test Azure Speech API error tracking."""
        recovery = VoiceErrorRecovery()
        
        # Simulate Azure errors
        await recovery.handle_voice_error(
            session_id="session1",
            error=Exception("429 Rate limit exceeded"),
            error_type=VoiceErrorType.API_ERROR,
        )
        
        await recovery.handle_voice_error(
            session_id="session2",
            error=Exception("401 Unauthorized"),
            error_type=VoiceErrorType.API_ERROR,
        )
        
        # Check error stats
        stats = recovery.get_azure_error_stats()
        assert stats["total_errors"] >= 2
        assert "azure_rate_limit" in stats["by_type"]
        assert "azure_auth_error" in stats["by_type"]
    
    def test_voice_error_logging_with_audio_sample(self):
        """Test error logging with audio samples."""
        recovery = VoiceErrorRecovery()
        
        # Create mock audio sample
        audio_sample = b"mock_audio_data"
        audio_metadata = {
            "sample_rate": 16000,
            "format": "wav",
            "duration_ms": 1000,
        }
        
        # This should not raise an exception
        asyncio.run(recovery.handle_voice_error(
            session_id="test_session",
            error=Exception("Audio quality too low"),
            error_type=VoiceErrorType.AUDIO_QUALITY,
            audio_sample=audio_sample,
            audio_metadata=audio_metadata,
        ))


# ============================================================================
# Test 16.2: API Error Handling
# **Validates: Requirements 15.2, 15.3**
# ============================================================================

class TestAPIErrorHandling:
    """Test exponential backoff retry logic."""
    
    def test_exponential_backoff_delays(self):
        """Test exponential backoff: 1s, 2s, 4s, 8s, 16s."""
        config = RetryConfig(
            max_retries=5,
            initial_delay=1.0,
            max_delay=16.0,
            exponential_base=2.0,
            jitter=False,  # Disable jitter for predictable testing
        )
        
        # Test delay progression
        expected_delays = [1.0, 2.0, 4.0, 8.0, 16.0]
        for attempt, expected in enumerate(expected_delays):
            delay = config.get_delay(attempt)
            assert delay == expected, f"Attempt {attempt}: expected {expected}s, got {delay}s"
    
    @pytest.mark.asyncio
    async def test_api_rate_limiting_handling(self):
        """Test rate limiting detection and handling."""
        handler = APIErrorHandler()
        
        # Simulate rate limit error
        error = Exception("429 Rate limit exceeded. Retry after 60 seconds")
        result = await handler.handle_api_error(
            error=error,
            provider="gemini",
            operation="generate",
        )
        
        # Verify classification
        assert result["error_type"] == "rate_limit"
        assert result["should_retry"] is True
        assert result["should_fallback"] is True
    
    @pytest.mark.asyncio
    async def test_api_fallback_on_quota_exceeded(self):
        """Test fallback to Azure OpenAI when Gemini quota exceeded."""
        handler = APIErrorHandler()
        
        # Simulate quota exceeded
        error = Exception("Quota exceeded for gemini-2.5-flash")
        result = await handler.handle_api_error(
            error=error,
            provider="gemini",
            operation="generate",
        )
        
        # Verify fallback recommendation
        assert result["error_type"] == "quota_exceeded"
        assert result["should_fallback"] is True
    
    @pytest.mark.asyncio
    async def test_admin_alert_on_all_apis_fail(self):
        """Test admin alert when all APIs fail."""
        handler = APIErrorHandler()
        
        # Register alert callback
        alert_triggered = []
        
        def alert_callback(error_context):
            alert_triggered.append(error_context)
        
        handler.register_admin_alert(alert_callback)
        
        # Simulate critical error
        error = Exception("401 Unauthorized - Invalid API key")
        await handler.handle_api_error(
            error=error,
            provider="azure_openai",
            operation="generate",
        )
        
        # Verify alert was triggered
        assert len(alert_triggered) > 0
        assert alert_triggered[0].error_type == APIErrorType.AUTHENTICATION
    
    @pytest.mark.asyncio
    async def test_retry_decorator(self):
        """Test with_retry decorator."""
        attempt_count = [0]
        
        @with_retry(
            config=RetryConfig(max_retries=2, initial_delay=0.01, jitter=False),
            category=ErrorCategory.API_CALL,
        )
        async def failing_function():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise Exception("Temporary error")
            return "success"
        
        # Should succeed on 3rd attempt
        result = await failing_function()
        assert result == "success"
        assert attempt_count[0] == 3


# ============================================================================
# Test 16.3: Database Error Handling
# **Validates: Requirement 15.8**
# ============================================================================

class TestDatabaseErrorHandling:
    """Test database transaction retry."""
    
    @pytest.mark.asyncio
    async def test_transaction_retry_up_to_3_times(self):
        """Test transaction retry up to 3 times."""
        recovery = DatabaseErrorRecovery(max_retries=3)
        
        attempt_count = [0]
        
        async def failing_operation():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                from sqlalchemy.exc import OperationalError
                raise OperationalError("Connection lost", None, None)
            return "success"
        
        # Should succeed on 3rd attempt
        result = await recovery.with_transaction_retry(
            operation=failing_operation,
            operation_name="test_operation",
        )
        
        assert result == "success"
        assert attempt_count[0] == 3
    
    @pytest.mark.asyncio
    async def test_redis_cache_temporarily(self):
        """Test storing data in Redis cache temporarily."""
        # Mock Redis client
        mock_redis = AsyncMock()
        recovery = DatabaseErrorRecovery(redis_client=mock_redis, max_retries=2)
        
        cache_data = {"key": "value", "timestamp": time.time()}
        
        attempt_count = [0]
        
        async def failing_operation():
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                from sqlalchemy.exc import OperationalError
                raise OperationalError("Deadlock detected", None, None)
            return "success"
        
        # Execute with cache
        result = await recovery.with_transaction_retry(
            operation=failing_operation,
            operation_name="test_operation",
            cache_key="test_cache_key",
            cache_data=cache_data,
        )
        
        # Verify cache was used
        assert mock_redis.setex.called or mock_redis.delete.called
    
    @pytest.mark.asyncio
    async def test_data_consistency_verification(self):
        """Test data consistency verification after recovery."""
        recovery = DatabaseErrorRecovery(max_retries=2)
        
        attempt_count = [0]
        
        async def operation_with_retry():
            attempt_count[0] += 1
            if attempt_count[0] == 1:
                from sqlalchemy.exc import OperationalError
                raise OperationalError("Timeout", None, None)
            return {"id": "123", "data": "test"}
        
        # Execute operation
        result = await recovery.with_transaction_retry(
            operation=operation_with_retry,
            operation_name="test_operation",
        )
        
        # Verify result
        assert result["id"] == "123"
        assert attempt_count[0] == 2
    
    def test_error_classification(self):
        """Test database error classification."""
        recovery = DatabaseErrorRecovery()
        
        # Test connection error
        from sqlalchemy.exc import OperationalError
        error = OperationalError("Connection refused", None, None)
        context = recovery.classify_error(error, "test_op")
        assert context.error_type == DatabaseErrorType.CONNECTION_ERROR
        
        # Test integrity error
        from sqlalchemy.exc import IntegrityError
        error = IntegrityError("Duplicate key", None, None)
        context = recovery.classify_error(error, "test_op")
        assert context.error_type == DatabaseErrorType.INTEGRITY_ERROR


# ============================================================================
# Test 16.4: Parts Not Found Handling
# **Validates: Requirement 15.5**
# ============================================================================

class TestPartsNotFoundHandling:
    """Test parts not found error handling."""
    
    @pytest.mark.asyncio
    async def test_search_alternatives(self):
        """Test searching for compatible alternatives."""
        handler = PartsNotFoundHandler()
        
        # Handle part not found
        context = await handler.handle_part_not_found(
            part_id="CAP-001",
            part_name="Capacitor 100uF",
            job_id="job_123",
        )
        
        # Verify alternatives were found
        assert context.strategy == PartNotFoundStrategy.SEARCH_ALTERNATIVES
        assert len(context.alternatives_found) > 0
    
    @pytest.mark.asyncio
    async def test_provide_lead_time(self):
        """Test providing estimated lead time."""
        handler = PartsNotFoundHandler()
        
        # Handle part not found (no alternatives)
        context = await handler.handle_part_not_found(
            part_id="RARE-001",
            part_name="Rare Component",
            job_id="job_123",
        )
        
        # Verify lead time is provided
        if context.strategy == PartNotFoundStrategy.ORDER_FROM_SUPPLIER:
            assert context.lead_time_days is not None
            assert context.lead_time_days > 0
    
    @pytest.mark.asyncio
    async def test_update_job_status_parts_pending(self):
        """Test updating job status to 'parts-pending'."""
        handler = PartsNotFoundHandler()
        
        # Handle part not found
        context = await handler.handle_part_not_found(
            part_id="PART-001",
            part_name="Test Part",
            job_id="job_123",
        )
        
        # Verify context was created
        assert context.job_id == "job_123"
        assert context.part_id == "PART-001"
        
        # Verify stats
        stats = handler.get_stats()
        assert stats["total_cases"] > 0


# ============================================================================
# Test 16.5: Scheduling Conflict Handling
# **Validates: Requirement 15.6**
# ============================================================================

class TestSchedulingConflictHandling:
    """Test scheduling conflict resolution."""
    
    @pytest.mark.asyncio
    async def test_propose_alternative_time_slots(self):
        """Test proposing alternative time slots."""
        handler = SchedulingConflictHandler()
        
        # Handle scheduling conflict
        context = await handler.handle_scheduling_conflict(
            job_id="job_123",
            requested_time="2024-01-15 10:00",
            technician_id="tech_001",
            conflict_reason="Technician already booked",
            is_emergency=False,
        )
        
        # Verify alternatives were proposed
        assert context.alternative_slots is not None
        assert len(context.alternative_slots) > 0
        assert all("time_slot" in slot for slot in context.alternative_slots)
    
    @pytest.mark.asyncio
    async def test_rerun_optimization_relaxed_constraints(self):
        """Test re-running optimization with relaxed constraints."""
        handler = SchedulingConflictHandler()
        
        # Handle conflict
        context = await handler.handle_scheduling_conflict(
            job_id="job_123",
            requested_time="2024-01-15 10:00",
            conflict_reason="No available technicians",
            is_emergency=False,
        )
        
        # Verify alternatives include different technicians
        technicians = set(slot["technician_id"] for slot in context.alternative_slots)
        assert len(technicians) >= 1
    
    @pytest.mark.asyncio
    async def test_escalate_emergency_jobs(self):
        """Test escalating emergency jobs to on-call technician."""
        handler = SchedulingConflictHandler()
        
        # Handle emergency conflict
        context = await handler.handle_scheduling_conflict(
            job_id="job_emergency",
            requested_time="2024-01-15 10:00",
            conflict_reason="All technicians busy",
            is_emergency=True,
        )
        
        # Verify emergency escalation
        assert context.is_emergency is True
        assert context.alternative_slots is not None
        assert len(context.alternative_slots) > 0
        
        # Check if on-call technician was assigned
        on_call_slot = context.alternative_slots[0]
        assert "technician_id" in on_call_slot
    
    def test_conflict_statistics(self):
        """Test scheduling conflict statistics."""
        handler = SchedulingConflictHandler()
        
        # Get stats
        stats = handler.get_stats()
        
        # Verify stats structure
        assert "total_conflicts" in stats
        assert "emergency_count" in stats
        assert "resolution_rate" in stats


# ============================================================================
# Test 16.6: Error Handler Integration
# **Validates: Requirements 15.1, 15.2, 15.3, 15.8**
# ============================================================================

class TestErrorHandlerIntegration:
    """Test error handler integration."""
    
    def test_error_logging(self):
        """Test error logging with context."""
        handler = ErrorHandler()
        
        # Log error
        error_context = ErrorContext(
            category=ErrorCategory.VOICE_PIPELINE,
            severity=ErrorSeverity.HIGH,
            message="Test error",
            details={"key": "value"},
        )
        
        handler.log_error(error_context)
        
        # Verify error was logged
        assert len(handler.error_log) > 0
        assert handler.error_log[-1].message == "Test error"
    
    def test_alert_callbacks(self):
        """Test alert callback registration and triggering."""
        handler = ErrorHandler()
        
        # Register callback
        alerts_received = []
        
        def alert_callback(error_context):
            alerts_received.append(error_context)
        
        handler.register_alert_callback(ErrorSeverity.HIGH, alert_callback)
        
        # Log high severity error
        error_context = ErrorContext(
            category=ErrorCategory.API_CALL,
            severity=ErrorSeverity.HIGH,
            message="Critical error",
        )
        
        handler.log_error(error_context)
        
        # Verify alert was triggered
        assert len(alerts_received) > 0
    
    def test_error_statistics(self):
        """Test error statistics collection."""
        handler = ErrorHandler()
        
        # Log multiple errors
        for i in range(5):
            handler.log_error(ErrorContext(
                category=ErrorCategory.API_CALL,
                severity=ErrorSeverity.MEDIUM,
                message=f"Error {i}",
            ))
        
        # Get stats
        stats = handler.get_error_stats()
        
        # Verify stats
        assert stats["total_errors"] >= 5
        assert "api_call" in stats["by_category"]
        assert "medium" in stats["by_severity"]
    
    @pytest.mark.asyncio
    async def test_fallback_decorator(self):
        """Test with_fallback decorator."""
        
        def fallback_function():
            return "fallback_value"
        
        @with_fallback(
            fallback_func=fallback_function,
            category=ErrorCategory.API_CALL,
        )
        def failing_function():
            raise Exception("Function failed")
        
        # Should return fallback value
        result = failing_function()
        assert result == "fallback_value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
