"""Call the LLM to generate Mpay integration SQL with retry logic."""

from __future__ import annotations

import functools
import logging
import re
import time
from typing import Any, Callable, TypeVar

from groq import Groq
from groq._exceptions import RateLimitError

from agent.config import llm_cfg
from agent.prompts import build_generation_prompt
from agent.schema import get_next_config_id, get_next_tran_id, schema_as_prompt

log = logging.getLogger(__name__)

_client: Groq | None = None
_last_request_time: float = 0.0


def _get_client() -> Groq:
    """Get or create the Groq API client."""
    global _client
    if _client is None:
        _client = Groq(api_key=llm_cfg.api_key)
    return _client


def _rate_limit_wait(min_interval: float = 0.5) -> None:
    """Enforce minimum time between API requests to avoid rate limits."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < min_interval:
        wait_time = min_interval - elapsed
        log.debug("Rate limiting: waiting %.2fs before next request", wait_time)
        time.sleep(wait_time)
    _last_request_time = time.time()


T = TypeVar("T")


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for exponential backoff retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay in seconds.
        backoff_factor: Multiplier for each retry.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = base_delay
            last_error: Exception | None = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as e:
                    last_error = e
                    if attempt == max_retries:
                        raise
                    log.warning(
                        "Rate limited (attempt %d/%d). Waiting %.1fs before retry…",
                        attempt, max_retries, delay,
                    )
                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
                except Exception as e:
                    last_error = e
                    if attempt == max_retries:
                        raise
                    log.warning(
                        "Request failed (attempt %d/%d): %s. Retrying after %.1fs…",
                        attempt, max_retries, str(e), delay,
                    )
                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
            
            # Should not reach here, but just in case
            if last_error:
                raise last_error
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def _clean_response(text: str) -> str:
    """Strip markdown fences and stray commentary the LLM sometimes adds."""
    # Remove ```sql ... ``` or ``` ... ```
    text = re.sub(r"```(?:sql)?\s*", "", text)
    text = re.sub(r"```", "", text)
    # Remove lines that are pure comments (-- ...) at the top/bottom
    lines = text.strip().splitlines()
    cleaned = [l for l in lines if not l.strip().startswith("--")]
    return "\n".join(cleaned).strip()


@retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
def _call_groq(messages: list[dict]) -> str:
    """Call Groq API with retries on rate limiting or transient errors."""
    _rate_limit_wait()
    
    response = _get_client().chat.completions.create(
        model=llm_cfg.model,
        messages=messages,
        temperature=llm_cfg.temperature,
    )
    
    raw = response.choices[0].message.content or ""
    return raw


def generate_sql(api_description: str) -> str:
    """Send the API description to the LLM and return cleaned SQL.
    
    Includes retry logic and rate-limit handling.
    """
    schema_text = schema_as_prompt()
    next_tid = get_next_tran_id()
    next_cid = get_next_config_id()
    log.info("DB state: next tran_id=%d, next config_id=%d", next_tid, next_cid)
    messages = build_generation_prompt(
        schema_text, api_description,
        next_tran_id=next_tid, next_config_id=next_cid,
    )

    log.info("Sending prompt to %s …", llm_cfg.model)
    
    try:
        raw = _call_groq(messages)
    except RateLimitError as e:
        raise RuntimeError(
            f"Rate limited by Groq API after retries: {e}. "
            "Please wait a moment and try again."
        ) from e
    except Exception as e:
        raise RuntimeError(f"Failed to generate SQL: {e}") from e

    log.debug("Raw LLM response:\n%s", raw)

    sql = _clean_response(raw)
    if not sql:
        raise RuntimeError("LLM returned an empty response.")
    
    log.info("✓ Generated %d bytes of SQL", len(sql))
    return sql

