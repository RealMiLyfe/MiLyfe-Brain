"""
OpenTelemetry instrumentation for MiLyfe Brain.

Provides distributed tracing, metrics, and log correlation.
Exports to OTLP collector (Jaeger, Tempo, or cloud providers).

Configuration via environment variables:
    OTEL_ENABLED=true
    OTEL_SERVICE_NAME=milyfe-brain-backend
    OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
    OTEL_EXPORTER_OTLP_PROTOCOL=grpc
    OTEL_TRACES_SAMPLER=parentbased_traceidratio
    OTEL_TRACES_SAMPLER_ARG=1.0
"""

import os
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Optional

# Check if OpenTelemetry is available and enabled
OTEL_ENABLED = os.getenv("OTEL_ENABLED", "false").lower() == "true"

if OTEL_ENABLED:
    try:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.metrics import Counter, Histogram, UpDownCounter
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.semconv.resource import ResourceAttributes
        from opentelemetry.trace import StatusCode

        OTEL_AVAILABLE = True
    except ImportError:
        OTEL_AVAILABLE = False
        OTEL_ENABLED = False
else:
    OTEL_AVAILABLE = False


class TelemetryService:
    """Manages OpenTelemetry instrumentation for the application."""

    def __init__(self):
        self._tracer: Optional[Any] = None
        self._meter: Optional[Any] = None
        self._initialized = False

        # Metrics
        self._request_counter: Optional[Any] = None
        self._request_duration: Optional[Any] = None
        self._active_agents: Optional[Any] = None
        self._llm_calls: Optional[Any] = None
        self._llm_duration: Optional[Any] = None
        self._tool_executions: Optional[Any] = None
        self._playbook_counter: Optional[Any] = None
        self._error_counter: Optional[Any] = None
        self._token_counter: Optional[Any] = None

    def initialize(self, app=None):
        """Initialize OpenTelemetry with configured exporters."""
        if not OTEL_ENABLED or not OTEL_AVAILABLE:
            return

        service_name = os.getenv("OTEL_SERVICE_NAME", "milyfe-brain-backend")
        service_version = os.getenv("OTEL_SERVICE_VERSION", "2.0.0")
        environment = os.getenv("OTEL_ENVIRONMENT", "development")

        # Resource identifies this service
        resource = Resource.create({
            ResourceAttributes.SERVICE_NAME: service_name,
            ResourceAttributes.SERVICE_VERSION: service_version,
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: environment,
            "service.namespace": "milyfe",
        })

        # ─── Tracing ──────────────────────────────────────────────────
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

        tracer_provider = TracerProvider(resource=resource)
        span_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(tracer_provider)
        self._tracer = trace.get_tracer(service_name, service_version)

        # ─── Metrics ──────────────────────────────────────────────────
        metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
        metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=30000)
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)
        self._meter = metrics.get_meter(service_name, service_version)

        # Define metrics
        self._request_counter = self._meter.create_counter(
            "http.server.request.count",
            description="Total HTTP requests",
            unit="requests",
        )
        self._request_duration = self._meter.create_histogram(
            "http.server.request.duration",
            description="HTTP request duration",
            unit="ms",
        )
        self._active_agents = self._meter.create_up_down_counter(
            "milyfe.agents.active",
            description="Currently active agents",
            unit="agents",
        )
        self._llm_calls = self._meter.create_counter(
            "milyfe.llm.calls",
            description="Total LLM API calls",
            unit="calls",
        )
        self._llm_duration = self._meter.create_histogram(
            "milyfe.llm.duration",
            description="LLM call duration",
            unit="ms",
        )
        self._tool_executions = self._meter.create_counter(
            "milyfe.tools.executions",
            description="Tool execution count",
            unit="executions",
        )
        self._playbook_counter = self._meter.create_counter(
            "milyfe.playbooks.total",
            description="Total playbooks created",
            unit="playbooks",
        )
        self._error_counter = self._meter.create_counter(
            "milyfe.errors",
            description="Error count by type",
            unit="errors",
        )
        self._token_counter = self._meter.create_counter(
            "milyfe.tokens.total",
            description="Total tokens used",
            unit="tokens",
        )

        # ─── Auto-instrumentation ────────────────────────────────────
        if app:
            FastAPIInstrumentor.instrument_app(app)

        # Instrument httpx (for Ollama and ChromaDB calls)
        HTTPXClientInstrumentor().instrument()

        self._initialized = True

    @property
    def tracer(self):
        """Get the tracer instance."""
        return self._tracer

    @contextmanager
    def span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Create a traced span context manager."""
        if not self._initialized or not self._tracer:
            yield None
            return

        with self._tracer.start_as_current_span(name, attributes=attributes or {}) as span:
            try:
                yield span
            except Exception as e:
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise

    def trace_function(self, name: Optional[str] = None):
        """Decorator to trace a function."""
        def decorator(func: Callable):
            span_name = name or f"{func.__module__}.{func.__qualname__}"

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self._initialized:
                    return await func(*args, **kwargs)
                with self.span(span_name):
                    return await func(*args, **kwargs)

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self._initialized:
                    return func(*args, **kwargs)
                with self.span(span_name):
                    return func(*args, **kwargs)

            if _is_async(func):
                return async_wrapper
            return sync_wrapper
        return decorator

    # ─── Metric Recording ─────────────────────────────────────────────

    def record_request(self, method: str, path: str, status_code: int, duration_ms: float):
        """Record an HTTP request metric."""
        if not self._initialized:
            return
        attrs = {"http.method": method, "http.route": path, "http.status_code": status_code}
        self._request_counter.add(1, attrs)
        self._request_duration.record(duration_ms, attrs)

    def record_agent_spawn(self, role: str):
        """Record agent spawn."""
        if not self._initialized:
            return
        self._active_agents.add(1, {"agent.role": role})

    def record_agent_retire(self, role: str):
        """Record agent retirement."""
        if not self._initialized:
            return
        self._active_agents.add(-1, {"agent.role": role})

    def record_llm_call(self, model: str, duration_ms: float, tokens: int = 0):
        """Record an LLM API call."""
        if not self._initialized:
            return
        attrs = {"llm.model": model}
        self._llm_calls.add(1, attrs)
        self._llm_duration.record(duration_ms, attrs)
        if tokens > 0:
            self._token_counter.add(tokens, attrs)

    def record_tool_execution(self, tool_name: str, success: bool):
        """Record a tool execution."""
        if not self._initialized:
            return
        self._tool_executions.add(1, {"tool.name": tool_name, "tool.success": success})

    def record_playbook_created(self, status: str = "created"):
        """Record playbook creation."""
        if not self._initialized:
            return
        self._playbook_counter.add(1, {"playbook.status": status})

    def record_error(self, error_type: str, component: str):
        """Record an error."""
        if not self._initialized:
            return
        self._error_counter.add(1, {"error.type": error_type, "error.component": component})


def _is_async(func):
    """Check if function is async."""
    import asyncio
    return asyncio.iscoroutinefunction(func)


# Singleton instance
telemetry = TelemetryService()
