# Getting Started

A step-by-step guide to get the Mpay AI Integration Agent running on your
machine in under 5 minutes.

## Prerequisites

| Tool     | Version | Why                                   |
| -------- | ------- | ------------------------------------- |
| Docker   | ≥ 24    | Runs MySQL (and optionally the agent) |
| Python   | ≥ 3.10  | Runs the agent locally                |
| Node.js  | ≥ 20    | Only for MCP IDE integration          |
| Groq key | —       | Free at https://console.groq.com      |

## 1 — Clone & configure

```bash
git clone <your-repo-url> mpay-ai-proc
cd mpay-ai-proc

cp .env.example .env
# Open .env and paste your GROQ_API_KEY
```

## 2 — Start the database

```bash
docker compose up -d mysql
```

Wait a few seconds for MySQL to become healthy:

```bash
docker compose ps          # STATUS should show "healthy"
```

## 3 — Run the agent

### Option A: Locally (recommended for development)

```bash
pip install -r agent/requirements.txt
python -m agent
```

You'll see an interactive prompt:

```
Describe the external API to integrate into Mpay.
(Enter a blank line when done)

> Base URL: https://api.example.com
> Endpoint: /v1/payment
> Method: POST
> Parameters: amount (required), account_number (required)
> Request format: JSON_POST
> Response format: JSON
>
```

The agent will generate SQL, show a preview, and ask for confirmation before
executing.

### Option B: One-shot from CLI

```bash
python -m agent --desc "Base URL: https://api.example.com, Endpoint: /pay, Method: POST"
```

### Option C: From a file

```bash
python -m agent --file api_spec.txt
```

### Option D: Docker

```bash
docker compose run --rm agent
```

## 4 — Verify

Connect to MySQL and check the data:

```bash
docker compose exec mysql mysql -umpay_ai -pmpay_ai_password mpay_dev \
  -e "SELECT * FROM ws_config;"
```

## Next steps

- [Architecture guide](architecture.md) — understand the module structure
- [MCP IDE Integration](mcp-setup.md) — let your AI assistant query the DB
- [Adding new tables](extending.md) — extend the agent for new Mpay tables
