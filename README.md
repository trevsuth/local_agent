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

## MCP Tools

### health
Simple health check tool (no inputs).

Input:
- No parameters

Returns:
- `status` (string)
- `service` (string)
- `timestamp_utc` (string, ISO8601)
- `env` (string, `MCP_ENV` or `unknown`)

Example response:
```json
{
  "status": "ok",
  "service": "mcp-demo",
  "timestamp_utc": "2026-01-28T12:34:56.789+00:00",
  "env": "local"
}
```

### quote_inventory_availability
Quote whether an order can be fulfilled from current component inventory.

Input parameters:
- `payload` (string, required): JSON string with:
  - `lines` (array, required): list of `{ "product_id": int, "quantity": int }`
  - `handling_days` (number, optional; default 2)
  - `shipping_days` (number, optional; default 5)
- `db_path` (string, optional): override DB path; default uses `data/mcp_demo.sqlite`

Example tool input:
```json
{
  "payload": "{\"lines\":[{\"product_id\":1,\"quantity\":10}],\"handling_days\":2,\"shipping_days\":5}"
}
```

Returns:
- `can_fulfill_now` (boolean)
- `earliest_ship_date` (string, YYYY-MM-DD)
- `estimated_delivery_date` (string, YYYY-MM-DD)
- `bottleneck_components` (array):
  - `component_id` (int)
  - `component_name` (string)
  - `required_qty` (int)
  - `quantity_on_hand` (int)
  - `shortage` (int)
  - `lead_time_days` (int)
  - `available_on` (string, YYYY-MM-DD)
- `explanation` (string)

Example response:
```json
{
  "can_fulfill_now": false,
  "earliest_ship_date": "2026-02-05",
  "estimated_delivery_date": "2026-02-10",
  "bottleneck_components": [
    {
      "component_id": 7,
      "component_name": "Flux Capacitor",
      "required_qty": 10,
      "quantity_on_hand": 2,
      "shortage": 8,
      "lead_time_days": 5,
      "available_on": "2026-02-02"
    }
  ],
  "explanation": "Order is short on Flux Capacitor (need 10, have 2). Lead time is 5 days; earliest ship date is 2026-02-05."
}
```
## Diagrams

- Table relations (Mermaid ER): `docs/db_tables_er.mmd`
- Flowchart (entities/indexes/triggers): `docs/db_flowchart.mmd`

Exports:
- `docs/db_tables_er.svg`
- `docs/db_flowchart.svg`
