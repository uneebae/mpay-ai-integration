# Extending the Agent

How to add new tables, customise prompts, or change LLM behaviour.

## Adding a new managed table

If you add a new table to Mpay's schema (e.g. `ws_auth_config`), the agent
needs to know about it.

### Step 1 — Add the table to the database

Add the `CREATE TABLE` to `db/init.sql`:

```sql
CREATE TABLE ws_auth_config (
  id INT AUTO_INCREMENT PRIMARY KEY,
  config_id INT,
  auth_type VARCHAR(50),
  auth_url VARCHAR(255),
  auth_params TEXT
);
```

### Step 2 — Register it in the agent

Open `agent/schema.py` and add the table name to the whitelist:

```python
MANAGED_TABLES = [
    "ws_config",
    "ws_req_param_details",
    "ws_req_param_map",
    "ws_endpoint_config",
    "ws_auth_config",          # ← add here
]
```

That's it. The agent will:

1. **Auto-discover** the new table's columns from `INFORMATION_SCHEMA`
2. **Include it** in the LLM prompt
3. **Allow INSERTs** targeting it
4. **Reject** INSERTs to any table _not_ in the list

### Step 3 — Recreate the database (if needed)

```bash
docker compose down -v         # removes the volume
docker compose up -d mysql     # recreates from init.sql
```

## Customising prompts

All prompts live in `agent/prompts.py`.

### System prompt

The `SYSTEM_PROMPT` defines the LLM's behaviour. You might want to:

- Add domain-specific rules (e.g. "always set `guaranteed = 1` for payment APIs")
- Restrict which columns should use default values
- Change the `tran_id` starting range

### User prompt

The `GENERATE_SQL_USER` template has two slots:

- `{schema}` — auto-filled by `schema.py`
- `{api_description}` — the user's input

You can add extra context here, like example INSERTs for the LLM to follow.

## Changing the LLM model

Edit `.env`:

```dotenv
LLM_MODEL=llama-3.3-70b-versatile   # default
LLM_TEMPERATURE=0                    # deterministic
```

Supported models depend on Groq's API. As of 2026, good options include:

| Model                     | Speed   | Quality | Notes       |
| ------------------------- | ------- | ------- | ----------- |
| `llama-3.3-70b-versatile` | Fast    | High    | Default     |
| `llama-3.1-8b-instant`    | Fastest | Medium  | For testing |
| `mixtral-8x7b-32768`      | Fast    | High    | Good at SQL |

## Switching to a different LLM provider

The agent uses the Groq client, but you can swap it out:

1. Replace the `groq` import in `agent/generator.py` with your provider's SDK
   (e.g. `openai`, `anthropic`)
2. Update `agent/config.py` to read the new API key
3. Update `agent/requirements.txt`

The prompt format (`messages` list with `role` / `content`) is standard OpenAI
format — most providers support it.

## Adding pre/post-processing hooks

If you need to run logic before or after SQL execution (e.g. audit logging,
Slack notifications), edit `agent/main.py`:

```python
def run(api_description: str) -> None:
    # ... existing generate/validate steps ...

    # Add your hook
    log_to_audit_table(api_description, statements)

    rows = execute(statements)

    # Post-execution hook
    notify_slack(f"New API configured: {rows} rows inserted")
```
