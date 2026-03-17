"""Integration tests for the complete pipeline."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from agent.validator import validate, ValidationError
from agent.executor import execute, ExecutionError, DataError, ConnectionError, AuthenticationError


class TestValidatorIntegration:
    """Integration tests for validator with realistic scenarios."""

    def test_complex_multi_statement_workflow(self):
        """Test realistic multi-statement validation workflow."""
        sql = """
        INSERT INTO ws_config (base_url, type) VALUES ('https://api1.com', 'TYPE1');
        INSERT INTO ws_config (base_url, type) VALUES ('https://api2.com', 'TYPE2');
        INSERT INTO ws_endpoint_config (endpoint_template, request_format, type, config_id, method) 
            VALUES ('/api/v1', 'JSON_POST', 'TYPE1', 1, 'POST');
        INSERT INTO ws_req_param_details (tran_id, tran_type, req_params, response_type) 
            VALUES (100, 'TYPE1', 'id,name', 'JSON');
        INSERT INTO ws_req_param_map (tran_id, param_name, param_priority, is_mandatory, regex) 
            VALUES (100, 'id', 1, 'Y', '^[0-9]+$');
        """
        result = validate(sql)
        assert len(result) == 5
        assert all("INSERT" in stmt.upper() for stmt in result)

    def test_sql_injection_prevention(self):
        """Verify SQL injection attempts are blocked."""
        malicious_sqls = [
            "INSERT INTO ws_config VALUES ('test'); DROP TABLE ws_config; --')",
            "INSERT INTO ws_config VALUES ('x' OR '1'='1'); DELETE FROM ws_config;",
            "INSERT INTO ws_config VALUES (UNHEX('4142'));  UPDATE ws_config SET type='hacked';",
        ]
        
        for sql in malicious_sqls:
            with pytest.raises(ValidationError):
                validate(sql)

    def test_semicolon_handling_edge_cases(self):
        """Test semicolon handling in various positions."""
        test_cases = [
            # Multiple semicolons
            ("INSERT INTO ws_config (base_url, type) VALUES ('test', 'A');;", 1),
            # Multiple statements with spacing
            ("INSERT INTO ws_config (base_url, type) VALUES ('test1', 'A');  \n\n  INSERT INTO ws_config (base_url, type) VALUES ('test2', 'B');", 2),
        ]
        
        for sql, expected_count in test_cases:
            result = validate(sql)
            assert len(result) == expected_count

    def test_whitespace_normalization(self):
        """Test that excessive whitespace is handled correctly."""
        sql = """
        INSERT 
            INTO 
                ws_config 
                    (base_url,  type) 
                        VALUES 
                            ('https://api.com', 'TEST')
        """
        result = validate(sql)
        assert len(result) == 1
        assert "INSERT" in result[0].upper()

    def test_unicode_and_special_characters(self):
        """Test validation with unicode and special characters in values."""
        sql_with_unicode = """
        INSERT INTO ws_config (base_url, type) VALUES ('https://api.com/路径', 'Type_🚀');
        INSERT INTO ws_config (base_url, type) VALUES ('https://api.com', 'Test\'s_API');
        """
        result = validate(sql_with_unicode)
        assert len(result) == 2


class TestValidatorEdgeCases:
    """Edge case tests for SQL validator."""

    def test_very_long_statement(self):
        """Test handling of very long SQL statements."""
        long_string = "x" * 10000
        sql = f"INSERT INTO ws_config (base_url, type) VALUES ('{long_string}', 'LONG')"
        result = validate(sql)
        assert len(result) == 1

    def test_statements_with_comments(self):
        """Test statements with SQL comments embedded in strings."""
        # Comment as part of string value (not SQL comment)
        sql = """
        INSERT INTO ws_config (base_url, type) VALUES ('https://api.com', 'TEST -- not a comment');
        INSERT INTO ws_config (base_url, type) VALUES ('https://api2.com', 'TEST /* also not a comment */');
        """
        # These should be valid since comments are in string literals
        result = validate(sql)
        assert len(result) == 2

    def test_null_value_handling(self):
        """Test proper handling of NULL values."""
        sql = """
        INSERT INTO ws_config (base_url, type) VALUES (NULL, 'TEST');
        INSERT INTO ws_endpoint_config (data_template, endpoint_template, request_format, response_format, type, config_id) 
            VALUES (NULL, '/api', 'JSON', 'JSON', 'TEST', 1);
        """
        result = validate(sql)
        assert len(result) == 2
        assert any("NULL" in stmt for stmt in result)

    def test_numeric_and_boolean_values(self):
        """Test handling of numeric and boolean values."""
        sql = """
        INSERT INTO ws_req_param_map (tran_id, param_name, param_priority, is_mandatory, is_compress, is_escape, is_max_length_lp) 
            VALUES (100, 'test', 1, 'Y', 0, 1, 1);
        INSERT INTO ws_req_param_map (tran_id, param_name, param_priority, is_mandatory, is_compress) 
            VALUES (101, 'test2', 99, 'N', 1);
        """
        result = validate(sql)
        assert len(result) == 2

    def test_backtick_quoted_identifiers(self):
        """Test table and column names with backticks."""
        sql = "INSERT INTO `ws_config` (`base_url`, `type`) VALUES ('https://api.com', 'TEST')"
        result = validate(sql)
        assert len(result) == 1


class TestValidatorPerformance:
    """Performance tests for validators."""

    def test_many_statements_performance(self):
        """Test validator performance with many statements."""
        statements = ";".join([
            f"INSERT INTO ws_config (base_url, type) VALUES ('https://api{i}.com', 'TYPE{i}')"
            for i in range(100)
        ])
        result = validate(statements)
        assert len(result) == 100

    def test_large_multirow_insert_expansion(self):
        """Test performance of multi-row INSERT expansion."""
        values = ", ".join([f"({i}, 'test{i}')" for i in range(50)])
        sql = f"INSERT INTO ws_req_param_map (tran_id, param_name) VALUES {values}"
        result = validate(sql)
        assert len(result) == 50


@pytest.mark.integration
class TestExecutorWithMocks:
    """Integration tests for executor with mocked database."""

    @patch('agent.executor.cursor')
    def test_successful_execution_with_mock(self, mock_cursor_ctx):
        """Test successful execution with mocked cursor."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor_ctx.return_value = mock_cursor
        
        from agent.executor import execute
        statements = ["INSERT INTO ws_config (base_url, type) VALUES ('test', 'TEST')"]
        result = execute(statements)
        
        assert result == 1
        mock_cursor.execute.assert_called_once()

    @patch('agent.executor.cursor')
    def test_integrity_error_handling(self, mock_cursor_ctx):
        """Test handling of integrity errors during execution."""
        from mysql.connector.errors import IntegrityError
        
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = IntegrityError("Duplicate entry")
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor_ctx.return_value = mock_cursor
        
        from agent.executor import execute, ExecutionError
        statements = ["INSERT INTO ws_config (base_url, type) VALUES ('test', 'TEST')"]
        
        with pytest.raises(ExecutionError):
            execute(statements)

    @patch('agent.executor.cursor')
    def test_multiple_statements_partial_failure(self, mock_cursor_ctx):
        """Test handling when one statement in a batch fails."""
        from mysql.connector.errors import DatabaseError
        
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        # First call succeeds, second fails
        mock_cursor.execute.side_effect = [None, DatabaseError("Error")]
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor_ctx.return_value = mock_cursor
        
        from agent.executor import execute, ExecutionError
        statements = [
            "INSERT INTO ws_config (base_url, type) VALUES ('test', 'TEST')",
            "INSERT INTO ws_config (base_url, type) VALUES ('test2', 'TEST2')"
        ]
        
        with pytest.raises(ExecutionError):
            execute(statements)


