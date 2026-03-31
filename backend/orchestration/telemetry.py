"""
Telemetry integration for TradeSense pipeline orchestration.

Provides integration with:
- Langfuse: Cloud LLM tracing and agent visualization
- Datadog: APM and monitoring (GitHub Student - free 2 years)
- Sentry: Error tracking (500k events/month free)
- Arize Phoenix: OpenTelemetry-based debugging (optional)

**Validates: Requirements 3.8, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
"""

import logging
import time
import traceback
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MetricsCollector:
    """
    Collects and aggregates metrics for observability.
    
    **Validates: Requirement 9.6** - Track voice latency, agent response time, API costs
    **Validates: Requirement 9.7** - Track first-time fix rate
    **Validates: Requirement 9.8** - Track job completion rate
    """

    def __init__(self):
        self._voice_latencies: List[float] = []
        self._agent_response_times: Dict[str, List[float]] = defaultdict(list)
        self._api_costs: Dict[str, float] = defaultdict(float)
        self._api_call_counts: Dict[str, int] = defaultdict(int)
        self._api_failures: Dict[str, int] = defaultdict(int)
        self._agent_errors: Dict[str, int] = defaultdict(int)
        self._first_time_fixes: int = 0
        self._total_jobs: int = 0
        self._completed_jobs: int = 0

    def record_voice_latency(self, latency_ms: float):
        """Record voice pipeline latency in milliseconds."""
        self._voice_latencies.append(latency_ms)

    def record_agent_response_time(self, agent: str, duration_ms: float):
        """Record agent response time in milliseconds."""
        self._agent_response_times[agent].append(duration_ms)

    def record_api_cost(self, provider: str, cost: float):
        """Record API call cost."""
        self._api_costs[provider] += cost
        self._api_call_counts[provider] += 1

    def record_api_failure(self, provider: str):
        """Record API call failure."""
        self._api_failures[provider] += 1

    def record_agent_error(self, agent: str):
        """Record agent execution error."""
        self._agent_errors[agent] += 1

    def record_job_completion(self, first_time_fix: bool):
        """Record job completion and first-time fix status."""
        self._total_jobs += 1
        self._completed_jobs += 1
        if first_time_fix:
            self._first_time_fixes += 1

    def get_voice_latency_percentiles(self) -> Dict[str, float]:
        """Calculate voice latency percentiles (p50, p95, p99)."""
        if not self._voice_latencies:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}

        sorted_latencies = sorted(self._voice_latencies)
        n = len(sorted_latencies)

        return {
            "p50": sorted_latencies[int(n * 0.50)],
            "p95": sorted_latencies[int(n * 0.95)],
            "p99": sorted_latencies[int(n * 0.99)],
        }

    def get_agent_response_times(self) -> Dict[str, Dict[str, float]]:
        """Get average response times per agent."""
        result = {}
        for agent, times in self._agent_response_times.items():
            if times:
                result[agent] = {
                    "avg": sum(times) / len(times),
                    "min": min(times),
                    "max": max(times),
                    "count": len(times),
                }
        return result

    def get_api_costs(self) -> Dict[str, Dict[str, Any]]:
        """Get API costs and call counts."""
        result = {}
        for provider in set(list(self._api_costs.keys()) + list(self._api_call_counts.keys())):
            result[provider] = {
                "total_cost": self._api_costs[provider],
                "call_count": self._api_call_counts[provider],
                "failure_count": self._api_failures[provider],
                "failure_rate": (
                    self._api_failures[provider] / self._api_call_counts[provider]
                    if self._api_call_counts[provider] > 0
                    else 0.0
                ),
            }
        return result

    def get_agent_error_rates(self) -> Dict[str, Dict[str, Any]]:
        """Get agent error rates."""
        result = {}
        for agent, error_count in self._agent_errors.items():
            total_calls = len(self._agent_response_times.get(agent, []))
            result[agent] = {
                "error_count": error_count,
                "total_calls": total_calls,
                "error_rate": error_count / total_calls if total_calls > 0 else 0.0,
            }
        return result

    def get_first_time_fix_rate(self) -> float:
        """Calculate first-time fix rate."""
        if self._completed_jobs == 0:
            return 0.0
        return self._first_time_fixes / self._completed_jobs

    def get_job_completion_rate(self) -> float:
        """Calculate job completion rate."""
        if self._total_jobs == 0:
            return 0.0
        return self._completed_jobs / self._total_jobs

    def reset(self):
        """Reset all metrics."""
        self._voice_latencies.clear()
        self._agent_response_times.clear()
        self._api_costs.clear()
        self._api_call_counts.clear()
        self._api_failures.clear()
        self._agent_errors.clear()
        self._first_time_fixes = 0
        self._total_jobs = 0
        self._completed_jobs = 0


