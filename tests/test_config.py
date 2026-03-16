"""Unit tests for configuration validation."""

import os
import pytest

from agent.config import DBConfig, LLMConfig, AgentConfig


class TestDBConfig:
    """Test database configuration validation."""

    def test_valid_config(self):
        """Valid database config passes validation."""
        config = DBConfig(
            host="localhost",
            port=3306,
            user="test_user",
            password="test_pass",
            database="test_db"
        )
        config.validate()  # Should not raise

    def test_invalid_port_too_low(self):
        """Port below 1 is rejected."""
        config = DBConfig(
            host="localhost",
            port=0,
            user="test_user",
            password="test_pass",
            database="test_db"
        )
        with pytest.raises(ValueError, match="MYSQL_PORT"):
            config.validate()

    def test_invalid_port_too_high(self):
        """Port above 65535 is rejected."""
        config = DBConfig(
            host="localhost",
            port=70000,
            user="test_user",
            password="test_pass",
            database="test_db"
        )
        with pytest.raises(ValueError, match="MYSQL_PORT"):
            config.validate()

    def test_empty_host(self):
        """Empty host is rejected."""
        config = DBConfig(
            host="",
            port=3306,
            user="test_user",
            password="test_pass",
            database="test_db"
        )
        with pytest.raises(ValueError, match="MYSQL_HOST"):
            config.validate()

    def test_empty_database(self):
        """Empty database name is rejected."""
        config = DBConfig(
            host="localhost",
            port=3306,
            user="test_user",
            password="test_pass",
            database=""
        )
        with pytest.raises(ValueError, match="MYSQL_DATABASE"):
            config.validate()


class TestLLMConfig:
    """Test LLM configuration validation."""

    def test_valid_config(self):
        """Valid LLM config passes validation."""
        config = LLMConfig(
            api_key="gsk_1234567890abcdefghij",
            model="llama-3.3-70b-versatile",
            temperature=0.5
        )
        config.validate()  # Should not raise

    def test_invalid_api_key_too_short(self):
        """API key that's too short is rejected."""
        config = LLMConfig(
            api_key="short",
            model="llama-3.3-70b-versatile",
            temperature=0.5
        )
        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            config.validate()

    def test_invalid_temperature_negative(self):
        """Negative temperature is rejected."""
        config = LLMConfig(
            api_key="gsk_1234567890abcdefghij",
            model="llama-3.3-70b-versatile",
            temperature=-0.5
        )
        with pytest.raises(ValueError, match="LLM_TEMPERATURE"):
            config.validate()

    def test_invalid_temperature_too_high(self):
        """Temperature above 2.0 is rejected."""
        config = LLMConfig(
            api_key="gsk_1234567890abcdefghij",
            model="llama-3.3-70b-versatile",
            temperature=3.0
        )
        with pytest.raises(ValueError, match="LLM_TEMPERATURE"):
            config.validate()

    def test_valid_temperature_boundaries(self):
        """Boundary values for temperature are valid."""
        for temp in [0.0, 1.0, 2.0]:
            config = LLMConfig(
                api_key="gsk_1234567890abcdefghij",
                model="llama-3.3-70b-versatile",
                temperature=temp
            )
            config.validate()  # Should not raise


class TestAgentConfig:
    """Test agent configuration validation."""

    def test_valid_config_lowercase(self):
        """Valid agent config with lowercase log level."""
        config = AgentConfig(auto_execute=False, log_level="INFO")
        config.validate()  # Should not raise

    def test_valid_config_all_levels(self):
        """All standard log levels are valid."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = AgentConfig(auto_execute=False, log_level=level)
            config.validate()  # Should not raise

    def test_invalid_log_level(self):
        """Invalid log level is rejected."""
        config = AgentConfig(auto_execute=False, log_level="INVALID")
        with pytest.raises(ValueError, match="LOG_LEVEL"):
            config.validate()

    def test_auto_execute_boolean_values(self):
        """Both auto_execute values are valid."""
        for value in [True, False]:
            config = AgentConfig(auto_execute=value, log_level="INFO")
            config.validate()  # Should not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
