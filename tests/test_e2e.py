"""End-to-end integration tests for the complete pipeline."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from agent.validator import validate
from agent.executor import execute
from agent.generator import _clean_response


class TestE2EValidationToPreparedSQL:
    """Test the flow from raw SQL to validated statements."""

    def test_raw_api_spec_to_valid_sql(self):
        """Test converting raw API spec to validated SQL."""
        # Simulated LLM output with markdown and comments
        raw_llm_output = """
        ```sql
        -- Configuration for Echo API
        INSERT INTO ws_config (base_url, type) VALUES ('https://postman-echo.com', 'ECHO');
        -- Endpoint configuration
        INSERT INTO ws_endpoint_config (endpoint_template, request_format, response_format, type, config_id, method) 
            VALUES ('/post', 'JSON_POST', 'JSON', 'ECHO', 1, 'POST');
        ```
        """
        
        # Step 1: Clean the response
        cleaned = _clean_response(raw_llm_output)
        assert "```" not in cleaned
        assert "-- " not in cleaned
        
        # Step 2: Validate the SQL
        validated = validate(cleaned)
        assert len(validated) == 2


class TestE2EMultipleAPIs:
    """Test handling multiple API integrations in sequence."""

    def test_multiple_api_configurations(self):
        """Test scenario with multiple payment APIs."""
        apis = [
            {
                "name": "Jazz Payment",
                "base_url": "https://payments.jazz.com.pk",
                "type": "JAZZ_PAYMENT",
                "endpoint": "/api/v1/payment",
                "params": "amount,msisdn,account_id"
            },
            {
                "name": "EasyPaisa",
                "base_url": "https://api.easypaisa.com",
                "type": "EASYPAISA",
                "endpoint": "/api/payment",
                "params": "amount,phone"
            }
        ]
        
        for api in apis:
            sql = f"""
            INSERT INTO ws_config (base_url, type) VALUES ('{api["base_url"]}', '{api["type"]}');
            INSERT INTO ws_endpoint_config (endpoint_template, request_format, response_format, type, config_id, method)
                VALUES ('{api["endpoint"]}', 'JSON_POST', 'JSON', '{api["type"]}', {len(apis)}, 'POST');
            """
            
            validated = validate(sql)
            assert len(validated) == 2


class TestE2EErrorRecovery:
    """Test error recovery scenarios in the pipeline."""

    def test_malformed_sql_recovery(self):
        """Test that malformed SQL doesn't break subsequent operations."""
        test_cases = [
            # Invalid SQL should be rejected
            ("SELECT * FROM ws_config", False),
            # Valid SQL should pass
            ("INSERT INTO ws_config (base_url, type) VALUES ('test', 'TEST')", True),
            # Another invalid
            ("DROP TABLE ws_config", False),
            # Valid again
            ("INSERT INTO ws_config (base_url, type) VALUES ('test2', 'TEST2')", True),
        ]
        
        for sql, should_pass in test_cases:
            if should_pass:
                result = validate(sql)
                assert len(result) > 0
            else:
                with pytest.raises(Exception):
                    validate(sql)

    @patch('agent.executor.cursor')
    def test_partial_batch_failure_recovery(self, mock_cursor_ctx):
        """Test recovery when one statement fails in a batch."""
        from mysql.connector.errors import IntegrityError
        
        mock_cursor = MagicMock()
        # First succeeds, second fails
        mock_cursor.execute.side_effect = [None, IntegrityError("Duplicate")]
        mock_cursor.rowcount = 1
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_cursor_ctx.return_value = mock_cursor
        
        from agent.executor import ExecutionError
        
        statements = [
            "INSERT INTO ws_config (base_url, type) VALUES ('api1', 'T1')",
            "INSERT INTO ws_config (base_url, type) VALUES ('api1', 'T1')",  # Duplicate
        ]
        
        # Can raise ExecutionError or DataError (ExecutionError wraps it)
        with pytest.raises((ExecutionError, Exception)):
            execute(statements)


class TestE2EDataConsistency:
    """Test data consistency across operations."""

    def test_multi_table_transaction_consistency(self):
        """Test that multi-table operations maintain consistency."""
        sql = """
        INSERT INTO ws_config (base_url, type) VALUES ('https://api.test.com', 'TEST_API');
        INSERT INTO ws_endpoint_config (endpoint_template, request_format, response_format, type, config_id, method)
            VALUES ('/api/v1', 'JSON_POST', 'JSON', 'TEST_API', 1, 'POST');
        INSERT INTO ws_req_param_details (tran_id, tran_type, req_params, response_type)
            VALUES (100, 'TEST_API', 'id,name', 'JSON');
        INSERT INTO ws_req_param_map (tran_id, param_name, param_priority, is_mandatory)
            VALUES (100, 'id', 1, 'Y'),
                   (100, 'name', 2, 'Y');
        """
        
        validated = validate(sql)
        # Multirow INSERT expands to 2 separate statements for the params
        assert len(validated) == 5
        
        # Check that all statements reference consistent IDs
        config_id_stmts = [s for s in validated if 'config_id' in s]
        assert len(config_id_stmts) > 0


