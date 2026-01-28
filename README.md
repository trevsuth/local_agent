## Setup Steps

### Prereqs
- `uv` (Python project manager)
- `docker` + `docker compose` (or compatible alternative)
- `just`

If you use Podman or another Docker alternative, update the container command in `.env` and `justfile`.

### Quick start (recommended)
1. Clone the repo
2. Run:
   ```bash
   just go
   ```
3. Open n8n: `http://127.0.0.1:5678`

### Manual setup
1. Create the sample database:
   ```bash
   just init-db
   ```
2. Start containers:
   ```bash
   just up
   ```
3. Pull an Ollama model:
   ```bash
   just model-pull qwen2.5:3b
   ```
4. Open n8n: `http://127.0.0.1:5678`

### Useful endpoints (inside Docker network)
- Ollama: `http://ollama:11434`
- MCP server: `http://mcp:8000/mcp`

### Quick checks
- `just check` (n8n → Ollama connectivity)
- `just mcp-ping` (MCP HTTP health)

### Troubleshooting
- Port 5678 busy: `just who-owns-5678`
- Port 11434 busy: `just who-owns-11434`
- Inspect running containers: `just ps`
- View logs: `just logs`, `just logs-n8n`, `just logs-ollama`

### Reset data
- Recreate and reseed DB: `just init-db`
- Reseed only: `just reseed-db`

## Observability

This stack includes OpenTelemetry Collector, Prometheus, Loki, Tempo, and Grafana. Promtail ships container logs to Loki with container name labels; the collector handles OTLP metrics/traces.

Services (host ports):
- OTel Collector (OTLP gRPC/HTTP): `http://localhost:4317` / `http://localhost:4318`
- Prometheus UI: `http://localhost:9090`
- Loki API: `http://localhost:3100`
- Tempo (traces): `http://localhost:3200`
- Grafana UI: `http://localhost:3000` (default `admin` / `admin`)
- Promtail (logs shipper): `http://localhost:9080`

Observability recipes:
- `just obs-up` / `just obs-down`
- `just obs-logs`
- `just obs-urls`
- `just obs-open` (Grafana)

MCP tracing:
- Traces are exported via OTLP/HTTP to the collector.
- Env overrides: `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`

## MCP Tools

Tool docs: `docs/tools.md`
## Diagrams

- Table relations (Mermaid ER): `docs/db_tables_er.mmd`
- Flowchart (entities/indexes/triggers): `docs/db_flowchart.mmd`

Exports:
- `docs/db_tables_er.svg`
- `docs/db_flowchart.svg`
