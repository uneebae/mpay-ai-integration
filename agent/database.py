"""Thin wrapper around mysql.connector with context-manager support."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

import mysql.connector
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursor

from agent.config import db_cfg

log = logging.getLogger(__name__)


def get_connection() -> MySQLConnection:
    """Create and return a new MySQL connection."""
    return mysql.connector.connect(
        host=db_cfg.host,
        port=db_cfg.port,
        user=db_cfg.user,
        password=db_cfg.password,
        database=db_cfg.database,
    )


@contextmanager
def cursor(*, commit: bool = False) -> Generator[MySQLCursor, None, None]:
    """Yield a cursor; optionally commit on success, always rollback on error."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        yield cur
        if commit:
            conn.commit()
            log.debug("Transaction committed")
    except Exception:
        conn.rollback()
        log.debug("Transaction rolled back")
        raise
    finally:
        cur.close()
        conn.close()