class TestValidatorComplexScenarios:
    """Test validator with complex real-world scenarios."""

    def test_real_world_echo_api_spec(self):
        """Test with real Echo API SQL."""
        sql = """
        INSERT INTO ws_config (base_url, type) VALUES ('https://postman-echo.com', 'ECHO_TEST');
        INSERT INTO ws_endpoint_config (data_template, endpoint_template, fields, request_format, response_format, type, config_id, method) 
            VALUES (NULL, '/post', 'message', 'JSON_POST', 'JSON', 'ECHO_TEST', 1, 'POST');
        INSERT INTO ws_req_param_details (tran_id, tran_type, req_params, queue_in, queue_out, req_params_length, queue_type, host_id, from_ip, enclosing_tag, reserval_api, response_type) 
            VALUES (100, 'ECHO_TEST', 'message', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'JSON');
        INSERT INTO ws_req_param_map (tran_id, param_name, param_priority, is_mandatory, is_compress, regex, max_length, append_length, value, log_column, is_escape, function_name, is_max_length_lp) 
            VALUES (100, 'message', 1, 'Y', 0, NULL, NULL, NULL, NULL, NULL, 0, NULL, 0);
        """
        result = validate(sql)
        assert len(result) == 4
        assert all("INSERT" in stmt.upper() for stmt in result)

    def test_real_world_payment_gateway_spec(self):
        """Test with real payment gateway SQL."""
        sql = """
        INSERT INTO ws_config (base_url, type) VALUES ('https://payments.jazz.com.pk', 'JAZZ_PAYMENT');
        INSERT INTO ws_endpoint_config (data_template, endpoint_template, fields, request_format, response_format, type, config_id, method) 
            VALUES (NULL, '/api/v1/payment', 'amount,msisdn,account_id', 'JSON_POST', 'JSON', 'JAZZ_PAYMENT', 1, 'POST');
        INSERT INTO ws_req_param_map (tran_id, param_name, param_priority, is_mandatory, is_compress, regex, max_length, value, is_escape) 
            VALUES (100, 'amount', 1, 'Y', 0, '^[0-9]+(\\.[0-9]+)?$', 10, NULL, 0);
        INSERT INTO ws_req_param_map (tran_id, param_name, param_priority, is_mandatory, is_compress, regex, max_length, value, is_escape) 
            VALUES (100, 'msisdn', 2, 'Y', 0, '^[0-9]{11}$', 11, NULL, 0);
        INSERT INTO ws_req_param_map (tran_id, param_name, param_priority, is_mandatory, is_compress, regex, max_length, value, is_escape) 
            VALUES (100, 'account_id', 3, 'Y', 0, '^[a-zA-Z0-9_]+$', 50, NULL, 0);
        """
        result = validate(sql)
        assert len(result) == 5


