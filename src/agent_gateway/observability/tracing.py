"""OpenTelemetry tracing setup."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

from agent_gateway.config.settings import Settings

_TRACING_CONFIGURED = False


def configure_tracing(settings: Settings) -> trace.Tracer:
    """Initialize a tracer provider and return the gateway tracer."""
    global _TRACING_CONFIGURED
    resource = Resource.create(
        {
            "service.name": settings.app_name,
            "deployment.environment": settings.app_env,
        }
    )
    provider = TracerProvider(resource=resource)
    if settings.is_demo or settings.app_debug:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    _TRACING_CONFIGURED = True
    return trace.get_tracer("agent_gateway")


def get_tracer(name: str = "agent_gateway") -> trace.Tracer:
    """Return a tracer, configuring a no-op-safe default if needed."""
    if not _TRACING_CONFIGURED:
        trace.set_tracer_provider(TracerProvider())
    return trace.get_tracer(name)
