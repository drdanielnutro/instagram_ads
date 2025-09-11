install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.6.12/install.sh | sh; source $HOME/.local/bin/env; }
	uv sync && npm --prefix frontend install

# Main development command: runs all agents and the frontend
dev: dev-all

# --- Development workflows ---
dev-all:
	@echo "Starting backend with ALL agents and frontend..."
	make dev-backend-all & make dev-frontend

dev-original:
	@echo "Starting backend with ORIGINAL agent (app) and frontend..."
	make dev-backend-original & make dev-frontend

dev-coder:
	@echo "Starting backend with CODER agent (app_coder) and frontend..."
	make dev-backend-coder & make dev-frontend

# --- Helper targets for backends ---
dev-backend-all:
	@uv run adk api_server --allow_origins="*"

dev-backend-original:
	@uv run adk api_server app --allow_origins="*"

dev-backend-coder:
	@uv run adk api_server app_coder --allow_origins="*"

dev-frontend:
	@npm --prefix frontend run dev

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

local-backend:
	uv run uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload

setup-dev-env:
	PROJECT_ID=$$(gcloud config get-value project) && \
	(cd deployment/terraform/dev && terraform init && terraform apply --var-file vars/env.tfvars --var dev_project_id=$$PROJECT_ID --auto-approve)

test:
	uv run pytest tests/unit && uv run pytest tests/integration

