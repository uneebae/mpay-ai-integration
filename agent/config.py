"""Centralised configuration — reads .env once and exposes typed settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

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


# Singletons — import these directly
db_cfg = DBConfig.from_env()
llm_cfg = LLMConfig.from_env()
agent_cfg = AgentConfig.from_env()
