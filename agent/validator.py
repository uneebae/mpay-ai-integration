"""Validate generated SQL before it touches the database."""

from __future__ import annotations

import logging
import re

from agent.schema import MANAGED_TABLES

log = logging.getLogger(__name__)

# Keywords that must never appear *outside* of string literals.
_DANGEROUS_KW = re.compile(
    r"\b(drop|truncate|delete|update|alter|create|grant|revoke)\b",
    re.IGNORECASE,
)


class ValidationError(Exception):
    """Raised when generated SQL fails safety checks."""


def _split_statements(sql: str) -> list[str]:
    """Split SQL text into individual statements, expanding multi-row VALUES.

    If an INSERT uses ``VALUES (…), (…), (…)`` syntax, it is expanded into
    one INSERT per row so each can be validated independently.
    """
    raw = [s.strip() for s in sql.split(";") if s.strip()]

    expanded: list[str] = []
    for stmt in raw:
        normalised = " ".join(stmt.split())
        # Detect multi-row: INSERT INTO table (cols) VALUES (...), (...), ...
        m = re.match(
            r"(INSERT\s+INTO\s+`?\w+`?\s*\([^)]+\)\s*VALUES\s*)"
            r"\((.+)\)\s*$",
            normalised,
            re.IGNORECASE | re.DOTALL,
        )
        if not m:
            expanded.append(stmt)
            continue

        prefix = m.group(1)        # "INSERT INTO tbl (cols) VALUES "
        body = m.group(2)           # everything between outer ( and )

        # Split tuples on "), (" — the boundary between value rows.
        # We use a regex that handles optional whitespace.
        tuples = re.split(r"\)\s*,\s*\(", body)

        if len(tuples) <= 1:
            # Not actually multi-row
            expanded.append(stmt)
        else:
            for t in tuples:
                expanded.append(f"{prefix}({t})")

    return expanded


def _strip_string_literals(sql: str) -> str:
    """Replace all single-quoted string values with a placeholder.

    This prevents false-positive keyword detection inside data values
    like ``VALUES ('update_url', ...)``.
    """
    return re.sub(r"'[^']*'", "'__STR__'", sql)


def _count_values(vals_str: str) -> int:
    """Count comma-separated values in a VALUES clause, respecting quotes."""
    count = 1
    depth = 0
    in_q = False
    for ch in vals_str:
        if ch == "'" and not in_q:
            in_q = True
        elif ch == "'" and in_q:
            in_q = False
        elif ch == "(" and not in_q:
            depth += 1
        elif ch == ")" and not in_q:
            depth -= 1
        elif ch == "," and not in_q and depth == 0:
            count += 1
    return count


def _repair_null_padding(stmt: str, num_cols: int, num_vals: int) -> str | None:
    """If values < columns, pad the VALUES clause with trailing NULLs.

    Returns the repaired statement, or None if the gap is too large (> 3)
    to be a simple counting mistake.
    """
    gap = num_cols - num_vals
    if gap < 1 or gap > 3:
        return None  # too large a gap — not a simple NULL-counting error
    # Insert NULLs before the closing paren of the VALUES clause
    padding = ", NULL" * gap
    # Find the last ')' in the statement
    idx = stmt.rfind(")")
    if idx == -1:
        return None
    return stmt[:idx] + padding + stmt[idx:]


def validate(sql: str) -> list[str]:
    """Return a list of validated INSERT statements.

    Raises ``ValidationError`` on the first problem found.
    """
    statements = _split_statements(sql)

    if not statements:
        raise ValidationError("No SQL statements found in generated output.")

    validated: list[str] = []

    for i, stmt in enumerate(statements, 1):
        normalised = " ".join(stmt.split())

        # ── Only INSERTs allowed ──────────────────────────────────────
        if not normalised.lower().startswith("insert"):
            raise ValidationError(
                f"Statement #{i} is not an INSERT:\n  {stmt[:120]}…"
            )

        # ── Must target a managed table ───────────────────────────────
        match = re.match(
            r"INSERT\s+INTO\s+`?(\w+)`?", normalised, re.IGNORECASE
        )
        if not match:
            raise ValidationError(
                f"Statement #{i}: cannot parse target table:\n  {stmt[:120]}…"
            )

        table = match.group(1)
        if table not in MANAGED_TABLES:
            raise ValidationError(
                f"Statement #{i} targets unknown table `{table}`. "
                f"Allowed: {MANAGED_TABLES}"
            )

        # ── Reject dangerous keywords outside string values ──────────
        stripped = _strip_string_literals(normalised)
        if _DANGEROUS_KW.search(stripped):
            raise ValidationError(
                f"Statement #{i} contains a forbidden keyword:\n  {stmt[:120]}…"
            )

        # ── Column/value count must match — auto-repair if close ─────
        col_match = re.search(
            r"INSERT\s+INTO\s+`?\w+`?\s*\(([^)]+)\)\s*VALUES",
            normalised, re.IGNORECASE,
        )
        val_match = re.search(
            r"VALUES\s*\((.+)\)\s*$", normalised, re.IGNORECASE | re.DOTALL,
        )
        if col_match and val_match:
            num_cols = len(col_match.group(1).split(","))
            num_vals = _count_values(val_match.group(1))

            if num_cols != num_vals:
                if num_vals < num_cols:
                    repaired = _repair_null_padding(
                        normalised, num_cols, num_vals
                    )
                    if repaired:
                        log.warning(
                            "Statement #%d: padded %d missing NULL(s) "
                            "for table `%s`",
                            i, num_cols - num_vals, table,
                        )
                        normalised = repaired
                        stmt = repaired
                    else:
                        raise ValidationError(
                            f"Statement #{i} has {num_cols} column(s) but "
                            f"{num_vals} value(s) — gap too large to repair. "
                            f"Table: `{table}`"
                        )
                else:
                    raise ValidationError(
                        f"Statement #{i} has {num_cols} column(s) but "
                        f"{num_vals} value(s). Table: `{table}`"
                    )

        validated.append(stmt)

    log.info("Validated %d INSERT statement(s)", len(validated))
    return validated