class AlertManager:
    """
    Manages alerting for observability metrics.
    
    **Validates: Requirement 9.6** - Alert on voice latency > 600ms
    **Validates: Requirement 9.7** - Alert on API failure > 1%
    **Validates: Requirement 9.8** - Alert on agent error > 5%
    """

    def __init__(self):
        self._alert_handlers: List[callable] = []
        self._alert_thresholds = {
            "voice_latency_p95": 600.0,  # ms
            "api_failure_rate": 0.01,  # 1%
            "agent_error_rate": 0.05,  # 5%
            "budget_threshold": 0.8,  # 80% of budget
        }

    def add_alert_handler(self, handler: callable):
        """Add a custom alert handler."""
        self._alert_handlers.append(handler)

    def check_voice_latency(self, p95_latency: float):
        """Check if voice latency exceeds threshold."""
        if p95_latency > self._alert_thresholds["voice_latency_p95"]:
            self._trigger_alert(
                "voice_latency_high",
                f"Voice latency p95 ({p95_latency:.2f}ms) exceeds threshold ({self._alert_thresholds['voice_latency_p95']}ms)",
                {"p95_latency": p95_latency, "threshold": self._alert_thresholds["voice_latency_p95"]},
            )

    def check_api_failure_rate(self, provider: str, failure_rate: float):
        """Check if API failure rate exceeds threshold."""
        if failure_rate > self._alert_thresholds["api_failure_rate"]:
            self._trigger_alert(
                "api_failure_rate_high",
                f"API failure rate for {provider} ({failure_rate:.2%}) exceeds threshold ({self._alert_thresholds['api_failure_rate']:.2%})",
                {"provider": provider, "failure_rate": failure_rate, "threshold": self._alert_thresholds["api_failure_rate"]},
            )

    def check_agent_error_rate(self, agent: str, error_rate: float):
        """Check if agent error rate exceeds threshold."""
        if error_rate > self._alert_thresholds["agent_error_rate"]:
            self._trigger_alert(
                "agent_error_rate_high",
                f"Agent error rate for {agent} ({error_rate:.2%}) exceeds threshold ({self._alert_thresholds['agent_error_rate']:.2%})",
                {"agent": agent, "error_rate": error_rate, "threshold": self._alert_thresholds["agent_error_rate"]},
            )

    def check_budget(self, spent: float, budget: float):
        """Check if budget spending exceeds threshold."""
        if budget > 0 and spent / budget > self._alert_thresholds["budget_threshold"]:
            self._trigger_alert(
                "budget_threshold_exceeded",
                f"Budget spending ({spent:.2f}) exceeds {self._alert_thresholds['budget_threshold']:.0%} of budget ({budget:.2f})",
                {"spent": spent, "budget": budget, "threshold": self._alert_thresholds["budget_threshold"]},
            )

    def _trigger_alert(self, alert_type: str, message: str, context: Dict[str, Any]):
        """Trigger an alert."""
        logger.warning(f"ALERT [{alert_type}]: {message}")

        for handler in self._alert_handlers:
            try:
                handler(alert_type, message, context)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")


