from contextlib import contextmanager
from collections.abc import Iterator

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.sdk.resources import Resource

from datapizza.agents import AgentHooks, StepContext, StepResult


_tracer: trace.Tracer | None = None


def get_tracer() -> trace.Tracer:
    global _tracer
    if _tracer is not None:
        return _tracer
    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        _tracer = provider.get_tracer(__name__)
    else:
        resource = Resource.create({
            "service.name": "finassist",
            "service.version": "0.1.0",
        })
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
        _tracer = provider.get_tracer(__name__)
    return _tracer


class TracingHooks(AgentHooks):
    """Hooks with nested span support + rate limit per-step.

    Span hierarchy (observability convention):
        agent.run.triage
        └─ agent.step.<agent_name>.N
            ├─ tool.<specialist_name>       (can_call → specialist invocation)
            │   └─ agent.run.<specialist_name>
            │       └─ agent.step.<specialist_name>.M
            │           └─ tool.<tool_name>  (actual tool execution)
            └─ ... (other tool calls)

    Ogni step di OGNI agente decrementa il RateLimitTracker condiviso.
    """

    def __init__(
        self,
        tracer: trace.Tracer | None = None,
        rate_limit_tracker=None,
        agent_name: str = "unknown",
    ) -> None:
        self._tracer = tracer or get_tracer()
        self._span: trace.Span | None = None
        self._rate_limit = rate_limit_tracker
        self._agent_name = agent_name

    def before_step(self, context: StepContext) -> None:
        if self._rate_limit is not None:
            self._rate_limit.consume()

        span_name = f"agent.step.{self._agent_name}.{context.step_index}"
        self._span = self._tracer.start_as_current_span(span_name)
        self._span.__enter__()
        self._span.set_attribute("type", "agent.step")
        self._span.set_attribute("agent", self._agent_name)
        self._span.set_attribute("step", context.step_index)
        self._span.set_attribute("task_input", context.task_input)

    def after_step(self, context: StepContext, result: StepResult) -> None:
        if self._span is not None:
            self._span.set_attribute("tools_used", [b.name for b in result.tools_used])
            self._span.__exit__(None, None, None)
            self._span = None


@contextmanager
def agent_run_span(
    tracer: trace.Tracer,
    agent_name: str,
    user_id: str | None = None,
    query: str | None = None,
) -> Iterator[trace.Span]:
    span_name = f"agent.run.{agent_name}"
    with tracer.start_as_current_span(span_name) as span:
        span.set_attribute("type", "agent.run")
        span.set_attribute("agent", agent_name)
        if user_id:
            span.set_attribute("user_id", user_id)
        if query:
            span.set_attribute("query", query)
        yield span


@contextmanager
def tool_call_span(
    tracer: trace.Tracer,
    tool_name: str,
    agent_name: str | None = None,
) -> Iterator[trace.Span]:
    span_name = f"tool.{tool_name}"
    with tracer.start_as_current_span(span_name) as span:
        span.set_attribute("type", "tool")
        span.set_attribute("tool", tool_name)
        if agent_name:
            span.set_attribute("agent", agent_name)
        yield span


@contextmanager
def error_propagation_span(
    tracer: trace.Tracer,
    agent_name: str,
    error: str,
) -> Iterator[trace.Span]:
    with tracer.start_as_current_span(f"error.{agent_name}") as span:
        span.set_attribute("type", "error")
        span.set_attribute("agent", agent_name)
        span.set_attribute("error.message", error)
        span.set_status(trace.Status(trace.StatusCode.ERROR, error))
        yield span
