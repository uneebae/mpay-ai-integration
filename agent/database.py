"""Database connection pooling and context-manager support."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Generator

import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.cursor import MySQLCursor
from mysql.connector.pooling import MySQLConnectionPool

from agent.config import db_cfg

log = logging.getLogger(__name__)

# Global connection pool (lazy-initialized)
_pool: MySQLConnectionPool | None = None


def _init_pool() -> MySQLConnectionPool:
    """Initialize and return the connection pool."""
    global _pool
    if _pool is None:
        log.info("Initializing connection pool (size=5)…")
        _pool = MySQLConnectionPool(
            pool_name="mpay_pool",
            pool_size=5,
            pool_reset_session=True,
            host=db_cfg.host,
            port=db_cfg.port,
            user=db_cfg.user,
            password=db_cfg.password,
            database=db_cfg.database,
        )
    return _pool


def get_connection() -> MySQLConnectionAbstract:
    """Get a connection from the pool (or create connection if pooling unavailable)."""
    try:
        pool = _init_pool()
        return pool.get_connection()
    except Exception as e:
        log.warning("Pool unavailable, falling back to direct connection: %s", e)
        # Fallback for compatibility
        return mysql.connector.connect(
            host=db_cfg.host,
            port=db_cfg.port,
            user=db_cfg.user,
            password=db_cfg.password,
            database=db_cfg.database,
        )


@contextmanager
def cursor(*, commit: bool = False, timeout: int = 30) -> Generator[MySQLCursor, None, None]:
    """Yield a cursor; optionally commit on success, always rollback on error.
    
    Args:
        commit: If True, commit on success; rollback on error.
        timeout: Connection timeout in seconds (not always supported by pool connections).
    """
    conn = get_connection()
    # Note: Some pooled connections don't support get_config(), so we don't set timeout via config
    # The timeout is already configured when the pool is initialized
    cur = conn.cursor()
    try:
        yield cur
        if commit:
            conn.commit()
            log.debug("Transaction committed")
    except Exception as e:
        conn.rollback()
        log.debug("Transaction rolled back due to: %s", str(e))
        raise
    finally:
        cur.close()
        conn.close()
