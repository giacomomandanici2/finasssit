import asyncio
from functools import wraps
from typing import Callable, ParamSpec, TypeVar


P = ParamSpec("P") # ParamSpec è un tipo speciale che rappresenta i parametri di una funzione, permettendo di mantenere la firma originale della funzione decorata.
R = TypeVar("R") # TypeVar è un tipo generico che rappresenta il tipo di ritorno di una funzione, permettendo di mantenere il tipo di ritorno originale della funzione decorata.

def retry_async(max_attempts: int = 3, backoff: float = 1.0):
    def decorator(func: Callable[P, R]):
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            attempt = 0
            delay = backoff

            while True:
                try:
                    return await func(*args, **kwargs)

                except asyncio.CancelledError:
                    raise  # non deve essere gestito

                except Exception:
                    attempt += 1

                    if attempt >= max_attempts:
                        raise

                    await asyncio.sleep(delay)
                    delay *= 2  # exponential backoff

        return wrapper
    return decorator
