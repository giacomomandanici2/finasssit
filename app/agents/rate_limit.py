"""Rate limit centralizzato: contatore per-utente decrementato
ad ogni step di ogni agente (triage + specialisti)."""

import logging

from datapizza.agents import AgentHooks, StepContext, StepResult

logger = logging.getLogger(__name__)

_MAX_STEPS_GLOBAL = 20


class RateLimitExceeded(Exception):
    """Sollevato quando il budget globale di step è esaurito."""


class RateLimitTracker:
    """Tracker condiviso tra tutti gli agenti di una richiesta."""

    def __init__(self, max_steps: int = _MAX_STEPS_GLOBAL):
        self._remaining = max_steps
        self._max_steps = max_steps

    @property
    def remaining(self) -> int:
        return self._remaining

    @property
    def max_steps(self) -> int:
        return self._max_steps

    def consume(self) -> None:
        if self._remaining <= 0:
            raise RateLimitExceeded(
                f"Rate limit superato: {self._max_steps} step globali esauriti."
            )
        self._remaining -= 1


class RateLimitHooks(AgentHooks):
    """Hooks che decrementano il contatore globale prima di ogni step."""

    def __init__(self, tracker: RateLimitTracker, inner: AgentHooks | None = None):
        self._tracker = tracker
        self._inner = inner

    def before_step(self, context: StepContext) -> None:
        self._tracker.consume()
        if self._inner is not None:
            self._inner.before_step(context)

    def after_step(self, context: StepContext, result: StepResult) -> None:
        if self._inner is not None:
            self._inner.after_step(context, result)
