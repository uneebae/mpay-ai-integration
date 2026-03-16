# Mpay AI Integration Agent

Automatically configure external API integrations in Mpay's database — describe
an API in plain English and the agent generates, validates, and executes the
required SQL.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  You describe an API (CLI / --file / --desc)                │
│                          ↓                                  │
│  ┌──────────┐   ┌────────────┐   ┌───────────┐             │
│  │ Schema   │ → │ LLM        │ → │ Validator │             │
│  │ Discovery│   │ Generator  │   │           │             │
│  └──────────┘   └────────────┘   └─────┬─────┘             │
│       ↑ reads DB                       │                    │
│       │              ┌─────────────────↓──────┐             │
│  ┌────┴───┐          │  Preview + Confirm     │             │
│  │ MySQL  │ ←────────│  then Execute          │             │
│  └────────┘          └────────────────────────┘             │
└─────────────────────────────────────────────────────────────┘
```

### Module breakdown

| Module         | Responsibility                                       |
| -------------- | ---------------------------------------------------- |
| `config.py`    | Reads `.env`, exposes typed dataclasses              |
| `database.py`  | Connection pool + context-managed cursors            |
| `schema.py`    | Auto-discovers table schemas from INFORMATION_SCHEMA |
| `prompts.py`   | System + user prompt templates (no hardcoded schema) |
| `generator.py` | Calls Groq LLM, cleans response                      |
| `validator.py` | Safety checks: INSERT-only, known tables, no DDL     |
| `executor.py`  | Runs validated SQL in a transaction                  |
| `main.py`      | Interactive CLI entry point                          |

## Quick Start

### 1. Set up environment

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 2a. Run with Docker (recommended)

```bash
docker compose up -d mysql        # start MySQL
docker compose run --rm agent     # interactive agent
```

### 2b. Run locally

```bash
pip install -r agent/requirements.txt
python -m agent                   # interactive
python -m agent --desc "Base URL: https://api.example.com ..."
python -m agent --file api_spec.txt
```

## IDE Integration — MCP MySQL Server

This repo ships a `.mcp.json` that connects the
[`@benborla29/mcp-server-mysql`](https://github.com/benborla/mcp-server-mysql)
MCP server to your IDE (VS Code / Cursor / Claude Code).

This gives your AI assistant **direct read access** to the live Mpay schema, so
it can inspect tables, run SELECT queries, and understand the data while you work.

### Setup

1. Make sure the MySQL container is running (`docker compose up -d mysql`).
2. Install Node.js ≥ 20 on your host.
3. The `.mcp.json` at the project root is auto-detected by compatible editors.

### What you can do with it

- Ask your AI assistant: _"Show me all rows in ws_config"_
- Ask: _"What columns does ws_endpoint_config have?"_
- Ask: _"Write an INSERT for a new SOAP integration"_ — it can read the real
  schema and craft accurate SQL.

## Configuration

| Variable          | Default                   | Description                |
| ----------------- | ------------------------- | -------------------------- |
| `GROQ_API_KEY`    | —                         | **Required.** Groq API key |
| `LLM_MODEL`       | `llama-3.3-70b-versatile` | Model to use               |
| `LLM_TEMPERATURE` | `0`                       | Sampling temperature       |
| `MYSQL_HOST`      | `localhost`               | MySQL host                 |
| `MYSQL_PORT`      | `3306`                    | MySQL port                 |
| `MYSQL_USER`      | `mpay_ai`                 | MySQL user                 |
| `MYSQL_PASSWORD`  | `mpay_ai_password`        | MySQL password             |
| `MYSQL_DATABASE`  | `mpay_dev`                | MySQL database             |
| `AUTO_EXECUTE`    | `false`                   | Skip confirm prompt        |
| `LOG_LEVEL`       | `INFO`                    | Python log level           |

## License

MIT
