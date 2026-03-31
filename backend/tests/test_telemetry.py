"""
Unit tests for telemetry integration.

**Validates: Requirements 3.8, 9.1, 9.2, 9.3**
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from orchestration.telemetry import TelemetryManager, get_telemetry_manager


class TestTelemetryManager:
    """Test TelemetryManager initialization and configuration."""

    @patch("orchestration.telemetry.settings")
    def test_initialization_without_credentials(self, mock_settings):
        """Test that TelemetryManager initializes gracefully without credentials."""
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = ""
        mock_settings.phoenix_collector_endpoint = ""

        manager = TelemetryManager()

        assert not manager.is_langfuse_enabled
        assert not manager.is_datadog_enabled
        assert not manager.is_sentry_enabled
        assert not manager.is_phoenix_enabled

    @patch("orchestration.telemetry.settings")
    def test_langfuse_initialization(self, mock_settings):
        """Test Langfuse initialization with valid credentials."""
        mock_settings.langfuse_public_key = "pk-test"
        mock_settings.langfuse_secret_key = "sk-test"
        mock_settings.langfuse_host = "https://cloud.langfuse.com"
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = ""
        mock_settings.phoenix_collector_endpoint = ""

        with patch("langfuse.Langfuse") as mock_langfuse_class:
            mock_langfuse_instance = MagicMock()
            mock_langfuse_class.return_value = mock_langfuse_instance

            manager = TelemetryManager()

            assert manager.is_langfuse_enabled
            mock_langfuse_class.assert_called_once_with(
                public_key="pk-test",
                secret_key="sk-test",
                host="https://cloud.langfuse.com",
            )

    @patch("orchestration.telemetry.settings")
    def test_sentry_initialization(self, mock_settings):
        """Test Sentry initialization with valid DSN."""
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = "https://test@sentry.io/123"
        mock_settings.sentry_environment = "test"
        mock_settings.sentry_traces_sample_rate = 1.0
        mock_settings.phoenix_collector_endpoint = ""

        with patch("sentry_sdk.init") as mock_sentry_init:
            manager = TelemetryManager()

            assert manager.is_sentry_enabled
            mock_sentry_init.assert_called_once_with(
                dsn="https://test@sentry.io/123",
                environment="test",
                traces_sample_rate=1.0,
            )

    @patch("orchestration.telemetry.settings")
    def test_initialization_handles_import_errors(self, mock_settings):
        """Test that initialization handles missing dependencies gracefully."""
        mock_settings.langfuse_public_key = "pk-test"
        mock_settings.langfuse_secret_key = "sk-test"
        mock_settings.langfuse_host = "https://cloud.langfuse.com"
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = ""
        mock_settings.phoenix_collector_endpoint = ""

        with patch("langfuse.Langfuse", side_effect=ImportError("Module not found")):
            manager = TelemetryManager()
            # Should not raise, just log warning
            assert not manager.is_langfuse_enabled


class TestPipelineTracing:
    """Test pipeline tracing with Langfuse."""

    @patch("orchestration.telemetry.settings")
    def test_trace_pipeline_start(self, mock_settings):
        """Test tracing pipeline start."""
        mock_settings.langfuse_public_key = "pk-test"
        mock_settings.langfuse_secret_key = "sk-test"
        mock_settings.langfuse_host = "https://cloud.langfuse.com"
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = ""
        mock_settings.phoenix_collector_endpoint = ""

        with patch("langfuse.Langfuse") as mock_langfuse_class:
            mock_langfuse = MagicMock()
            mock_trace = MagicMock()
            mock_langfuse.trace.return_value = mock_trace
            mock_langfuse_class.return_value = mock_langfuse

            manager = TelemetryManager()

            trace = manager.trace_pipeline_start(
                pipeline_name="test_pipeline",
                run_id="run-123",
                inputs={"key": "value"},
                metadata={"env": "test"},
            )

            assert trace == mock_trace
            mock_langfuse.trace.assert_called_once_with(
                name="test_pipeline",
                id="run-123",
                input={"key": "value"},
                metadata={"env": "test"},
            )

    @patch("orchestration.telemetry.settings")
    def test_trace_pipeline_end_success(self, mock_settings):
        """Test tracing pipeline end with success."""
        mock_settings.langfuse_public_key = "pk-test"
        mock_settings.langfuse_secret_key = "sk-test"
        mock_settings.langfuse_host = "https://cloud.langfuse.com"
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = ""
        mock_settings.phoenix_collector_endpoint = ""

        with patch("langfuse.Langfuse") as mock_langfuse_class:
            mock_langfuse = MagicMock()
            mock_langfuse_class.return_value = mock_langfuse

            manager = TelemetryManager()

            manager.trace_pipeline_end(
                run_id="run-123",
                status="completed",
                outputs={"result": "success"},
            )

            mock_langfuse.trace.assert_called_once_with(
                id="run-123",
                output={"result": "success"},
                metadata={"status": "completed"},
            )

    @patch("orchestration.telemetry.settings")
    def test_trace_pipeline_end_failure(self, mock_settings):
        """Test tracing pipeline end with failure."""
        mock_settings.langfuse_public_key = "pk-test"
        mock_settings.langfuse_secret_key = "sk-test"
        mock_settings.langfuse_host = "https://cloud.langfuse.com"
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = ""
        mock_settings.phoenix_collector_endpoint = ""

        with patch("langfuse.Langfuse") as mock_langfuse_class:
            mock_langfuse = MagicMock()
            mock_langfuse_class.return_value = mock_langfuse

            manager = TelemetryManager()

            manager.trace_pipeline_end(
                run_id="run-123",
                status="failed",
                error="Test error",
            )

            mock_langfuse.trace.assert_called_once_with(
                id="run-123",
                output={},
                metadata={"status": "failed", "error": "Test error"},
            )

    @patch("orchestration.telemetry.settings")
    def test_trace_pipeline_without_langfuse(self, mock_settings):
        """Test that tracing works gracefully without Langfuse."""
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = ""
        mock_settings.phoenix_collector_endpoint = ""

        manager = TelemetryManager()

        # Should not raise
        trace = manager.trace_pipeline_start(
            pipeline_name="test_pipeline",
            run_id="run-123",
            inputs={},
        )
        assert trace is None

        manager.trace_pipeline_end(run_id="run-123", status="completed")


class TestStepTracing:
    """Test step tracing with Langfuse."""

    @patch("orchestration.telemetry.settings")
    def test_trace_step_start(self, mock_settings):
        """Test tracing step start."""
        mock_settings.langfuse_public_key = "pk-test"
        mock_settings.langfuse_secret_key = "sk-test"
        mock_settings.langfuse_host = "https://cloud.langfuse.com"
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = ""
        mock_settings.phoenix_collector_endpoint = ""

        with patch("langfuse.Langfuse") as mock_langfuse_class:
            mock_langfuse = MagicMock()
            mock_span = MagicMock()
            mock_langfuse.span.return_value = mock_span
            mock_langfuse_class.return_value = mock_langfuse

            manager = TelemetryManager()

            span = manager.trace_step_start(
                run_id="run-123",
                step_name="intake",
                agent="intake_agent",
                inputs={"customer": "John"},
                attempt=1,
            )

            assert span == mock_span
            mock_langfuse.span.assert_called_once_with(
                trace_id="run-123",
                name="intake",
                input={"customer": "John"},
                metadata={"agent": "intake_agent", "attempt": 1},
            )

    @patch("orchestration.telemetry.settings")
    def test_trace_step_end(self, mock_settings):
        """Test tracing step end."""
        mock_settings.langfuse_public_key = "pk-test"
        mock_settings.langfuse_secret_key = "sk-test"
        mock_settings.langfuse_host = "https://cloud.langfuse.com"
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = ""
        mock_settings.phoenix_collector_endpoint = ""

        with patch("langfuse.Langfuse") as mock_langfuse_class:
            mock_langfuse = MagicMock()
            mock_langfuse_class.return_value = mock_langfuse

            manager = TelemetryManager()

            manager.trace_step_end(
                span_id="span-456",
                status="completed",
                outputs={"lead_id": "123"},
                duration=1.5,
            )

            mock_langfuse.span.assert_called_once_with(
                id="span-456",
                output={"lead_id": "123"},
                metadata={"status": "completed", "duration_seconds": 1.5},
            )


class TestErrorCapture:
    """Test error capture with Sentry."""

    @patch("orchestration.telemetry.settings")
    def test_capture_error(self, mock_settings):
        """Test capturing errors with Sentry."""
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = "https://test@sentry.io/123"
        mock_settings.sentry_environment = "test"
        mock_settings.sentry_traces_sample_rate = 1.0
        mock_settings.phoenix_collector_endpoint = ""

        with patch("sentry_sdk.init"), \
             patch("sentry_sdk.push_scope") as mock_push_scope, \
             patch("sentry_sdk.capture_exception") as mock_capture:
            
            mock_scope = MagicMock()
            mock_push_scope.return_value.__enter__.return_value = mock_scope

            manager = TelemetryManager()

            error = ValueError("Test error")
            context = {"pipeline": "test", "step": "intake"}

            manager.capture_error(error, context=context, level="error")

            mock_push_scope.assert_called_once()
            mock_scope.set_context.assert_any_call("pipeline", "test")
            mock_scope.set_context.assert_any_call("step", "intake")
            assert mock_scope.level == "error"
            mock_capture.assert_called_once_with(error)

    @patch("orchestration.telemetry.settings")
    def test_capture_error_without_sentry(self, mock_settings):
        """Test that error capture works gracefully without Sentry."""
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = ""
        mock_settings.phoenix_collector_endpoint = ""

        manager = TelemetryManager()

        # Should not raise
        error = ValueError("Test error")
        manager.capture_error(error)


class TestMetrics:
    """Test metrics recording with Datadog."""

    @patch("orchestration.telemetry.settings")
    def test_record_metric(self, mock_settings):
        """Test recording metrics with Datadog."""
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""
        mock_settings.use_datadog = True
        mock_settings.datadog_api_key = "test-key"
        mock_settings.datadog_site = "datadoghq.com"
        mock_settings.datadog_service = "tradesense"
        mock_settings.datadog_env = "test"
        mock_settings.sentry_dsn = ""
        mock_settings.phoenix_collector_endpoint = ""

        with patch("ddtrace.patch_all"), \
             patch("ddtrace.tracer") as mock_tracer:
            
            manager = TelemetryManager()

            manager.record_metric(
                "pipeline.duration",
                1.5,
                tags={"pipeline": "test", "status": "completed"},
            )

            # Verify tracer was configured (actual metric recording is internal to ddtrace)
            assert manager.is_datadog_enabled

    @patch("orchestration.telemetry.settings")
    def test_record_metric_without_datadog(self, mock_settings):
        """Test that metric recording works gracefully without Datadog."""
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = ""
        mock_settings.phoenix_collector_endpoint = ""

        manager = TelemetryManager()

        # Should not raise
        manager.record_metric("test.metric", 1.0)


@pytest.mark.asyncio
class TestPhoenixTracing:
    """Test OpenTelemetry tracing with Phoenix."""

    @patch("orchestration.telemetry.settings")
    async def test_trace_operation_without_phoenix(self, mock_settings):
        """Test that operation tracing works gracefully without Phoenix."""
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = ""
        mock_settings.phoenix_collector_endpoint = ""

        manager = TelemetryManager()

        async with manager.trace_operation("test_op") as span:
            assert span is None


class TestTelemetryFlush:
    """Test telemetry flushing."""

    @patch("orchestration.telemetry.settings")
    def test_flush(self, mock_settings):
        """Test flushing telemetry data."""
        mock_settings.langfuse_public_key = "pk-test"
        mock_settings.langfuse_secret_key = "sk-test"
        mock_settings.langfuse_host = "https://cloud.langfuse.com"
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = "https://test@sentry.io/123"
        mock_settings.sentry_environment = "test"
        mock_settings.sentry_traces_sample_rate = 1.0
        mock_settings.phoenix_collector_endpoint = ""

        with patch("langfuse.Langfuse") as mock_langfuse_class, \
             patch("sentry_sdk.init"), \
             patch("sentry_sdk.flush") as mock_sentry_flush:
            
            mock_langfuse = MagicMock()
            mock_langfuse_class.return_value = mock_langfuse

            manager = TelemetryManager()
            manager.flush()

            mock_langfuse.flush.assert_called_once()
            mock_sentry_flush.assert_called_once()


class TestGetTelemetryManager:
    """Test global telemetry manager singleton."""

    def test_get_telemetry_manager_singleton(self):
        """Test that get_telemetry_manager returns the same instance."""
        manager1 = get_telemetry_manager()
        manager2 = get_telemetry_manager()

        assert manager1 is manager2

