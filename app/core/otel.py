import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor

from app.core.config import settings

logger = logging.getLogger(__name__)


def setup_otel(app, service_name: str = "finassist") -> None:
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "0.1.0",
    })

    provider = TracerProvider(resource=resource)

    otlp_endpoint = settings.otel_exporter_otlp_endpoint
    if otlp_endpoint:
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
        )
        logger.info("[otel] OTLP exporter configured: %s", otlp_endpoint)
    else:
        provider.add_span_processor(
            SimpleSpanProcessor(ConsoleSpanExporter())
        )
        logger.info("[otel] No OTLP endpoint — using console exporter")

    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()

    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from app.core.db import engine
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
        logger.info("[otel] SQLAlchemy auto-instrumentation enabled")
    except Exception as exc:
        logger.warning("[otel] SQLAlchemy instrumentation skipped: %s", exc)

    logger.info("[otel] FastAPI + httpx auto-instrumentation enabled")
