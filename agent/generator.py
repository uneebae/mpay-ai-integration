"""Call the LLM to generate Mpay integration SQL."""

from __future__ import annotations

import logging
import re

from groq import Groq

from agent.config import llm_cfg
from agent.prompts import build_generation_prompt
from agent.schema import get_next_config_id, get_next_tran_id, schema_as_prompt

log = logging.getLogger(__name__)

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=llm_cfg.api_key)
    return _client


def _clean_response(text: str) -> str:
    """Strip markdown fences and stray commentary the LLM sometimes adds."""
    # Remove ```sql ... ``` or ``` ... ```
    text = re.sub(r"```(?:sql)?\s*", "", text)
    text = re.sub(r"```", "", text)
    # Remove lines that are pure comments (-- ...) at the top/bottom
    lines = text.strip().splitlines()
    cleaned = [l for l in lines if not l.strip().startswith("--")]
    return "\n".join(cleaned).strip()


def generate_sql(api_description: str) -> str:
    """Send the API description to the LLM and return cleaned SQL."""
    schema_text = schema_as_prompt()
    next_tid = get_next_tran_id()
    next_cid = get_next_config_id()
    log.info("DB state: next tran_id=%d, next config_id=%d", next_tid, next_cid)
    messages = build_generation_prompt(
        schema_text, api_description,
        next_tran_id=next_tid, next_config_id=next_cid,
    )

    log.info("Sending prompt to %s …", llm_cfg.model)
    response = _get_client().chat.completions.create(
        model=llm_cfg.model,
        messages=messages,
        temperature=llm_cfg.temperature,
    )

    raw = response.choices[0].message.content or ""
    log.debug("Raw LLM response:\n%s", raw)

    sql = _clean_response(raw)
    if not sql:
        raise RuntimeError("LLM returned an empty response.")
    return sql
