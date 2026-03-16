"""Prompt templates — single source of truth for every LLM interaction."""

from __future__ import annotations

SYSTEM_PROMPT = """\
You are an expert SQL engineer for the Mpay payment platform.

Your ONLY job is to produce INSERT statements that configure a new external API
integration inside Mpay's database.

Rules you MUST follow:
1. Output **only** valid SQL — no markdown fences, no commentary, no explanation.
2. Use **only** INSERT statements.
3. Follow the schema exactly — never invent columns or tables.
4. `id` columns are AUTO_INCREMENT — omit them from INSERT statements.
5. Use the exact `tran_id` value provided below as "Next tran_id". Do NOT
   use any other value.
6. Use the exact `config_id` value provided below as "Next config_id" when
   inserting into `ws_endpoint_config`.
7. **Only include columns you have a real value for.** Omit any column whose
   value would be NULL — MySQL will default it. This keeps statements short
   and avoids column-count mistakes.
8. Use one INSERT per row — do NOT use multi-row VALUES syntax.
9. Wrap string values in single quotes; use NULL (not the string 'NULL') only
   when you must explicitly set a column to NULL.
10. End every statement with a semicolon.
11. If the API description is ambiguous, make reasonable defaults that a
    payment integration engineer would choose.
"""

GENERATE_SQL_USER = """\
Database schema (auto-discovered from live DB):

{schema}

---

Current database state:
- Next tran_id to use: {next_tran_id}
- Next config_id to use (for ws_endpoint_config.config_id): {next_config_id}

---

Integrate the following external API into Mpay by generating the required
INSERT statements across all relevant tables:

{api_description}
"""


def build_generation_prompt(
    schema_text: str,
    api_description: str,
    *,
    next_tran_id: int = 100,
    next_config_id: int = 1,
) -> list[dict]:
    """Return the messages list ready for the chat completions API."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": GENERATE_SQL_USER.format(
                schema=schema_text,
                api_description=api_description.strip(),
                next_tran_id=next_tran_id,
                next_config_id=next_config_id,
            ),
        },
    ]
