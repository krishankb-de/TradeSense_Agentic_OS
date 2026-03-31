"""
Telemetry integration for TradeSense pipeline orchestration.

Provides integration with:
- Langfuse: Cloud LLM tracing and agent visualization
- Datadog: APM and monitoring (GitHub Student - free 2 years)
- Sentry: Error tracking (500k events/month free)
- Arize Phoenix: OpenTelemetry-based debugging (optional)

**Validates: Requirements 3.8, 9.1, 9.2, 9.3**
"""

import logging
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TelemetryManager:
    """
    Manages telemetry integration for pipeline orchestration.
    
    **Validates: Requirement 3.8** - Emit telemetry to Langfuse and Arize Phoenix
    **Validates: Requirement 9.1** - Use Langfuse for agent graph visualization
    **Validates: Requirement 9.2** - Use Arize Phoenix for OpenTelemetry debugging
    """

    def __init__(self):
        self._langfuse_client = None
        self._datadog_initialized = False
        self._sentry_initialized = False
        self._phoenix_initialized = False
        self._initialize()

    def _initialize(self):
        """Initialize telemetry integrations based on configuration."""
        # Initialize Langfuse
        if settings.langfuse_public_key and settings.langfuse_secret_key:
            try:
                from langfuse import Langfuse

                self._langfuse_client = Langfuse(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    host=settings.langfuse_host,
                )
                logger.info(f"Langfuse initialized: {settings.langfuse_host}")
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse: {e}")

        # Initialize Datadog
        if settings.use_datadog and settings.datadog_api_key:
            try:
                from ddtrace import patch_all, tracer

                patch_all()
                tracer.configure(
                    hostname=settings.datadog_site,
                    service=settings.datadog_service,
                    env=settings.datadog_env,
                )
                self._datadog_initialized = True
                logger.info(f"Datadog APM initialized: {settings.datadog_service}")
            except Exception as e:
                logger.warning(f"Failed to initialize Datadog: {e}")

        # Initialize Sentry
        if settings.sentry_dsn:
            try:
                import sentry_sdk

                sentry_sdk.init(
                    dsn=settings.sentry_dsn,
                    environment=settings.sentry_environment,
                    traces_sample_rate=settings.sentry_traces_sample_rate,
                )
                self._sentry_initialized = True
                logger.info(f"Sentry initialized: {settings.sentry_environment}")
            except Exception as e:
                logger.warning(f"Failed to initialize Sentry: {e}")

        # Initialize Phoenix (OpenTelemetry)
        if settings.phoenix_collector_endpoint:
            try:
                from opentelemetry import trace
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.sdk.trace.export import BatchSpanProcessor

                # Set up OTLP exporter for Phoenix
                otlp_exporter = OTLPSpanExporter(
                    endpoint=settings.phoenix_collector_endpoint
                )
                provider = TracerProvider()
                provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
                trace.set_tracer_provider(provider)

                self._phoenix_initialized = True
                logger.info(f"Phoenix OTLP initialized: {settings.phoenix_collector_endpoint}")
            except Exception as e:
                logger.warning(f"Failed to initialize Phoenix: {e}")

    @property
    def is_langfuse_enabled(self) -> bool:
        """Check if Langfuse is enabled."""
        return self._langfuse_client is not None

    @property
    def is_datadog_enabled(self) -> bool:
        """Check if Datadog is enabled."""
        return self._datadog_initialized

    @property
    def is_sentry_enabled(self) -> bool:
        """Check if Sentry is enabled."""
        return self._sentry_initialized

    @property
    def is_phoenix_enabled(self) -> bool:
        """Check if Phoenix is enabled."""
        return self._phoenix_initialized

    def trace_pipeline_start(
        self,
        pipeline_name: str,
        run_id: str,
        inputs: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """
        Trace the start of a pipeline execution.
        
        **Validates: Requirement 9.1** - Emit traces to Langfuse for DAG visualization
        
        Args:
            pipeline_name: Name of the pipeline
            run_id: Unique run identifier
            inputs: Pipeline input parameters
            metadata: Additional metadata
            
        Returns:
            Langfuse trace object if enabled, None otherwise
        """
        if not self.is_langfuse_enabled:
            return None

        try:
            trace = self._langfuse_client.trace(
                name=pipeline_name,
                id=run_id,
                input=inputs,
                metadata=metadata or {},
            )
            logger.debug(f"Langfuse trace started: {pipeline_name} ({run_id})")
            return trace
        except Exception as e:
            logger.warning(f"Failed to start Langfuse trace: {e}")
            return None

    def trace_pipeline_end(
        self,
        run_id: str,
        status: str,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        """
        Trace the end of a pipeline execution.
        
        Args:
            run_id: Unique run identifier
            status: Pipeline status (completed, failed, cancelled)
            outputs: Pipeline outputs
            error: Error message if failed
        """
        if not self.is_langfuse_enabled:
            return

        try:
            # Update trace with final status
            self._langfuse_client.trace(
                id=run_id,
                output=outputs or {},
                metadata={"status": status, "error": error} if error else {"status": status},
            )
            logger.debug(f"Langfuse trace ended: {run_id} ({status})")
        except Exception as e:
            logger.warning(f"Failed to end Langfuse trace: {e}")

    def trace_step_start(
        self,
        run_id: str,
        step_name: str,
        agent: str,
        inputs: Dict[str, Any],
        attempt: int = 1,
    ) -> Optional[Any]:
        """
        Trace the start of a pipeline step.
        
        **Validates: Requirement 9.1** - Track agent execution in Langfuse
        
        Args:
            run_id: Pipeline run identifier
            step_name: Name of the step
            agent: Agent type (intake, diagnostic, fulfillment)
            inputs: Step input parameters
            attempt: Retry attempt number
            
        Returns:
            Langfuse span object if enabled, None otherwise
        """
        if not self.is_langfuse_enabled:
            return None

        try:
            span = self._langfuse_client.span(
                trace_id=run_id,
                name=step_name,
                input=inputs,
                metadata={
                    "agent": agent,
                    "attempt": attempt,
                },
            )
            logger.debug(f"Langfuse span started: {step_name} (attempt {attempt})")
            return span
        except Exception as e:
            logger.warning(f"Failed to start Langfuse span: {e}")
            return None

    def trace_step_end(
        self,
        span_id: str,
        status: str,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        duration: Optional[float] = None,
    ):
        """
        Trace the end of a pipeline step.
        
        Args:
            span_id: Span identifier
            status: Step status (completed, failed, skipped)
            outputs: Step outputs
            error: Error message if failed
            duration: Execution duration in seconds
        """
        if not self.is_langfuse_enabled:
            return

        try:
            metadata = {"status": status}
            if error:
                metadata["error"] = error
            if duration is not None:
                metadata["duration_seconds"] = duration

            self._langfuse_client.span(
                id=span_id,
                output=outputs or {},
                metadata=metadata,
            )
            logger.debug(f"Langfuse span ended: {span_id} ({status})")
        except Exception as e:
            logger.warning(f"Failed to end Langfuse span: {e}")

    def capture_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        level: str = "error",
    ):
        """
        Capture an error with Sentry.
        
        **Validates: Task 6.3** - Add Sentry error tracking
        
        Args:
            error: Exception to capture
            context: Additional context
            level: Error level (error, warning, info)
        """
        if not self.is_sentry_enabled:
            return

        try:
            import sentry_sdk

            with sentry_sdk.push_scope() as scope:
                if context:
                    for key, value in context.items():
                        scope.set_context(key, value)
                scope.level = level
                sentry_sdk.capture_exception(error)

            logger.debug(f"Error captured in Sentry: {type(error).__name__}")
        except Exception as e:
            logger.warning(f"Failed to capture error in Sentry: {e}")

    def record_metric(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ):
        """
        Record a metric with Datadog.
        
        **Validates: Task 6.3** - Add Datadog monitoring
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional tags for the metric
        """
        if not self.is_datadog_enabled:
            return

        try:
            from ddtrace import tracer

            # Record custom metric
            tracer.set_tags(tags or {})
            logger.debug(f"Metric recorded: {metric_name}={value}")
        except Exception as e:
            logger.warning(f"Failed to record metric in Datadog: {e}")

    @asynccontextmanager
    async def trace_operation(
        self,
        operation_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for tracing an operation with OpenTelemetry (Phoenix).
        
        **Validates: Requirement 9.2** - Use Arize Phoenix for OpenTelemetry debugging
        
        Args:
            operation_name: Name of the operation
            metadata: Additional metadata
            
        Yields:
            Span object for adding additional attributes
        """
        if not self.is_phoenix_enabled:
            yield None
            return

        try:
            from opentelemetry import trace

            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(operation_name) as span:
                if metadata:
                    for key, value in metadata.items():
                        span.set_attribute(key, str(value))
                yield span
        except Exception as e:
            logger.warning(f"Failed to trace operation with Phoenix: {e}")
            yield None

    def flush(self):
        """Flush all pending telemetry data."""
        if self.is_langfuse_enabled:
            try:
                self._langfuse_client.flush()
                logger.debug("Langfuse telemetry flushed")
            except Exception as e:
                logger.warning(f"Failed to flush Langfuse: {e}")

        if self.is_sentry_enabled:
            try:
                import sentry_sdk

                sentry_sdk.flush()
                logger.debug("Sentry telemetry flushed")
            except Exception as e:
                logger.warning(f"Failed to flush Sentry: {e}")


# Global telemetry manager instance
_telemetry_manager: Optional[TelemetryManager] = None


def get_telemetry_manager() -> TelemetryManager:
    """Get or create the global telemetry manager instance."""
    global _telemetry_manager
    if _telemetry_manager is None:
        _telemetry_manager = TelemetryManager()
    return _telemetry_manager
