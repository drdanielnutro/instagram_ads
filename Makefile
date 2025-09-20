install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.6.12/install.sh | sh; source $HOME/.local/bin/env; }
	uv sync && npm --prefix frontend install

# Helper function to check and kill processes on specific ports
check-and-kill-ports:
	@echo "🔍 Checking ports 8000 (backend) and 5173 (frontend)..."
	@if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then \
		echo "⚠️  Port 8000 is in use. Killing process..."; \
		lsof -ti:8000 | xargs kill -9 2>/dev/null || true; \
		echo "✅ Port 8000 cleared"; \
	else \
		echo "✅ Port 8000 is free"; \
	fi
	@if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null 2>&1; then \
		echo "⚠️  Port 5173 is in use. Killing process..."; \
		lsof -ti:5173 | xargs kill -9 2>/dev/null || true; \
		echo "✅ Port 5173 cleared"; \
	else \
		echo "✅ Port 5173 is free"; \
	fi
	@echo "🚀 Ports ready for development server"
	@sleep 1

# Main development command: runs all agents and the frontend
dev: check-and-kill-ports
	@export GOOGLE_APPLICATION_CREDENTIALS=$${GOOGLE_APPLICATION_CREDENTIALS:-./sa-key.json}; \
	 echo "Using GOOGLE_APPLICATION_CREDENTIALS=$${GOOGLE_APPLICATION_CREDENTIALS}"; \
	 if [ ! -f "$${GOOGLE_APPLICATION_CREDENTIALS}" ]; then \
	   echo "⚠️  Service account key not found at $${GOOGLE_APPLICATION_CREDENTIALS}. Continuing with ADC credentials (Signed URLs may fail)."; \
	 fi; \
	 make dev-all

# --- Development workflows ---
dev-all:
	@echo "Starting backend with ALL agents and frontend..."
	make dev-backend-all & make dev-frontend

dev-original: check-and-kill-ports
	@echo "Starting backend with ORIGINAL agent (app) and frontend..."
	make dev-backend-original & make dev-frontend

dev-coder: check-and-kill-ports
	@echo "Starting backend with CODER agent (app_coder) and frontend..."
	make dev-backend-coder & make dev-frontend

# --- Helper targets for backends ---
dev-backend-all:
	@echo "Starting backend with uvicorn (app.server:app) to include custom endpoints like /run_preflight"
	@uv run uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload

dev-backend-original:
	@uv run adk api_server app --allow_origins="*"

dev-backend-coder:
	@uv run adk api_server app_coder --allow_origins="*"

dev-frontend:
	@npm --prefix frontend run dev

# --- Quiet/filtered logging helpers ---

# Patterns to filter out high-volume, low-signal lines from backend logs
NOISE_PATTERNS := Generated event in agent run streaming|LLM Request|LLM Response|Raw response|HTTP Request: POST|AFC is enabled|Starting sequential extraction passes|Starting extraction pass|Processing batch|Starting resolver process|Starting string parsing|Completed parsing of string|Starting to extract and order extractions|Completed extraction and ordering of extractions|Starting alignment process|Completed alignment process

# Start backend (ADK API server) and write both raw and filtered logs
dev-backend-all-quiet:
	@mkdir -p logs
	@echo "Starting backend (quiet) with filtered logging (uvicorn app.server:app)..."
	@uv run uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload 2>&1 \
		| tee logs/backend.raw.log \
		| grep -E -v '$(NOISE_PATTERNS)' \
		| tee logs/backend.filtered.log

# Start frontend with reduced log level
dev-frontend-quiet:
	@npm --prefix frontend run dev -- --logLevel warn

# Start both backend (quiet) and frontend (quiet)
dev-quiet:
	@echo "Starting backend (quiet) and waiting for readiness..."
	( make dev-backend-all-quiet & ) ; \
	BACKEND_URL="http://127.0.0.1:8000/docs" ; \
	for i in $$(seq 1 60); do \
	  if curl -sf -o /dev/null $$BACKEND_URL; then \
	    echo "Backend ready (responded 200 at $$BACKEND_URL)." ; \
	    break ; \
	  fi ; \
	  if [ $$i -eq 1 ]; then echo "Waiting for backend to become ready..." ; fi ; \
	  sleep 1 ; \
	  if [ $$i -eq 60 ]; then echo "Timed out waiting for backend (60s)." ; exit 1 ; fi ; \
	done ; \
	make dev-frontend-quiet

# Follow essential signals in real time from raw backend log
logs-follow-essential:
	@mkdir -p logs
	@echo "Following essential backend signals... (Ctrl+C to stop)"
	@tail -f logs/backend.raw.log | grep -E "Fazendo fetch da URL|Conteúdo salvo no estado|Iniciando análise StoryBrand|Usando Vertex AI| 200 OK|WARNING|ERROR|CRITICAL|New session created:"

# Produce slimmed log file (filtering noise from raw log)
logs-slim:
	@mkdir -p logs
	@echo "Generating logs/backend.slim.log (filtered)..."
	@grep -E -v '$(NOISE_PATTERNS)' logs/backend.raw.log > logs/backend.slim.log || true
	@echo "Created logs/backend.slim.log"

# Extract only essential lines to a separate file
logs-essential:
	@mkdir -p logs
	@echo "Generating logs/backend.essential.log (essential signals only)..."
	@grep -E "Iniciando processamento|Fazendo fetch da URL|Conteúdo salvo no estado|Iniciando análise StoryBrand|Usando Vertex AI|LangExtract params|StoryBrand input sizes|Conteúdo truncado|StoryBrand timing| 200 OK|final_assembler|final_validator|WARNING|ERROR|CRITICAL|New session created:" logs/backend.raw.log > logs/backend.essential.log || true
	@echo "Created logs/backend.essential.log"

logs-storybrand:
	@mkdir -p logs
	@echo "Filtering StoryBrand-related timing & params..."
	@grep -E "Iniciando análise StoryBrand|LangExtract params|StoryBrand input sizes|Conteúdo truncado|StoryBrand timing" logs/backend.raw.log > logs/backend.storybrand.log || true
	@echo "Created logs/backend.storybrand.log"

playground:
	uv run adk web --port 8501

lint:
	uv run codespell
	uv run ruff check . --diff
	uv run ruff format . --check --diff
	uv run mypy .

# --- Commands from Agent Starter Pack ---

backend:
	PROJECT_ID=$$(gcloud config get-value project) && \
	gcloud beta run deploy my-project \
		--source . \
		--memory "4Gi" \
		--project $$PROJECT_ID \
		--region "southamerica-east1" \
		--no-allow-unauthenticated \
		--no-cpu-throttling \
		--labels "created-by=adk" \
		--set-env-vars \
		"COMMIT_SHA=$(shell git rev-parse HEAD)" \
		$(if $(IAP),--iap) \
		$(if $(PORT),--port=$(PORT))

local-backend: check-and-kill-ports
	uv run uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload

setup-dev-env:
	PROJECT_ID=$$(gcloud config get-value project) && \
	(cd deployment/terraform/dev && terraform init && terraform apply --var-file vars/env.tfvars --var dev_project_id=$$PROJECT_ID --auto-approve)

test:
	uv run pytest tests/unit && uv run pytest tests/integration
