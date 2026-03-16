# Configuration Reference

All configuration is via environment variables, read from a `.env` file at the
project root.

## Quick setup

```bash
cp .env.example .env
# Edit .env with your values
```

## Variable reference

### LLM Provider

| Variable          | Required | Default                   | Description                                             |
| ----------------- | -------- | ------------------------- | ------------------------------------------------------- |
| `GROQ_API_KEY`    | **Yes**  | —                         | Your Groq API key (get one at https://console.groq.com) |
| `LLM_MODEL`       | No       | `llama-3.3-70b-versatile` | Groq model identifier                                   |
| `LLM_TEMPERATURE` | No       | `0`                       | Sampling temperature (0 = deterministic)                |

### MySQL Connection

| Variable         | Required | Default            | Description       |
| ---------------- | -------- | ------------------ | ----------------- |
| `MYSQL_HOST`     | No       | `localhost`        | MySQL server host |
| `MYSQL_PORT`     | No       | `3306`             | MySQL server port |
| `MYSQL_USER`     | No       | `mpay_ai`          | MySQL username    |
| `MYSQL_PASSWORD` | No       | `mpay_ai_password` | MySQL password    |
| `MYSQL_DATABASE` | No       | `mpay_dev`         | Database name     |

> **Note:** When running inside Docker Compose, `MYSQL_HOST` is overridden to
> `mysql` (the Docker service name) via `docker-compose.yml`.

### Agent Behaviour

| Variable       | Required | Default | Description                                                |
| -------------- | -------- | ------- | ---------------------------------------------------------- |
| `AUTO_EXECUTE` | No       | `false` | Skip the confirmation prompt and execute immediately       |
| `LOG_LEVEL`    | No       | `INFO`  | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

## Docker Compose environment

The `docker-compose.yml` sets these for the MySQL container:

| Variable              | Value              |
| --------------------- | ------------------ |
| `MYSQL_ROOT_PASSWORD` | `rootpassword`     |
| `MYSQL_DATABASE`      | `mpay_dev`         |
| `MYSQL_USER`          | `mpay_ai`          |
| `MYSQL_PASSWORD`      | `mpay_ai_password` |

These match the defaults in `.env.example` so everything works out of the box.

## MCP server environment

The `.mcp.json` configures the MySQL MCP server for IDE integration. Its
variables are separate from the agent's `.env`:

| Variable                 | Value              | Description              |
| ------------------------ | ------------------ | ------------------------ |
| `MYSQL_HOST`             | `127.0.0.1`        | Host (from host machine) |
| `MYSQL_PORT`             | `3306`             | Port                     |
| `MYSQL_USER`             | `mpay_ai`          | Username                 |
| `MYSQL_PASS`             | `mpay_ai_password` | Password (note: `_PASS`) |
| `MYSQL_DB`               | `mpay_dev`         | Database (note: `_DB`)   |
| `ALLOW_INSERT_OPERATION` | `true`             | Allow AI to run INSERTs  |
| `ALLOW_UPDATE_OPERATION` | `false`            | Block UPDATEs            |
| `ALLOW_DELETE_OPERATION` | `false`            | Block DELETEs            |

> **Security:** For production, set all `ALLOW_*` flags to `false`.

## Example `.env` file

```dotenv
# ── LLM Provider ──────────────────────────────────────────────
GROQ_API_KEY=gsk_your_key_here
LLM_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0

# ── MySQL ─────────────────────────────────────────────────────
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=mpay_ai
MYSQL_PASSWORD=mpay_ai_password
MYSQL_DATABASE=mpay_dev

# ── Agent behaviour ──────────────────────────────────────────
AUTO_EXECUTE=false
LOG_LEVEL=INFO
```
