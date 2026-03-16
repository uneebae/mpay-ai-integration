"""Auto-discover the Mpay schema from the live database.

This eliminates the need to hard-code column names inside LLM prompts.
Every time the agent runs it reads the *real* schema, so prompt and DB
can never drift out of sync.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from agent.database import cursor

log = logging.getLogger(__name__)

# Tables the agent is allowed to generate INSERTs for.
MANAGED_TABLES = [
    "ws_config",
    "ws_req_param_details",
    "ws_req_param_map",
    "ws_endpoint_config",
]


@dataclass(frozen=True)
class Column:
    name: str
    col_type: str
    is_nullable: bool
    key: str  # PRI, MUL, UNI, or ""
    default: str | None
    extra: str  # e.g. "auto_increment"


@dataclass(frozen=True)
class TableSchema:
    name: str
    columns: list[Column]

    def to_prompt_text(self) -> str:
        """Render this table as concise DDL-like text the LLM can consume."""
        lines = [f"Table `{self.name}`"]
        for c in self.columns:
            parts = [f"  - {c.name} {c.col_type}"]
            if c.key == "PRI":
                parts.append("PRIMARY KEY")
            if c.extra:
                parts.append(c.extra.upper())
            if not c.is_nullable:
                parts.append("NOT NULL")
            if c.default is not None:
                parts.append(f"DEFAULT {c.default}")
            lines.append(" ".join(parts))
        return "\n".join(lines)


def discover_schema() -> list[TableSchema]:
    """Query INFORMATION_SCHEMA and return structured metadata."""
    schemas: list[TableSchema] = []
    with cursor() as cur:
        for table in MANAGED_TABLES:
            cur.execute(
                "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, "
                "COLUMN_DEFAULT, EXTRA "
                "FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
                "ORDER BY ORDINAL_POSITION",
                (table,),
            )
            cols = [
                Column(
                    name=row[0],
                    col_type=row[1],
                    is_nullable=row[2] == "YES",
                    key=row[3] or "",
                    default=row[4],
                    extra=row[5] or "",
                )
                for row in cur.fetchall()
            ]
            if cols:
                schemas.append(TableSchema(name=table, columns=cols))
            else:
                log.warning("Table %s not found in database", table)
    return schemas


def get_next_tran_id() -> int:
    """Return the next available tran_id (max + 1, or 100 if table is empty)."""
    with cursor() as cur:
        cur.execute(
            "SELECT COALESCE(MAX(tran_id), 99) + 1 FROM ws_req_param_details"
        )
        return cur.fetchone()[0]


def get_next_config_id() -> int:
    """Return the next auto-increment id for ws_config."""
    with cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM ws_config")
        return cur.fetchone()[0]


def schema_as_prompt(schemas: list[TableSchema] | None = None) -> str:
    """Return the full prompt-ready schema block."""
    schemas = schemas or discover_schema()
    return "\n\n".join(s.to_prompt_text() for s in schemas)
