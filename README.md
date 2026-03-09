# Bitquery MCP Server for Solana

MCP (Model Context Protocol) server that answers natural-language questions about Solana on-chain data using Bitquery. Uses OpenAI to turn questions into GraphQL and to format results (e.g. tables, summaries).

Video tutorial: [Building an MCP with Claude for Solana Trade Data](https://youtu.be/q-QL5EGfT5k)

## Prerequisites

* A [Bitquery](http://ide.bitquery.io/) account and [bearer token](https://docs.bitquery.io/docs/authorisation/how-to-generate/).
* An [OpenAI](https://platform.openai.com) API key (used to generate queries and format answers).
* Python 3.x.

## Flow

### Client ↔ server (MCP SSE)

```
Client --> GET /sse --> Server (SSE stream, session_id)
Client --> POST /messages/?session_id=... --> Server (initialize, notifications/initialized, tools/list, tools/call)
Server --> SSE events --> Client (responses)
```

### Single tool: `ask_bitquery(question)`

```
question --> LLM (OpenAI) --> GraphQL query --> Bitquery API --> raw JSON --> LLM (OpenAI) --> formatted answer (table/summary)
```

1. **Question → query:** User question (e.g. "top tokens in solana, share as table") is sent to OpenAI with a system prompt; the model returns a Bitquery GraphQL query.
2. **Query → data:** That query is run against the Bitquery REST API; raw JSON is returned.
3. **Data → answer:** Raw JSON plus the original question are sent to OpenAI again; the model returns a human-friendly answer (markdown table, summary, etc.).

## Setup

1. Clone the repo and install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Copy env and set your keys:

   ```bash
   cp .env.example .env
   # Edit .env: BITQUERY_TOKEN, OPENAI_API_KEY; optionally PORT (default 8000)
   ```

3. Run the server:

   ```bash
   python server.py
   # Listens on http://0.0.0.0:8000 (or PORT from .env)
   ```

4. Test (optional):

   ```bash
   python test_server.py --url http://localhost:8000
   python test_server.py --url http://localhost:8000 --question "top tokens in solana, share as table"
   ```

## Environment variables

| Variable          | Purpose |
|------------------|--------|
| `BITQUERY_TOKEN` | Bitquery API bearer token |
| `OPENAI_API_KEY` | OpenAI API key (query generation + output formatting) |
| `PORT`           | Server port (default 8000) |

## Using with Claude / Cursor

* In Claude (or Cursor) settings, open the **Developer** section and add this MCP server (SSE transport, URL e.g. `http://localhost:8000/sse`).
* In chat, you can invoke the tool with natural language; the server handles "top tokens in solana", "share as table", etc., and returns formatted answers.

## Bitquery data & APIs

* Example queries and data points live in `bitquery_utils.py`.
* More examples and docs: [Bitquery streaming docs](https://github.com/bitquery/streaming-data-platform-docs). Support for multiple chains (Bitcoin, Solana, Tron, EVM) via Telegram or support tickets.

## Project layout

* `server.py` — FastAPI app, MCP SSE transport, `ask_bitquery` tool (LLM → Bitquery → LLM).
* `bitquery_utils.py` — Bitquery REST client and example GraphQL helpers.
* `config.py` — Loads `BITQUERY_TOKEN` from env.
* `test_server.py` — Script to test health, SSE session, and tool call.
