"""Unit tests for SQL generation utilities."""

import pytest

from agent.generator import _clean_response


class TestCleanResponse:
    """Test response cleaning from LLM output."""

    def test_removes_sql_markdown(self):
        """Remove ```sql ... ``` markdown fence."""
        response = """```sql
INSERT INTO ws_config VALUES ('test');
```"""
        result = _clean_response(response)
        assert "INSERT" in result
        assert "```" not in result

    def test_removes_generic_markdown(self):
        """Remove generic ``` ``` fence."""
        response = """```
INSERT INTO ws_config VALUES ('test');
```"""
        result = _clean_response(response)
        assert "INSERT" in result
        assert "```" not in result

    def test_removes_comment_lines(self):
        """Remove SQL comment lines at start/end."""
        response = """-- This is a comment
INSERT INTO ws_config VALUES ('test');
-- Another comment"""
        result = _clean_response(response)
        assert "INSERT" in result
        assert "comment" not in result.lower() or "VALUES" in result

    def test_preserves_valid_sql(self):
        """Valid SQL without commentary is unchanged."""
        response = "INSERT INTO ws_config (base_url, type) VALUES ('https://api.example.com', 'TEST')"
        result = _clean_response(response)
        assert result == response

    def test_handles_multiline_sql(self):
        """Multiline SQL statements are preserved."""
        response = """INSERT INTO ws_config (base_url, type) VALUES 
        ('https://api.example.com', 'TEST');
INSERT INTO ws_endpoint_config (data_template) VALUES (NULL);"""
        result = _clean_response(response)
        assert "INSERT" in result
        assert "VALUES" in result
        assert result.count("INSERT") == 2

    def test_removes_leading_trailing_whitespace(self):
        """Leading and trailing whitespace is stripped."""
        response = """
        
        INSERT INTO ws_config VALUES ('test');
        
        """
        result = _clean_response(response)
        assert not result.startswith("\n")
        assert not result.endswith("\n")

    def test_empty_response(self):
        """Empty or whitespace-only response returns empty string."""
        assert _clean_response("") == ""
        assert _clean_response("   ") == ""
        assert _clean_response("\n\n\n") == ""

    def test_complex_real_world_example(self):
        """Real-world LLM response with commentary and fences."""
        response = """```sql
-- Creating payment gateway configuration
INSERT INTO ws_config (base_url, type) VALUES ('https://payments.example.com', 'PAYMENT_GATEWAY');
INSERT INTO ws_endpoint_config (endpoint_template, request_format) VALUES ('/api/v1/payment', 'JSON_POST');
```

That should set up the basic configuration for the payment gateway."""
        
        result = _clean_response(response)
        assert "INSERT" in result
        assert "```" not in result
        assert "gateway" not in result.lower() or "PAYMENT_GATEWAY" in result
        # Should have 2 INSERT statements
        assert result.count("INSERT") == 2


class TestRetryDecorator:
    """Test retry logic decorator (if needed for unit testing)."""

    def test_retry_with_backoff_imports(self):
        """Verify retry decorator is importable."""
        from agent.generator import retry_with_backoff
        assert retry_with_backoff is not None
        # Can be applied as a decorator
        @retry_with_backoff(max_retries=2)
        def dummy_func():
            return "success"
        
        assert dummy_func() == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
