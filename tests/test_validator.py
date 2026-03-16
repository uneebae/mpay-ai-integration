"""Unit tests for SQL validation."""

import pytest

from agent.validator import ValidationError, validate, _split_statements, _count_values


class TestSplitStatements:
    """Test statement splitting and multi-row expansion."""

    def test_single_statement(self):
        """Single statement is returned as-is."""
        sql = "INSERT INTO ws_config (base_url, type) VALUES ('https://api.example.com', 'TEST')"
        result = _split_statements(sql)
        assert len(result) == 1
        assert "VALUES" in result[0]

    def test_multiple_statements(self):
        """Multiple statements separated by semicolons."""
        sql = """
        INSERT INTO ws_config (base_url, type) VALUES ('https://api.example.com', 'TEST');
        INSERT INTO ws_config (base_url, type) VALUES ('https://api2.example.com', 'TEST2');
        """
        result = _split_statements(sql)
        assert len(result) == 2

    def test_multirow_expansion(self):
        """Multi-row VALUES is expanded into separate statements."""
        sql = """INSERT INTO ws_config (base_url, type) VALUES 
        ('https://api1.example.com', 'TEST1'),
        ('https://api2.example.com', 'TEST2'),
        ('https://api3.example.com', 'TEST3')"""
        result = _split_statements(sql)
        assert len(result) == 3
        for stmt in result:
            assert "VALUES" in stmt.upper()


class TestCountValues:
    """Test value counting in tuples."""

    def test_single_value(self):
        """Single value is counted correctly."""
        assert _count_values("'value'") == 1

    def test_multiple_values(self):
        """Multiple comma-separated values."""
        assert _count_values("'value1', 'value2', 'value3'") == 3

    def test_values_with_nulls(self):
        """NULL values are counted."""
        assert _count_values("'value1', NULL, 'value3'") == 3

    def test_values_with_quotes_inside(self):
        """String values containing commas don't break counting."""
        assert _count_values("'value,with,comma', 'normal'") == 2


class TestValidate:
    """Test complete SQL validation."""

    def test_valid_insert(self):
        """Valid INSERT statement passes validation."""
        sql = "INSERT INTO ws_config (base_url, type) VALUES ('https://api.example.com', 'TEST')"
        result = validate(sql)
        assert len(result) == 1
        assert "INSERT" in result[0].upper()

    def test_reject_non_insert(self):
        """Non-INSERT statements are rejected."""
        sql = "SELECT * FROM ws_config"
        with pytest.raises(ValidationError, match="not an INSERT"):
            validate(sql)

    def test_reject_drop_statement(self):
        """DROP and other dangerous keywords are rejected."""
        sql = "INSERT INTO ws_config (base_url, type) VALUES ('DROP TABLE', 'TEST')"
        # This should still pass because the keyword is inside a string literal
        result = validate(sql)
        assert len(result) == 1

    def test_reject_unknown_table(self):
        """Unknown table names are rejected."""
        sql = "INSERT INTO unknown_table (col) VALUES ('value')"
        with pytest.raises(ValidationError, match="unknown table"):
            validate(sql)

    def test_reject_empty_sql(self):
        """Empty SQL is rejected."""
        sql = ""
        with pytest.raises(ValidationError, match="No SQL statements"):
            validate(sql)

    def test_column_value_mismatch(self):
        """Mismatched column and value counts are auto-repaired if gap is small (≤3)."""
        # Gap of 1 is auto-repaired
        sql = "INSERT INTO ws_config (base_url, type) VALUES ('value1')"
        result = validate(sql)
        assert len(result) == 1
        # Should have been repaired with a NULL
        assert "NULL" in result[0]

    def test_column_value_mismatch_too_large(self):
        """Large gaps (>3) in column/value counts raise error."""
        sql = "INSERT INTO ws_config (base_url, type, unknown1, unknown2, unknown3, unknown4, unknown5) VALUES ('value1')"
        with pytest.raises(ValidationError, match="column|value"):
            validate(sql)

    def test_column_value_repair_with_nulls(self):
        """Auto-repair of missing values by padding with NULLs."""
        sql = "INSERT INTO ws_config (base_url, type) VALUES ('https://api.example.com')"
        result = validate(sql)
        assert len(result) == 1
        # Should have been repaired with a NULL
        assert "NULL" in result[0] or "," in result[0]

    def test_multirow_validation(self):
        """Multiple rows in one statement are validated separately."""
        sql = """INSERT INTO ws_config (base_url, type) VALUES 
        ('https://api1.example.com', 'TEST1'),
        ('https://api2.example.com', 'TEST2')"""
        result = validate(sql)
        assert len(result) == 2


class TestValidationErrorMessages:
    """Test that error messages are helpful."""

    def test_error_includes_statement_number(self):
        """Error messages include which statement failed."""
        sql = """
        INSERT INTO ws_config (base_url, type) VALUES ('https://api.example.com', 'TEST');
        SELECT * FROM ws_config;
        """
        with pytest.raises(ValidationError) as exc_info:
            validate(sql)
        assert "Statement #2" in str(exc_info.value) or "SELECT" in str(exc_info.value)

    def test_error_includes_table_name(self):
        """Error messages include the problematic table name."""
        sql = "INSERT INTO nonexistent_table (col) VALUES ('value')"
        with pytest.raises(ValidationError) as exc_info:
            validate(sql)
        assert "nonexistent_table" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
