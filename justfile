set dotenv-load := true
set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

container_app := "docker"
compose := container_app + " compose"
DB := "data/mcp_demo.sqlite"
SCHEMA := "setup/schema.sql"

n8n_service := "n8n"
ollama_service := "ollama"

# -------- begin recipes ---------

# -------- lifecycle -------------

default:
	@just --list

# start docker compose
up:
	{{compose}} up -d

# end docker compose (preserve vols)
down:
	{{compose}} down

# end docker compose (remove vols)
down-vols:
	{{compose}} down -v

# restart compose
restart:
	{{compose}} restart

# get processes
ps:
	{{compose}} ps

# pull images
pull:
	{{compose}} pull

# update images
update: pull up
	@echo "Updated images and ensured services are running"

# -------- logs -------------

# get recent logs (all)
logs:
	{{compose}} logs -f --tail=200

# get recent logs (n8n)
logs-n8n:
	{{compose}} logs -f --tail=200 {{n8n_service}}

# get recent logs (ollama)
logs-ollama:
	{{compose}} logs -f --tail=200 {{ollama_service}}

# ---------- shell ---------

# n8n shell
sh-n8n:
	{{compose}} exec {{n8n_service}} sh

# ollama shell
sh-ollama:
	{{compose}} exec {{ollama_service}} sh

# ---------- health / connectivity ----------

# Health Check
check:
	@echo "Checking n8n -> ollama connectivity"
	{{compose}} exec {{n8n_service}} sh -lc 'wget -qO- http://{{ollama_service}}:11434/api/tags >/dev/null && echo "OK: n8n can reach ollama"'

# show models available to ollama
tags:
	{{compose}} exec {{ollama_service}} sh -lc 'curl -fsS http://127.0.0.1:11434/api/tags | sed "s/,/,\n/g"'

# --------- Ollama model managment ----------
# Pull ollama model: `just model-pull llama3.2`
model-pull model:
	{{compose}} exec {{ollama_service}} ollama pull {{model}}

# List ollama models
model-list:
	{{compose}} exec {{ollama_service}} ollama list

# Remove ollama models `just model-rm llama3.2`
model-rm model:
	{{compose}} exec {{ollama_service}} ollama rm {{model}}

# Quick smoke test generation: `just gen llama3.2 "Say Hello"`
gen model prompt="Hello from Ollama":
	{{compose}} exec {{ollama_service}} sh -lc 'ollama run {{model}} "{{prompt}}"'

# ---------- Backups ----------

# Backup both volumes into ./backups with timestamped tarballs
backup:
	mkdir -p backups
	@ts="$$(date +%Y%m%d_%H%M%S)"; \
	echo "Backing up n8n_data -> backups/n8n_data_$$ts.tar.gz"; \
	{{container_app}} run --rm -v n8n_data:/data -v "$$(pwd)/backups:/backups" alpine sh -lc 'cd /data && tar -czf /backups/n8n_data_'"$$ts"'.tar.gz .'; \
	echo "Backing up ollama_data -> backups/ollama_data_$$ts.tar.gz"; \
	{{container_app}} run --rm -v ollama_data:/data -v "$$(pwd)/backups:/backups" alpine sh -lc 'cd /data && tar -czf /backups/ollama_data_'"$$ts"'.tar.gz .'; \
	echo "Done."

# Restore; requires tou ro provide the backup file explicitly: `just restore backups/n8n_data_20260117_221000.tar.gz backups/ollama_data_20260117_221000.tar.gz`
restore n8n_tar ollama_tar:
	@echo "Restoring n8n_data from {{n8n_tar}}"
	{{container_app}} run --rm -v n8n_data:/data -v "$$(pwd):/host" alpine sh -lc 'rm -rf /data/* && cd /data && tar -xzf /host/{{n8n_tar}}'
	@echo "Restoring ollama_data from {{ollama_tar}}"
	{{container_app}} run --rm -v ollama_data:/data -v "$$(pwd):/host" alpine sh -lc 'rm -rf /data/* && cd /data && tar -xzf /host/{{ollama_tar}}'
	@echo "Restore complete. Consider running: just up"

