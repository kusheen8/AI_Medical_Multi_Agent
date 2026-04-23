"""
Distributed Tracing configuration for Phase 5.
Sets up OpenTelemetry with OTLP exporter for Jaeger/Zipkin.
"""

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import get_settings


def setup_tracing(app: FastAPI) -> None:
    """Initialize OpenTelemetry tracing for the application.

    Sets up the tracer provider, configures the OTLP exporter,
    and instruments FastAPI, PyMongo, and HTTPX.
    """
    settings = get_settings()

    # Create resource identifying the service
    resource = Resource(attributes={
        SERVICE_NAME: "ai-medical-multi-agent"
    })

    # Set up Tracer Provider
    provider = TracerProvider(resource=resource)
    
    # Configure OTLP Exporter (can be configured via OTEL_EXPORTER_OTLP_ENDPOINT env var)
    otlp_exporter = OTLPSpanExporter()
    processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(processor)

    # Register the tracer provider globally
    trace.set_tracer_provider(provider)

    # Instrument third-party libraries globally
    PymongoInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()

    # Instrument FastAPI application
    FastAPIInstrumentor.instrument_app(app)
