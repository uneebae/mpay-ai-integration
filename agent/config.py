"""Centralised configuration — reads .env once, validates, and exposes typed settings."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

log = logging.getLogger(__name__)

# Walk up until we find .env (works inside docker or local dev)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

    @classmethod
    def from_env(cls) -> "DBConfig":
        return cls(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "mpay_ai"),
            password=os.getenv("MYSQL_PASSWORD", "mpay_ai_password"),
            database=os.getenv("MYSQL_DATABASE", "mpay_dev"),
        )

    def validate(self) -> None:
        """Validate database configuration."""
        if not self.host:
            raise ValueError("MYSQL_HOST cannot be empty")
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"MYSQL_PORT must be 1-65535, got {self.port}")
        if not self.user:
            raise ValueError("MYSQL_USER cannot be empty")
        if not self.database:
            raise ValueError("MYSQL_DATABASE cannot be empty")
        log.info("✓ Database config validated: %s@%s:%d/%s", self.user, self.host, self.port, self.database)


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    model: str
    temperature: float

    @classmethod
    def from_env(cls) -> "LLMConfig":
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise EnvironmentError(
                "GROQ_API_KEY is not set. Copy .env.example → .env and add your key."
            )
        return cls(
            api_key=api_key,
            model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
        )

    def validate(self) -> None:
        """Validate LLM configuration."""
        if not self.api_key or len(self.api_key) < 10:
            raise ValueError("GROQ_API_KEY appears invalid (too short)")
        if not self.model:
            raise ValueError("LLM_MODEL cannot be empty")
        if self.temperature < 0 or self.temperature > 2:
            raise ValueError(f"LLM_TEMPERATURE must be 0-2, got {self.temperature}")
        log.info("✓ LLM config validated: model=%s, temp=%.1f", self.model, self.temperature)


@dataclass(frozen=True)
class AgentConfig:
    auto_execute: bool
    log_level: str

    @classmethod
    def from_env(cls) -> "AgentConfig":
        return cls(
            auto_execute=os.getenv("AUTO_EXECUTE", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )

    def validate(self) -> None:
        """Validate agent configuration."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}, got {self.log_level}")
        log.info("✓ Agent config validated: auto_execute=%s, log_level=%s", self.auto_execute, self.log_level)


def validate_all() -> None:
    """Validate all configurations at startup."""
    log.info("Validating all configurations…")
    db_cfg.validate()
    llm_cfg.validate()
    agent_cfg.validate()
    log.info("✓ All configurations valid!")


# Singletons — import these directly
db_cfg = DBConfig.from_env()
llm_cfg = LLMConfig.from_env()
agent_cfg = AgentConfig.from_env()

# Validate on module load
validate_all()

