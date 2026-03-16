# Troubleshooting

Common issues and how to fix them.

## Agent issues

### `GROQ_API_KEY is not set`

```
EnvironmentError: GROQ_API_KEY is not set. Copy .env.example → .env and add your key.
```

**Fix:** Create a `.env` file from the template:

```bash
cp .env.example .env
# Edit .env and add your Groq API key
```

Get a free key at https://console.groq.com

### `Can't connect to MySQL server`

```
mysql.connector.errors.InterfaceError: 2003: Can't connect to MySQL server on 'localhost:3306'
```

**Fix:**

1. Make sure MySQL is running:
   ```bash
   docker compose up -d mysql
   docker compose ps    # should show "healthy"
   ```
2. Check that `.env` has the correct host/port:
   ```
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   ```

### `Validation failed: Statement #1 targets unknown table`

The LLM generated an INSERT for a table that isn't in the whitelist.

**Fix:** If the table is legitimate, add it to `MANAGED_TABLES` in
`agent/schema.py`. See [extending.md](extending.md) for details.

### `LLM returned an empty response`

The Groq API returned no content.

**Possible causes:**

- Temporary API outage — retry
- Model rate limit — wait and retry
- API key quota exceeded — check https://console.groq.com

### Generated SQL looks wrong

If the LLM produces bad SQL (wrong columns, missing values):

1. Check the schema is correct: `python -c "from agent.schema import schema_as_prompt; print(schema_as_prompt())"`
2. Try a different model in `.env`: `LLM_MODEL=mixtral-8x7b-32768`
3. Adjust the system prompt in `agent/prompts.py`

## Docker issues

### `docker compose` fails with "version is obsolete"

This is just a warning and can be safely ignored. The `version` field has been
removed from `docker-compose.yml`.

### Port 3306 already in use

```bash
# Find what's using the port
sudo lsof -i :3306

# Stop the existing MySQL or change the port in docker-compose.yml
```

### Database tables don't exist

If the tables aren't created on startup:

```bash
# Remove the volume and recreate
docker compose down -v
docker compose up -d mysql
```

The `init.sql` only runs on first-time volume creation.

## MCP issues

### MCP server doesn't start

1. Check Node.js version: `node --version` (need ≥ 20)
2. Try running manually:
   ```bash
   MYSQL_HOST=127.0.0.1 MYSQL_PORT=3306 MYSQL_USER=mpay_ai \
   MYSQL_PASS=mpay_ai_password MYSQL_DB=mpay_dev \
   npx -y @benborla29/mcp-server-mysql
   ```
3. Check editor logs for errors

### Editor doesn't detect `.mcp.json`

- **VS Code:** Requires GitHub Copilot Chat extension with MCP support
- **Cursor:** Should auto-detect; try restarting the editor
- **Claude Code:** Run `claude mcp add-from-project`

See [mcp-setup.md](mcp-setup.md) for full setup instructions.
