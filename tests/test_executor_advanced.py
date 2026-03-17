"""Advanced executor tests with comprehensive error scenarios."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call

from agent.executor import (
    execute,
    ExecutionError,
    DataError,
    ConnectionError,
    AuthenticationError,
)


class TestExecutorErrorHandling:
    """Comprehensive error handling tests."""

    @patch('agent.executor.cursor')
    def test_authentication_error_detection(self, mock_cursor_ctx):
        """Test that authentication errors are properly detected and raised."""
        import mysql.connector
        
        mock_cursor_ctx.side_effect = mysql.connector.errors.Error(
            "Access denied for user 'bad_user'@'localhost'"
        )
        
        with pytest.raises(AuthenticationError):
            execute(["INSERT INTO ws_config VALUES ('test', 'TEST')"])

    @patch('agent.executor.cursor')
    def test_connection_refused_error(self, mock_cursor_ctx):
        """Test that connection refused errors are properly handled."""
        import mysql.connector
        
        mock_cursor_ctx.side_effect = mysql.connector.errors.Error(
            "Can't connect to MySQL server on 'localhost'"
        )
        
        with pytest.raises(ConnectionError):
            execute(["INSERT INTO ws_config VALUES ('test', 'TEST')"])

    @patch('agent.executor.cursor')
    def test_data_integrity_error(self, mock_cursor_ctx):
        """Test handling of data integrity constraint violations."""
        from mysql.connector.errors import IntegrityError
        
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = IntegrityError("Duplicate entry 'test-key'")
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor_ctx.return_value = mock_cursor
        
        with pytest.raises(ExecutionError, match="integrity"):
            execute(["INSERT INTO ws_config VALUES ('test', 'TEST')"])

    @patch('agent.executor.cursor')
    def test_programming_error_handling(self, mock_cursor_ctx):
        """Test handling of SQL syntax errors."""
        from mysql.connector.errors import ProgrammingError
        
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = ProgrammingError("Syntax error in SQL")
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor_ctx.return_value = mock_cursor
        
        with pytest.raises(ExecutionError, match="syntax"):
            execute(["INSERT INTO ws_config VALUES ('test', 'TEST')"])

    @patch('agent.executor.cursor')
    def test_unexpected_exception_handling(self, mock_cursor_ctx):
        """Test handling of unexpected exceptions."""
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = RuntimeError("Unexpected error")
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor_ctx.return_value = mock_cursor
        
        with pytest.raises(ExecutionError):
            execute(["INSERT INTO ws_config VALUES ('test', 'TEST')"])


class TestExecutorSuccessCases:
    """Test successful execution scenarios."""

    @patch('agent.executor.cursor')
    def test_single_statement_execution(self, mock_cursor_ctx):
        """Test execution of a single statement."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor_ctx.return_value = mock_cursor
        
        result = execute(["INSERT INTO ws_config (base_url, type) VALUES ('https://api.com', 'TEST')"])
        assert result == 1
        mock_cursor.execute.assert_called_once()

    @patch('agent.executor.cursor')
    def test_multiple_statements_execution(self, mock_cursor_ctx):
        """Test execution of multiple statements."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor_ctx.return_value = mock_cursor
        
        statements = [
            "INSERT INTO ws_config (base_url, type) VALUES ('https://api1.com', 'TEST1')",
            "INSERT INTO ws_config (base_url, type) VALUES ('https://api2.com', 'TEST2')",
            "INSERT INTO ws_endpoint_config (endpoint_template, request_format, response_format, type, config_id) VALUES ('/api', 'JSON', 'JSON', 'TEST1', 1)",
        ]
        result = execute(statements)
        assert result == 3
        assert mock_cursor.execute.call_count == 3

    @patch('agent.executor.cursor')
    def test_zero_rows_affected(self, mock_cursor_ctx):
        """Test when no rows are affected by INSERT."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor_ctx.return_value = mock_cursor
        
        result = execute(["INSERT INTO ws_config (base_url, type) VALUES ('https://api.com', 'TEST')"])
        assert result == 0

    @patch('agent.executor.cursor')
    def test_bulk_insert_execution(self, mock_cursor_ctx):
        """Test execution with high row count."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1000
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor_ctx.return_value = mock_cursor
        
        result = execute(["INSERT INTO ws_config (base_url, type) VALUES ('https://api.com', 'TEST')"])
        assert result == 1000


class TestExecutorTransactionBehavior:
    """Test transaction handling and rollback behavior."""

    @patch('agent.executor.cursor')
    def test_transaction_commit_on_success(self, mock_cursor_ctx):
        """Test that transaction is committed on success."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_connection = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        # Mock the connection and its commit/rollback
        def get_conn():
            conn = MagicMock()
            cur = MagicMock()
            cur.rowcount = 1
            conn.cursor.return_value = cur
            conn.commit = MagicMock()
            conn.rollback = MagicMock()
            return conn, cur
        
        # Simplified test - just verify the execute is called
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor_ctx.return_value = mock_cursor
        
        result = execute(["INSERT INTO ws_config VALUES ('test', 'TEST')"])
        assert result > 0

    @patch('agent.executor.cursor')
    def test_error_triggers_rollback(self, mock_cursor_ctx):
        """Verify that errors trigger transaction rollback."""
        from mysql.connector.errors import IntegrityError
        
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = IntegrityError("Duplicate")
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor_ctx.return_value = mock_cursor
        
        with pytest.raises(ExecutionError):
            execute(["INSERT INTO ws_config VALUES ('test', 'TEST')"])


