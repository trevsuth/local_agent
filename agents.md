# Local Agent Stack (n8n + Ollama + FastMCP)

This repo sets up a completely self-hosted AI agent playground composed of:
- **n8n** – orchestrates workflows and calls into tools/LLMs.
- **Ollama** – runs local LLM models that n8n and the MCP server can call.
- **FastMCP** – exposes a small tool API and inventory DB over HTTP for agent use.
- It’s meant to be easy to run and replicate: everything is containerized and common workflows are wrapped in `just` recipes to keep the developer experience smooth.

## Directory map (what lives where)
- `docker-compose.yml` — boots the three services.
- `Dockerfile.mcp` — builds the FastMCP service image.
- `mcp_app/` — FastMCP server code (tools, services, DB access).
- `setup/` — utilities to create artifacts for the MCP server (DB schema + seed scripts).
- `data/` — SQLite DB files used by FastMCP (e.g., `mcp_demo.sqlite`).
- `docs/` — project docs (add your notes, design decisions, etc.).
- `documents/` — general documents the MCP server can search/index.
- `justfile` — convenience commands (`just up`, `just mcp-smoke`, etc.).

## How to run
1) Start everything: `just up`
2) Check MCP health/tools (needs Docker access): `just mcp-smoke`
3) Tail logs: `just logs`, `just logs-n8n`, `just logs-ollama`

## LLM metadata files
Some components publish LLM-friendly documentation indexes you can point tools at:
- **n8n docs** — community-maintained `n8n-docs-llms.txt` (sitemap-style) at `https://raw.githubusercontent.com/Synaptiv-AI/awesome-n8n/main/n8n-docs-llms.txt`. citeturn2view0
- **FastMCP docs** — official:
  - `llms.txt` (sitemap): `https://gofastmcp.com/llms.txt`
  - `llms-full.txt` (full corpus): `https://gofastmcp.com/llms-full.txt`
  Both URLs are advertised in the FastMCP docs under “LLM-Friendly Docs.” citeturn4search0

> When you add more libraries with `llm.txt` / `llm-full.txt`, list them here with their URLs.

## Notes
- MCP HTTP endpoint is published on `http://localhost:8000/mcp` (transport=http).
- Ollama listens on `http://localhost:11434`; n8n on `http://localhost:5678`.
- Database seeding: `just init-db` (creates/loads `data/mcp_demo.sqlite`).