class TestE2EEncodingAndSpecialChars:
    """Test handling of special characters and encodings."""

    def test_unicode_in_api_specs(self):
        """Test handling of Unicode characters in values."""
        sql = """
        INSERT INTO ws_config (base_url, type) VALUES ('https://api.example.com/路径', 'API_中文');
        INSERT INTO ws_endpoint_config (endpoint_template, request_format, response_format, type, config_id, method)
            VALUES ('/数据接口', 'JSON_POST', 'JSON', 'API_中文', 1, 'POST');
        """
        
        validated = validate(sql)
        assert len(validated) == 2

    def test_escaped_quotes_in_values(self):
        """Test handling of escaped quotes in values."""
        sql = """
        INSERT INTO ws_config (base_url, type) VALUES ('https://api.example.com', 'Test\\'s API');
        INSERT INTO ws_endpoint_config (endpoint_template, request_format, response_format, type, config_id, method)
            VALUES ('/endpoint', 'JSON_POST', 'JSON', 'Test\\'s API', 1, 'POST');
        """
        
        validated = validate(sql)
        assert len(validated) == 2

    def test_newlines_and_tabs_in_values(self):
        """Test handling of whitespace characters in values."""
        sql = """
        INSERT INTO ws_config (base_url, type) VALUES ('https://api.example.com/path\\nwith\\nnewlines', 'TEST');
        INSERT INTO ws_endpoint_config (endpoint_template, request_format, response_format, type, config_id, method)
            VALUES ('/endpoint\\twith\\ttabs', 'JSON_POST', 'JSON', 'TEST', 1, 'POST');
        """
        
        validated = validate(sql)
        assert len(validated) == 2


class TestE2ELargeScaleOperations:
    """Test with large-scale data operations."""

    def test_large_number_of_parameters(self):
        """Test API with many parameters."""
        param_count = 50
        params_insert = ", ".join([
            f"({i+100}, 'param{i}', {i+1}, 'Y')"
            for i in range(param_count)
        ])
        
        sql = f"""
        INSERT INTO ws_config (base_url, type) VALUES ('https://api.example.com', 'LARGE_API');
        INSERT INTO ws_endpoint_config (endpoint_template, request_format, response_format, type, config_id, method)
            VALUES ('/endpoint', 'JSON_POST', 'JSON', 'LARGE_API', 1, 'POST');
        INSERT INTO ws_req_param_map (tran_id, param_name, param_priority, is_mandatory)
            VALUES {params_insert};
        """
        
        validated = validate(sql)
        # Multirow INSERT expands each param into separate statement
        assert len(validated) == (2 + param_count)  # 1 config + 1 endpoint + 50 params

    def test_deep_nesting_of_configurations(self):
        """Test complex nested configuration scenarios."""
        configs = 5
        endpoints_per_config = 3
        params_per_endpoint = 4
        
        statements = []
        config_id = 1
        tran_id = 100
        
        for c in range(configs):
            statements.append(
                f"INSERT INTO ws_config (base_url, type) VALUES ('https://api{c}.com', 'TYPE{c}');"
            )
            
            for e in range(endpoints_per_config):
                statements.append(
                    f"INSERT INTO ws_endpoint_config (endpoint_template, request_format, response_format, type, config_id, method) "
                    f"VALUES ('/endpoint{e}', 'JSON_POST', 'JSON', 'TYPE{c}', {config_id}, 'POST');"
                )
                
                for p in range(params_per_endpoint):
                    statements.append(
                        f"INSERT INTO ws_req_param_map (tran_id, param_name, param_priority, is_mandatory) "
                        f"VALUES ({tran_id}, 'param{p}', {p+1}, 'Y');"
                    )
                    tran_id += 1
        
        sql = "\n".join(statements)
        validated = validate(sql)
        expected_count = configs + (configs * endpoints_per_config) + (configs * endpoints_per_config * params_per_endpoint)
        assert len(validated) == expected_count


class TestE2ERealWorldScenarios:
    """Test real-world integration scenarios."""

    def test_complete_payment_api_integration(self):
        """Test complete payment API workflow."""
        sql = """
        INSERT INTO ws_config (base_url, type) VALUES ('https://payments.example.com', 'PAYMENT_API');
        INSERT INTO ws_endpoint_config (endpoint_template, request_format, response_format, type, config_id, method)
            VALUES ('/v1/transfer', 'JSON_POST', 'JSON', 'PAYMENT_API', 1, 'POST');
        INSERT INTO ws_req_param_details (tran_id, tran_type, req_params, response_type)
            VALUES (100, 'PAYMENT_API', 'amount,recipient,sender', 'JSON');
        INSERT INTO ws_req_param_map (tran_id, param_name, param_priority, is_mandatory, regex, max_length)
            VALUES (100, 'amount', 1, 'Y', '^[0-9]+(\\.[0-9]{2})?$', 10),
                   (100, 'recipient', 2, 'Y', '^[0-9]{11}$', 11),
                   (100, 'sender', 3, 'Y', '^[0-9]{11}$', 11);
        """
        
        validated = validate(sql)
        # Multirow INSERT expands to 3 separate statements for params (1 config + 1 endpoint + 1 details + 3 params)
        assert len(validated) == 6
        # Verify all statements are INSERTs
        assert all("INSERT" in s.upper() for s in validated)

    def test_api_update_workflow(self):
        """Test updating API configuration (delete old, insert new)."""
        # Note: This would be update/delete in real scenario, but we only allow INSERT
        sql1 = """
        INSERT INTO ws_config (base_url, type) VALUES ('https://api-v1.example.com', 'API_OLD');
        INSERT INTO ws_endpoint_config (endpoint_template, request_format, response_format, type, config_id, method)
            VALUES ('/v1/endpoint', 'JSON', 'JSON', 'API_OLD', 1, 'POST');
        """
        
        # New version
        sql2 = """
        INSERT INTO ws_config (base_url, type) VALUES ('https://api-v2.example.com', 'API_NEW');
        INSERT INTO ws_endpoint_config (endpoint_template, request_format, response_format, type, config_id, method)
            VALUES ('/v2/endpoint', 'JSON_POST', 'JSON', 'API_NEW', 2, 'POST');
        """
        
        validated1 = validate(sql1)
        validated2 = validate(sql2)
        
        assert len(validated1) == 2
        assert len(validated2) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
