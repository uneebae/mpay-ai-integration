"""Execute validated SQL statements safely inside a transaction."""

from __future__ import annotations

import logging

import mysql.connector
from mysql.connector.errors import DatabaseError, IntegrityError, ProgrammingError

from agent.database import cursor

log = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Base class for execution errors."""
    pass


class AuthenticationError(ExecutionError):
    """Database authentication failed."""
    pass


class ConnectionError(ExecutionError):
    """Database connection failed."""
    pass


class DataError(ExecutionError):
    """Data integrity or constraint violation."""
    pass


def execute(statements: list[str]) -> int:
    """Execute a list of pre-validated INSERT statements.
    
    Returns the number of rows inserted.
    
    Raises:
        AuthenticationError: If authentication fails.
        ConnectionError: If database connection fails.
        DataError: If data constraints are violated.
        ExecutionError: For other execution errors.
    """
    total = 0
    
    try:
        with cursor(commit=True) as cur:
            for i, stmt in enumerate(statements, 1):
                log.debug("Executing statement %d/%d: %s…", i, len(statements), stmt[:80])
                
                try:
                    cur.execute(stmt)
                    rows = cur.rowcount
                    total += rows
                    log.debug("Statement %d: inserted %d row(s)", i, rows)
                    
                except IntegrityError as e:
                    raise DataError(
                        f"Data integrity violation in statement #{i}: {e}"
                    ) from e
                except ProgrammingError as e:
                    raise DataError(
                        f"SQL syntax or column error in statement #{i}: {e}"
                    ) from e
                except DatabaseError as e:
                    raise DataError(
                        f"Database error in statement #{i}: {e}"
                    ) from e
        
        log.info("✓ Successfully executed %d statement(s), inserted %d row(s)", 
                 len(statements), total)
        return total
        
    except (mysql.connector.errors.Error, mysql.connector.Error) as e:
        error_msg = str(e).lower()
        
        if "access denied" in error_msg or "authentication" in error_msg:
            raise AuthenticationError(
                f"Database authentication failed. Check MYSQL_USER and MYSQL_PASSWORD. Details: {e}"
            ) from e
        
        if "can't connect" in error_msg or "connection refuse" in error_msg:
            raise ConnectionError(
                f"Cannot connect to database at {log.name}. Is MySQL running? Details: {e}"
            ) from e
        
        if isinstance(e, (IntegrityError, ProgrammingError, DatabaseError)):
            raise DataError(f"Database error: {e}") from e
        
        raise ExecutionError(f"Unexpected database error: {e}") from e
        
    except Exception as e:
        raise ExecutionError(f"Execution failed (transaction rolled back): {e}") from e

