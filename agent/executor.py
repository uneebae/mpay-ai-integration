"""Execute validated SQL statements safely inside a transaction."""

from __future__ import annotations

import logging

from agent.database import cursor

log = logging.getLogger(__name__)


def execute(statements: list[str]) -> int:
    """Execute a list of pre-validated INSERT statements.

    Returns the number of rows inserted.
    """
    total = 0
    with cursor(commit=True) as cur:
        for stmt in statements:
            log.debug("Executing: %s", stmt[:200])
            cur.execute(stmt)
            total += cur.rowcount
    log.info("Inserted %d row(s) across %d statement(s)", total, len(statements))
    return total
