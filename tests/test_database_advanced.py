"""Database module tests with connection pooling and error handling."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from agent.database import cursor, get_connection, _init_pool


class TestConnectionPooling:
    """Test connection pool initialization and behavior."""

    @patch('agent.database.MySQLConnectionPool')
    def test_pool_initialization(self, mock_pool_class):
        """Test that connection pool is initialized correctly."""
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool
        
        # Clear the module-level _pool to force re-initialization
        import agent.database
        agent.database._pool = None
        
        pool = _init_pool()
        
        mock_pool_class.assert_called_once()
        call_kwargs = mock_pool_class.call_args[1]
        assert call_kwargs['pool_name'] == 'mpay_pool'
        assert call_kwargs['pool_size'] == 5
        assert call_kwargs['pool_reset_session'] is True

    @patch('agent.database.MySQLConnectionPool')
    def test_pool_singleton_pattern(self, mock_pool_class):
        """Test that pool is only created once (singleton pattern)."""
        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool
        
        import agent.database
        agent.database._pool = None
        
        pool1 = _init_pool()
        pool2 = _init_pool()
        
        # Should only be called once
        assert mock_pool_class.call_count == 1
        assert pool1 is pool2

    @patch('agent.database._init_pool')
    def test_get_connection_from_pool(self, mock_init_pool):
        """Test getting connection from pool."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool.get_connection.return_value = mock_conn
        mock_init_pool.return_value = mock_pool
        
        conn = get_connection()
        
        assert conn == mock_conn
        mock_pool.get_connection.assert_called_once()

    @patch('agent.database._init_pool')
    @patch('agent.database.mysql.connector.connect')
    def test_fallback_to_direct_connection(self, mock_direct_connect, mock_init_pool):
        """Test fallback to direct connection when pool is unavailable."""
        mock_init_pool.side_effect = Exception("Pool unavailable")
        mock_conn = MagicMock()
        mock_direct_connect.return_value = mock_conn
        
        conn = get_connection()
        
        assert conn == mock_conn
        mock_direct_connect.assert_called_once()


class TestCursorContextManager:
    """Test cursor context manager behavior."""

    @patch('agent.database.get_connection')
    def test_cursor_context_success_commit(self, mock_get_conn):
        """Test successful cursor execution with commit."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_conn.return_value = mock_conn
        
        with cursor(commit=True) as cur:
            cur.execute("INSERT INTO ws_config VALUES ('test', 'TEST')")
        
        mock_conn.commit.assert_called_once()
        mock_conn.rollback.assert_not_called()
        mock_cur.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('agent.database.get_connection')
    def test_cursor_context_no_commit(self, mock_get_conn):
        """Test cursor execution without commit."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_conn.return_value = mock_conn
        
        with cursor(commit=False) as cur:
            cur.execute("SELECT * FROM ws_config")
        
        mock_conn.commit.assert_not_called()
        mock_cur.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('agent.database.get_connection')
    def test_cursor_context_error_rollback(self, mock_get_conn):
        """Test that exceptions trigger rollback."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_conn.return_value = mock_conn
        
        with pytest.raises(ValueError):
            with cursor(commit=True) as cur:
                raise ValueError("Test error")
        
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()
        mock_cur.close.assert_called_once()

    @patch('agent.database.get_connection')
    def test_cursor_context_cleanup_on_error(self, mock_get_conn):
        """Test that cursor and connection are cleaned up even on error."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_conn.return_value = mock_conn
        
        try:
            with cursor(commit=True) as cur:
                raise RuntimeError("Critical error")
        except RuntimeError:
            pass
        
        mock_cur.close.assert_called_once()
        mock_conn.close.assert_called_once()


class TestCursorExecution:
    """Test actual cursor execution behavior."""

    @patch('agent.database.get_connection')
    def test_execute_single_statement(self, mock_get_conn):
        """Test executing a single SQL statement."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.rowcount = 1
        mock_conn.cursor.return_value = mock_cur
        mock_get_conn.return_value = mock_conn
        
        with cursor(commit=True) as cur:
            cur.execute("INSERT INTO ws_config (base_url, type) VALUES ('test', 'TEST')")
        
        mock_cur.execute.assert_called_once_with("INSERT INTO ws_config (base_url, type) VALUES ('test', 'TEST')")

    @patch('agent.database.get_connection')
    def test_fetch_results(self, mock_get_conn):
        """Test fetching results from cursor."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [('test', 'TEST')]
        mock_conn.cursor.return_value = mock_cur
        mock_get_conn.return_value = mock_conn
        
        with cursor() as cur:
            cur.execute("SELECT base_url, type FROM ws_config")
            result = cur.fetchall()
        
        assert result == [('test', 'TEST')]

    @patch('agent.database.get_connection')
    def test_cursor_execute_many(self, mock_get_conn):
        """Test executemany with multiple rows."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.rowcount = 3
        mock_conn.cursor.return_value = mock_cur
        mock_get_conn.return_value = mock_conn
        
        data = [('api1', 'T1'), ('api2', 'T2'), ('api3', 'T3')]
        with cursor(commit=True) as cur:
            cur.executemany(
                "INSERT INTO ws_config (base_url, type) VALUES (%s, %s)",
                data
            )
        
        mock_cur.executemany.assert_called_once()
        assert mock_cur.rowcount == 3


class TestConnectionErrors:
    """Test behavior with connection errors."""

    @patch('agent.database.get_connection')
    def test_connection_error_handling(self, mock_get_conn):
        """Test handling of connection errors."""
        import mysql.connector
        
        mock_get_conn.side_effect = mysql.connector.Error("Connection failed")
        
        with pytest.raises(Exception):
            with cursor() as cur:
                cur.execute("SELECT 1")

    @patch('agent.database.get_connection')
    def test_cursor_creation_error(self, mock_get_conn):
        """Test handling of cursor creation errors."""
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = RuntimeError("Cursor creation failed")
        mock_get_conn.return_value = mock_conn
        
        with pytest.raises(RuntimeError):
            with cursor() as cur:
                pass


class TestDatabaseLogging:
    """Test that database operations are properly logged."""

    @patch('agent.database.log')
    @patch('agent.database._init_pool')
    def test_pool_initialization_logged(self, mock_init_pool, mock_log):
        """Test that pool initialization is logged."""
        mock_pool = MagicMock()
        mock_init_pool.return_value = mock_pool
        
        import agent.database
        agent.database._pool = None
        
        # Call init_pool through get_connection to also test logging
        _init_pool()
        
        # Check if info was logged
        mock_log.info.assert_called()

    @patch('agent.database.get_connection')
    @patch('agent.database.log')
    def test_transaction_commit_logged(self, mock_log, mock_get_conn):
        """Test that commits are logged."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_conn.return_value = mock_conn
        
        with cursor(commit=True) as cur:
            cur.execute("INSERT INTO ws_config VALUES ('test', 'TEST')")
        
        mock_log.debug.assert_called()

    @patch('agent.database.get_connection')
    @patch('agent.database.log')
    def test_transaction_rollback_logged(self, mock_log, mock_get_conn):
        """Test that rollbacks are logged."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_conn.return_value = mock_conn
        
        try:
            with cursor(commit=True) as cur:
                raise RuntimeError("Test error")
        except RuntimeError:
            pass
        
        # Should log debug message about rollback
        mock_log.debug.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
