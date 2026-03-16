# Architecture

How the Mpay AI Integration Agent is structured and why.

## High-level flow

```
 User input (API description)
        │
        ▼
 ┌──────────────┐     ┌───────────────┐
 │ schema.py    │────▶│ prompts.py    │
 │ (discovers   │     │ (builds LLM   │
 │  live schema)│     │  messages)    │
 └──────────────┘     └───────┬───────┘
                              │
                              ▼
                      ┌───────────────┐
                      │ generator.py  │
                      │ (calls Groq   │
                      │  LLM API)     │
                      └───────┬───────┘
                              │ raw SQL
                              ▼
                      ┌───────────────┐
                      │ validator.py  │
                      │ (safety       │
                      │  checks)      │
                      └───────┬───────┘
                              │ validated stmts
                              ▼
                      ┌───────────────┐
                      │ executor.py   │
                      │ (transactional│
                      │  INSERT)      │
                      └───────────────┘
```

## Module reference

### `config.py`

- Reads `.env` using `python-dotenv`
- Exposes three frozen dataclasses: `DBConfig`, `LLMConfig`, `AgentConfig`
- Singleton instances (`db_cfg`, `llm_cfg`, `agent_cfg`) created at import time
- Fails fast if `GROQ_API_KEY` is missing

### `database.py`

- `get_connection()` — creates a new `mysql.connector` connection
- `cursor(commit=False)` — context manager that yields a cursor, handles
  commit/rollback, and closes the connection

### `schema.py`

- `MANAGED_TABLES` — whitelist of tables the agent is allowed to touch
- `discover_schema()` — queries `INFORMATION_SCHEMA.COLUMNS` for each managed
  table and returns structured `TableSchema` objects
- `schema_as_prompt()` — renders the schema as human-readable text for the LLM
- **Key design decision**: the schema is always read live from the database, so
  the LLM prompt can never drift out of sync with the actual column definitions

### `prompts.py`

- `SYSTEM_PROMPT` — strict rules: INSERT-only, follow schema, no markdown
- `GENERATE_SQL_USER` — template with `{schema}` and `{api_description}` slots
- `build_generation_prompt()` — assembles the messages list

### `generator.py`

- `generate_sql()` — orchestrates schema discovery → prompt building → LLM call
- `_clean_response()` — strips markdown fences and SQL comments from the output
- Uses a lazy singleton for the Groq client

### `validator.py`

- `validate()` — multi-layer safety check:
  1. Must be an INSERT statement
  2. Must target a table in `MANAGED_TABLES`
  3. Must not contain dangerous keywords (DROP, DELETE, ALTER, etc.) outside
     string literals
- `_strip_string_literals()` — replaces quoted strings with placeholders before
  keyword scanning to avoid false positives

### `executor.py`

- `execute()` — runs validated statements inside a single transaction
- Returns the total row count
- On any error, the entire transaction is rolled back

### `main.py`

- CLI entry point with `argparse`
- Supports interactive input, `--desc`, and `--file` modes
- Colour-coded output with ANSI escape codes
- Preview/confirm step (skippable with `AUTO_EXECUTE=true`)

## Directory layout

```
mpay-ai-proc/
├── .env.example          # Template for environment variables
├── .env                  # Your local config (git-ignored)
├── .gitignore
├── .mcp.json             # MCP server config for IDE integration
├── Dockerfile            # Agent container image
├── docker-compose.yml    # MySQL + Agent services
├── README.md
├── agent/
│   ├── __init__.py
│   ├── __main__.py       # `python -m agent` entry point
│   ├── config.py         # Environment config
│   ├── database.py       # MySQL connection management
│   ├── schema.py         # Live schema discovery
│   ├── prompts.py        # LLM prompt templates
│   ├── generator.py      # LLM SQL generation
│   ├── validator.py      # SQL safety validation
│   ├── executor.py       # Transactional SQL execution
│   ├── main.py           # CLI application
│   └── requirements.txt  # Python dependencies
├── db/
│   └── init.sql          # Database schema (Docker init)
└── docs/
    ├── getting-started.md
    ├── architecture.md
    ├── mcp-setup.md
    ├── extending.md
    └── configuration.md
```