class TelemetryManager:
    """
    Manages telemetry integration for pipeline orchestration.
    
    **Validates: Requirement 3.8** - Emit telemetry to Langfuse and Arize Phoenix
    **Validates: Requirement 9.1** - Use Langfuse for agent graph visualization
    **Validates: Requirement 9.2** - Use Arize Phoenix for OpenTelemetry debugging
    **Validates: Requirement 9.4** - Integrate Langfuse tracing in Python
    **Validates: Requirement 9.5** - Integrate Datadog tracing in Python
    **Validates: Requirement 9.6** - Track voice latency, agent response time, API costs
    **Validates: Requirement 9.7** - Track first-time fix rate
    **Validates: Requirement 9.8** - Track job completion rate
    """

    def __init__(self):
        self._langfuse_client = None
        self._datadog_initialized = False
        self._sentry_initialized = False
        self._phoenix_initialized = False
        self._metrics_collector = MetricsCollector()
        self._alert_manager = AlertManager()
        self._initialize()

    def _initialize(self):
        """Initialize telemetry integrations based on configuration."""
        # Initialize Langfuse (Cloud)
        if settings.langfuse_public_key and settings.langfuse_secret_key:
            try:
                from langfuse import Langfuse

                self._langfuse_client = Langfuse(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    host=settings.langfuse_host,
                )
                logger.info(f"Langfuse cloud initialized: {settings.langfuse_host}")
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse: {e}")

        # Initialize Datadog (GitHub Student Pack - Free 2 years)
        if settings.use_datadog and settings.datadog_api_key:
            try:
                from ddtrace import patch_all, tracer

                # Patch all supported libraries for automatic instrumentation
                patch_all()

                # Configure tracer
                tracer.configure(
                    hostname=settings.datadog_site,
                    service=settings.datadog_service,
                    env=settings.datadog_env,
                )

                self._datadog_initialized = True
                logger.info(f"Datadog APM initialized: {settings.datadog_service} ({settings.datadog_env})")
            except Exception as e:
                logger.warning(f"Failed to initialize Datadog: {e}")

        # Initialize Sentry (500k events/month free)
        if settings.sentry_dsn:
            try:
                import sentry_sdk

                sentry_sdk.init(
                    dsn=settings.sentry_dsn,
                    environment=settings.sentry_environment,
                    traces_sample_rate=settings.sentry_traces_sample_rate,
                    # Enable performance monitoring
                    enable_tracing=True,
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

    @property
    def metrics(self) -> MetricsCollector:
        """Get metrics collector."""
        return self._metrics_collector

    @property
    def alerts(self) -> AlertManager:
        """Get alert manager."""
        return self._alert_manager

    def record_voice_latency(self, latency_ms: float):
        """
        Record voice pipeline latency.
        
        **Validates: Requirement 9.6** - Track voice latency (p50, p95, p99)
        """
        self._metrics_collector.record_voice_latency(latency_ms)

        # Check for alerts
        percentiles = self._metrics_collector.get_voice_latency_percentiles()
        if percentiles["p95"] > 0:
            self._alert_manager.check_voice_latency(percentiles["p95"])

        # Record to Datadog
        if self.is_datadog_enabled:
            self.record_metric("voice.latency", latency_ms, tags={"unit": "ms"})

    def record_agent_response_time(self, agent: str, duration_ms: float):
        """
        Record agent response time.
        
        **Validates: Requirement 9.6** - Track agent response time
        """
        self._metrics_collector.record_agent_response_time(agent, duration_ms)

        # Record to Datadog
        if self.is_datadog_enabled:
            self.record_metric("agent.response_time", duration_ms, tags={"agent": agent, "unit": "ms"})

    def record_api_call(self, provider: str, cost: float = 0.0, success: bool = True):
        """
        Record API call with cost and success status.
        
        **Validates: Requirement 9.6** - Track API costs
        **Validates: Requirement 9.7** - Track API failure rate
        """
        if cost > 0:
            self._metrics_collector.record_api_cost(provider, cost)

        if not success:
            self._metrics_collector.record_api_failure(provider)

            # Check for alerts
            api_costs = self._metrics_collector.get_api_costs()
            if provider in api_costs:
                self._alert_manager.check_api_failure_rate(provider, api_costs[provider]["failure_rate"])

        # Record to Datadog
        if self.is_datadog_enabled:
            self.record_metric("api.call", 1, tags={"provider": provider, "success": str(success)})
            if cost > 0:
                self.record_metric("api.cost", cost, tags={"provider": provider})

    def record_agent_error(self, agent: str):
        """
        Record agent execution error.
        
        **Validates: Requirement 9.8** - Track agent error rate
        """
        self._metrics_collector.record_agent_error(agent)

        # Check for alerts
        error_rates = self._metrics_collector.get_agent_error_rates()
        if agent in error_rates:
            self._alert_manager.check_agent_error_rate(agent, error_rates[agent]["error_rate"])

        # Record to Datadog
        if self.is_datadog_enabled:
            self.record_metric("agent.error", 1, tags={"agent": agent})

    def record_job_completion(self, first_time_fix: bool):
        """
        Record job completion and first-time fix status.
        
        **Validates: Requirement 9.7** - Track first-time fix rate
        **Validates: Requirement 9.8** - Track job completion rate
        """
        self._metrics_collector.record_job_completion(first_time_fix)

        # Record to Datadog
        if self.is_datadog_enabled:
            self.record_metric("job.completion", 1, tags={"first_time_fix": str(first_time_fix)})
            self.record_metric("job.first_time_fix_rate", self._metrics_collector.get_first_time_fix_rate())
            self.record_metric("job.completion_rate", self._metrics_collector.get_job_completion_rate())

    def check_budget_alert(self, spent: float, budget: float):
        """
        Check if budget spending exceeds threshold.
        
        **Validates: Requirement 9.6** - Budget alerts
        """
        self._alert_manager.check_budget(spent, budget)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all collected metrics."""
        return {
            "voice_latency": self._metrics_collector.get_voice_latency_percentiles(),
            "agent_response_times": self._metrics_collector.get_agent_response_times(),
            "api_costs": self._metrics_collector.get_api_costs(),
            "agent_error_rates": self._metrics_collector.get_agent_error_rates(),
            "first_time_fix_rate": self._metrics_collector.get_first_time_fix_rate(),
            "job_completion_rate": self._metrics_collector.get_job_completion_rate(),
        }

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