@pytest.mark.parametrize("invalid_table", [
    "INSERT INTO fake_table VALUES ('test')",
    "INSERT INTO ws_unknown VALUES ('test')",
    "INSERT INTO `bad_table` VALUES (1, 2)",
])
class TestValidatorInvalidTables:
    """Parametrized tests for invalid table names."""
    
    def test_invalid_table_rejection(self, invalid_table):
        """Test that invalid table names are rejected."""
        with pytest.raises(ValidationError, match="unknown table"):
            validate(invalid_table)


@pytest.mark.parametrize("dangerous_sql", [
    "INSERT INTO ws_config VALUES ('x'); DROP TABLE ws_config;",
    "INSERT INTO ws_config VALUES ('x'); DELETE FROM ws_config;",
    "INSERT INTO ws_config VALUES ('x'); TRUNCATE ws_config;",
    "INSERT INTO ws_config VALUES ('x'); ALTER TABLE ws_config ADD COLUMN hack INT;",
    "INSERT INTO ws_config VALUES ('x'); GRANT ALL ON *.* TO hacker;",
    "INSERT INTO ws_config VALUES ('x'); REVOKE ALL ON *.* FROM user;",
    "INSERT INTO ws_config VALUES ('x'); UPDATE ws_config SET type='hacked';",
    "INSERT INTO ws_config VALUES ('x'); CREATE TABLE backdoor (id INT);",
])
class TestValidatorSecurityChecks:
    """Parametrized security tests for dangerous SQL."""
    
    def test_dangerous_sql_rejection(self, dangerous_sql):
        """Test that dangerous SQL patterns are rejected."""
        with pytest.raises(ValidationError):
            validate(dangerous_sql)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
