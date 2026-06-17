from contextlib import contextmanager
from collections.abc import Iterator

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.resources import Resource

from datapizza.agents import AgentHooks, StepContext, StepResult


def setup_tracing(
    service_name: str = "finassist",
    service_version: str = "0.1.0",
    enable_console: bool = True,
    enable_otlp: bool = True,
) -> trace.Tracer:
    resource = Resource.create({
        "service.name": service_name,
        "service.version": service_version,
    })
    provider = TracerProvider(resource=resource)

    if enable_console:
        provider.add_span_processor(
            SimpleSpanProcessor(ConsoleSpanExporter())
        )

    if enable_otlp:
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter())
        )

    trace.set_tracer_provider(provider)
    return provider.get_tracer(__name__)


_tracer: trace.Tracer | None = None


def get_tracer() -> trace.Tracer:
    global _tracer
    if _tracer is None:
        _tracer = setup_tracing()
    return _tracer


class TracingHooks(AgentHooks):
    def __init__(self, tracer: trace.Tracer | None = None) -> None:
        self._tracer = tracer or get_tracer()

    def before_step(self, context: StepContext) -> None:
        span_name = f"agent.step.{context.step_index}"
        self._span = self._tracer.start_as_current_span(span_name)
        self._span.__enter__()
        self._span.set_attribute("type", "agent.step")
        self._span.set_attribute("step", context.step_index)
        self._span.set_attribute("task_input", context.task_input)

    def after_step(self, context: StepContext, result: StepResult) -> None:
        if hasattr(self, "_span") and self._span:
            self._span.set_attribute("tools_used", [b.name for b in result.tools_used])
            self._span.__exit__(None, None, None)


@contextmanager
def agent_run_span(
    tracer: trace.Tracer,
    user_id: str,
    query: str,
) -> Iterator[trace.Span]:
    with tracer.start_as_current_span("agent.run") as span:
        span.set_attribute("type", "agent.run")
        span.set_attribute("user_id", user_id)
        span.set_attribute("query", query)
        yield span