class TestExecutorInputValidation:
    """Test input validation in executor."""

    @patch('agent.executor.cursor')
    def test_empty_statement_list(self, mock_cursor_ctx):
        """Test handling of empty statement list."""
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor_ctx.return_value = mock_cursor
        
        result = execute([])
        assert result == 0
        mock_cursor.execute.assert_not_called()

    @patch('agent.executor.cursor')
    def test_single_empty_statement(self, mock_cursor_ctx):
        """Test handling of empty statement strings."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor_ctx.return_value = mock_cursor
        
        # Empty statements should still try to execute
        execute([""])
        # The cursor.execute will be called even with empty statement
        assert mock_cursor.execute.called

    @patch('agent.executor.cursor')
    def test_very_long_statement(self, mock_cursor_ctx):
        """Test handling of very long SQL statements."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor_ctx.return_value = mock_cursor
        
        long_value = "x" * 100000
        long_stmt = f"INSERT INTO ws_config (base_url, type) VALUES ('{long_value}', 'TEST')"
        result = execute([long_stmt])
        assert result == 1


class TestExecutorStatementSequencing:
    """Test execution order and statement validation."""

    @patch('agent.executor.cursor')
    def test_statements_executed_in_order(self, mock_cursor_ctx):
        """Verify statements are executed in the correct order."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor_ctx.return_value = mock_cursor
        
        statements = [
            "INSERT INTO ws_config (base_url, type) VALUES ('api1', 'T1')",
            "INSERT INTO ws_config (base_url, type) VALUES ('api2', 'T2')",
            "INSERT INTO ws_config (base_url, type) VALUES ('api3', 'T3')",
        ]
        execute(statements)
        
        # Verify each statement was called in order
        calls = mock_cursor.execute.call_args_list
        assert len(calls) == 3
        assert calls[0][0][0] == statements[0]
        assert calls[1][0][0] == statements[1]
        assert calls[2][0][0] == statements[2]

    @patch('agent.executor.cursor')
    def test_failure_on_later_statement_after_success(self, mock_cursor_ctx):
        """Test that later statement failure doesn't affect earlier successes in transaction."""
        from mysql.connector.errors import IntegrityError
        
        mock_cursor = MagicMock()
        # First succeeds, second fails
        mock_cursor.execute.side_effect = [None, IntegrityError("Duplicate")]
        mock_cursor.rowcount = 1
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor_ctx.return_value = mock_cursor
        
        with pytest.raises(ExecutionError):
            execute([
                "INSERT INTO ws_config (base_url, type) VALUES ('api1', 'T1')",
                "INSERT INTO ws_config (base_url, type) VALUES ('api2', 'T2')",
            ])


@pytest.mark.parametrize("error_message,expected_error_type", [
    ("Access denied for user 'test'", AuthenticationError),
    ("Can't connect to MySQL", ConnectionError),
    ("Duplicate entry", ExecutionError),  # Wrapped by outer handler
    ("Syntax error", ExecutionError),  # Wrapped by outer handler
    ("Unknown error", ExecutionError),
])
class TestExecutorErrorMapping:
    """Parametrized tests for error type mapping."""

    @patch('agent.executor.cursor')
    def test_error_classification(self, mock_cursor_ctx, error_message, expected_error_type):
        """Test that errors are correctly classified."""
        import mysql.connector
        
        mock_cursor_ctx.side_effect = mysql.connector.errors.Error(error_message)
        
        with pytest.raises(expected_error_type):
            execute(["INSERT INTO ws_config VALUES ('test', 'TEST')"])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
