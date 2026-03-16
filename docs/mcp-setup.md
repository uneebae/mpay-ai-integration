# MCP IDE Integration

Use the **Model Context Protocol (MCP)** to give your AI coding assistant direct
access to the Mpay MySQL database — right inside your editor.

## What is MCP?

MCP is an open protocol that lets AI assistants (Claude, Copilot, Cursor, etc.)
call external tools. An MCP _server_ exposes capabilities (like "run a SQL
query") and the AI assistant calls them as needed.

We use [`@benborla29/mcp-server-mysql`](https://github.com/benborla/mcp-server-mysql)
— a community MCP server that exposes MySQL read/write operations.

## What this gives you

With MCP configured, you can ask your AI assistant things like:

- _"Show me all rows in `ws_config`"_
- _"What columns does `ws_endpoint_config` have?"_
- _"Write an INSERT for a new SOAP integration and execute it"_
- _"What's the latest `tran_id` in `ws_req_param_details`?"_

The assistant can read the real schema and data — no guessing.

## Setup

### Prerequisites

| Tool    | Version | Notes                          |
| ------- | ------- | ------------------------------ |
| Node.js | ≥ 20    | Required to run the MCP server |
| MySQL   | Running | `docker compose up -d mysql`   |

### Step 1 — Verify `.mcp.json`

The project root already contains a `.mcp.json`:

```json
{
  "mcpServers": {
    "mpay_mysql": {
      "command": "npx",
      "args": ["-y", "@benborla29/mcp-server-mysql"],
      "env": {
        "MYSQL_HOST": "127.0.0.1",
        "MYSQL_PORT": "3306",
        "MYSQL_USER": "mpay_ai",
        "MYSQL_PASS": "mpay_ai_password",
        "MYSQL_DB": "mpay_dev",
        "ALLOW_INSERT_OPERATION": "true",
        "ALLOW_UPDATE_OPERATION": "false",
        "ALLOW_DELETE_OPERATION": "false"
      }
    }
  }
}
```

This is auto-detected by VS Code (with GitHub Copilot), Cursor, and Claude Code.

### Step 2 — Start MySQL

```bash
docker compose up -d mysql
```

### Step 3 — Open the project in your editor

The MCP server starts automatically when your editor detects `.mcp.json`.

### Step 4 — Test it

Ask your assistant:

> Show me all tables in the mpay_dev database

It should respond with the four Mpay tables and their schemas.

## Security notes

| Setting                  | Value   | Meaning                        |
| ------------------------ | ------- | ------------------------------ |
| `ALLOW_INSERT_OPERATION` | `true`  | AI can run INSERTs             |
| `ALLOW_UPDATE_OPERATION` | `false` | AI cannot UPDATE existing rows |
| `ALLOW_DELETE_OPERATION` | `false` | AI cannot DELETE rows          |

For production databases, set all write flags to `false` and use the AI for
read-only exploration.

## Troubleshooting

### "Cannot find module" error

Make sure Node.js ≥ 20 is installed:

```bash
node --version   # should be v20+
```

### "Server disconnected"

1. Check that MySQL is running: `docker compose ps`
2. Verify credentials match your `.env`
3. Try running the server manually:

```bash
MYSQL_HOST=127.0.0.1 MYSQL_PORT=3306 MYSQL_USER=mpay_ai \
MYSQL_PASS=mpay_ai_password MYSQL_DB=mpay_dev \
npx -y @benborla29/mcp-server-mysql
```

### Editor doesn't detect MCP

- **VS Code**: Requires GitHub Copilot Chat extension
- **Cursor**: Supports MCP natively
- **Claude Code**: Run `claude mcp add-from-project` to import from `.mcp.json`