# ---------- Saftey / diagnostics ----------

# Config
config:
	{{compose}} config


# Display ports
ports:
	@echo "Listening ports for containers"
	{{container_app}} ps --format 'table {{ "{{" }}.Names{{ "}}" }}\t{{ "{{" }}.Ports{{ "}}" }}'

# Display who owns port 11434
who-owns-11434:
	@echo "What is listening on :11434 on the host?"
	(ss -ltnp | grep 11434) || echo "Nothing is listening on 11434"

# Display who owns port 5678
who-owns-5678:
	@echo "What is listening on :5678 on the host?"
	(ss -ltnp | grep 5678) || echo "Nothing is listening on 5678"

# ---------- Database functions ----------

# Create sqlite database
init-db:
	mkdir -p data
	rm -f {{DB}}
	uv run setup/create_db.py --db {{DB}} --schema {{SCHEMA}}
	uv run setup/seed_db.py --db {{DB}} --seed

# reseed database
reseed-db:
	python setup/seed_db.py --db {{DB}} --seed

# ---------- MCP Connectivity Checks ----------

# Quick Ping
mcp-ping:
	curl -sf http://localhost:8000/ > /dev/null \
		&& echo "✅ MCP server is reachable" \
		|| (echo "❌ MCP server not reachable" && exit 1)

# tool discovery
mcp-tools:
	curl -s http://localhost:8000/tools | jq . \
		|| (echo "❌ Failed to fetch MCP tools" && exit 1)

# MCP invokation
mcp-quote:
	curl -s http://localhost:8000/tools/quote_inventory_availability \
		-H "Content-Type: application/json" \
		-d '{"lines": [{ "product_id": 1, "quantity": 50 }]}' | jq .

# Compbined MCP test
mcp-smoke:
	@echo "🔍 Checking MCP HTTP endpoint from inside the container..."
	@{{compose}} exec mcp uv run python -c "import httpx, sys; r=httpx.get('http://127.0.0.1:8000/mcp', headers={'Accept':'text/event-stream'}); print('HTTP status', r.status_code); sys.exit(0 if r.status_code < 500 else 1)"
	@echo "🔍 Running availability quote inside MCP container..."
	@{{compose}} exec mcp uv run python -c "from mcp_app.server.main import quote_inventory_availability; print('✅ Quote result:', quote_inventory_availability.__wrapped__([{'product_id':1,'quantity':10}]))"

# All-in-one local setup: verify tools, sync deps, start stack, open n8n
go:
	@# Check required tooling
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "⚠️  uv not found. Install from https://github.com/astral-sh/uv and re-run: just go"; exit 1; \
	fi
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "⚠️  docker CLI not found. Install Docker Desktop/Engine, ensure it's running, then re-run: just go"; exit 1; \
	fi
	@if ! docker compose version >/dev/null 2>&1; then \
		echo "⚠️  docker compose plugin not available. Install Docker Compose (v2+) and re-run: just go"; exit 1; \
	fi
	@echo "👉 Syncing Python deps with uv..."
	@uv sync
	@echo "👉 Starting containers (ollama, mcp, n8n)..."
	@docker compose up -d
	@echo "👉 Opening n8n in your browser (http://localhost:5678)..."
	@python - <<'PY'
import os, webbrowser
url = os.environ.get("N8N_URL", "http://localhost:5678")
try:
    webbrowser.open(url)
    print(f"Opened {url} in the default browser.")
except Exception as e:
    print(f"Please open {url} manually (auto-open failed: {e})")
PY

# Check from inside docker network
mcp-ping-docker:
	docker run --rm --network backend curlimages/curl:8.6.0 \
		curl -sf http://mcp:8000/ \
		&& echo "✅ MCP reachable from Docker network"
