# Local Agent Stack (n8n + Ollama + FastMCP)

This repo sets up a completely self-hosted AI agent playground composed of:
- **n8n** – orchestrates workflows and calls into tools/LLMs.
- **Ollama** – runs local LLM models that n8n and the MCP server can call.
- **FastMCP** – exposes a small tool API and inventory DB over HTTP for agent use.
- **Observability stack** – Prometheus, Loki, Tempo, Grafana, OTel Collector, Promtail.
- It’s meant to be easy to run and replicate: everything is containerized and common workflows are wrapped in `just` recipes to keep the developer experience smooth.

## Directory map (what lives where)
- `docker-compose.yml` — boots the stack.
- `Dockerfile.mcp` — builds the FastMCP service image.
- `mcp_app/` — FastMCP server code (tools, services, DB access).
- `setup/` — utilities to create artifacts for the MCP server (DB schema + seed scripts).
- `setup/observability/` — configs for OTel Collector, Loki, Tempo, Prometheus, Promtail, Grafana.
- `data/` — SQLite DB files used by FastMCP (e.g., `mcp_demo.sqlite`).
- `docs/` — project docs + Mermaid diagrams.
- `docs/tools.md` — MCP tool reference.
- `documents/` — general documents the MCP server can search/index.
- `justfile` — convenience commands (`just up`, `just mcp-smoke`, etc.).

## How to run
1) Start everything: `just up` (or `just go`)
2) Start observability: `just obs-up`
3) Check MCP health/tools (needs Docker access): `just mcp-smoke`
4) Tail logs: `just logs`, `just logs-n8n`, `just logs-ollama`, `just obs-logs`

## Observability notes
- MCP traces export via OTLP/HTTP → OTel Collector → Tempo.
- Container logs ship via Promtail → Loki (labels include container/service name).
- Prometheus scrapes OTel Collector metrics endpoint.

## Notes
- MCP HTTP endpoint (host): `http://localhost:8000/mcp`
- Ollama (host): `http://localhost:11434`
- n8n (host): `http://localhost:5678`
- Grafana (host): `http://localhost:3000`
- Prometheus (host): `http://localhost:9090`
- Loki (host): `http://localhost:3100`
- Tempo (host): `http://localhost:3200`
- OTel Collector (host): `http://localhost:4317` (gRPC), `http://localhost:4318` (HTTP)
- Inside Docker network use service names (e.g., `http://mcp:8000`, `http://ollama:11434`).
- Database seeding: `just init-db` (creates/loads `data/mcp_demo.sqlite`).
