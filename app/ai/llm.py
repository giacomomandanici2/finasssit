import asyncio
import json
import logging
import time
from functools import lru_cache
from typing import TypeVar

from openai import AsyncAzureOpenAI
from openai import (
    APIStatusError,
    APITimeoutError,
    APIConnectionError,
)
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
    before_sleep_log,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

B = TypeVar("B", bound=BaseModel)


class CircuitBreakerOpenError(Exception): ...


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, (APITimeoutError, APIConnectionError)):
        return True
    if isinstance(exc, APIStatusError) and exc.status_code >= 429:
        return True
    return False


def _inline_defs(schema: dict) -> dict:
    definitions = schema.pop("$defs", {})
    if not definitions:
        return schema
    schema_str = json.dumps(schema)
    for name, ref_schema in definitions.items():
        old = f'{{"$ref": "#/$defs/{name}"}}'
        new = json.dumps(ref_schema)
        schema_str = schema_str.replace(old, new)
    return json.loads(schema_str)


# Implementa il pattern circuit breaker per evitare chiamate inutili a un servizio che sta fallendo:
class AsyncCircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._open = False
        self._lock = asyncio.Lock()

    async def call(self, coro_factory):
        async with self._lock:
            if self._open:
                if time.monotonic() - self._last_failure_time >= self._recovery_timeout:
                    self._open = False
                else:
                    raise CircuitBreakerOpenError("LLM circuit breaker is open")

        try:
            result = await coro_factory()
        except asyncio.CancelledError:
            raise
        except Exception:
            async with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.monotonic()
                if self._failure_count >= self._failure_threshold:
                    self._open = True
            raise
        else:
            async with self._lock:
                self._failure_count = 0
            return result


class LLMClient:
    def __init__(self):
        self._client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_key,
            api_version=settings.azure_openai_api_version,
            timeout=30.0,
        )
        self._deployment = settings.azure_openai_deployment
        self._circuit_breaker = AsyncCircuitBreaker()

    # chat è il metodo che usi per parlare con il modello Azure OpenAI.
    # Concretamente: gli passi una lista di messaggi (tipo [{"role": "user", "content": "Classifica questa transazione"}]) e uno schema Pydantic (es. TransazioneScored), e lui:
    # 1. Chiama Azure OpenAI con quei messaggi
    # 2. Gli dice di rispondere in JSON rispettando lo schema che gli hai dato
    # 3. Prende la risposta JSON, la valida e la trasforma nell'oggetto Pydantic che hai specificato
    # Quindi invece di ricevere un testo libero e doverlo parsare a mano, ottieni direttamente un oggetto tipizzato pronto all'uso. È un wrapper che nasconde tutta la complessità (chiamata HTTP, retry, timeout, validazione JSON, circuit breaker).

    async def chat(self, messages: list[dict], schema: type[B]) -> B:
        return await self._circuit_breaker.call(
            lambda: self._chat_with_retry(messages, schema),
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10, jitter=2),
        retry=retry_if_exception(_is_retryable),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _chat_with_retry(self, messages: list[dict], schema: type[B]) -> B:
        raw = schema.model_json_schema()
        raw["additionalProperties"] = False
        json_schema = _inline_defs(raw)

        response = await self._client.chat.completions.create(
            model=self._deployment,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": json_schema,
                    "strict": True,
                },
            },
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("LLM returned empty response")
        return schema.model_validate_json(content)

#qui sto creando l'istanza della llm che poi tramite Dep inj viene injettata dove serve
@lru_cache
def get_llm() -> LLMClient:
    return LLMClient()
