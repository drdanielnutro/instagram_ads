# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Instagram Ads generation system based on Google ADK (Agent Development Kit) that automates the creation of ad content (text and images) in JSON format for Instagram campaigns.

## Common Development Commands

### Starting Development Environment
```bash
# Main development command - auto-kills ports and starts all services
make dev

# Alternative: Start with quieter logging
make dev-quiet

# Start backend only (includes /run_preflight endpoint)
make dev-backend-all

# Start frontend only
make dev-frontend
```

### Running Tests
```bash
# Run all tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=app --cov-report=html

# Run specific test categories
pytest tests/unit
pytest tests/integration
```

### Code Quality
```bash
# Run all linters
make lint

# Individual linting commands
uv run ruff check . --diff
uv run ruff format . --check --diff
uv run mypy .
uv run codespell
```

### Deployment
```bash
# Deploy to Google Cloud Run
make backend

# Setup development environment in GCP
make setup-dev-env
```

## High-Level Architecture

### Multi-Agent Pipeline
The system uses sequential ADK agents organized in a pipeline:
```
input_processor → landing_page_analyzer → planning_pipeline → execution_pipeline → final_assembly → validation
```

### Key Components

1. **Preflight System** (`/run_preflight` endpoint)
   - Validates and normalizes user input before ADK processing
   - Selects fixed plans based on ad format (Reels/Stories/Feed)
   - Returns initial state with implementation plan
   - Located in `app/server.py:93-166`

2. **Landing Page Analysis**
   - Uses `web_fetch_tool` to extract HTML content
   - Performs StoryBrand analysis via LangExtract/Vertex AI
   - Extracts 7 StoryBrand elements for ad context
   - Implementation in `app/callbacks/landing_page_callbacks.py`

3. **Plan Execution**
   - Fixed plans per format stored in `app/plan_models/fixed_plans.py`
   - Format specifications in `app/format_specifications.py`
   - 8 task categories: STRATEGY, RESEARCH, COPY_DRAFT, VISUAL_DRAFT, etc.
   - Each task generates JSON fragments that are assembled

4. **Persistence**
   - Local: `artifacts/ads_final/<timestamp>_<session>_<formato>.json`
   - GCS: Optional upload to `gs://<bucket>/ads/final/`
   - Handled by `app/callbacks/persist_outputs.py`

### Critical Files

- **Main agent**: `app/agent.py` - Complete pipeline definition (881 lines)
- **Server**: `app/server.py` - FastAPI endpoints including preflight
- **LangExtract**: `app/tools/langextract_sb7.py` - StoryBrand analysis
- **Fixed Plans**: `app/plan_models/fixed_plans.py` - Pre-defined execution plans
- **Format Specs**: `app/format_specifications.py` - Instagram format rules

### Frontend Architecture

- React + TypeScript + Vite
- Located in `frontend/` directory
- Main components:
  - `App.tsx` - Main application component
  - `InputForm.tsx` - User input handling
  - `ChatMessagesView.tsx` - Message display
  - UI components in `components/ui/`

## Input Format

Required fields:
- `landing_page_url`: Target page URL
- `objetivo_final`: Campaign goal (e.g., agendamentos, leads)
- `perfil_cliente`: Target audience persona
- `formato_anuncio`: "Reels", "Stories", or "Feed"

Optional field:
- `foco`: Campaign theme or hook

## Environment Variables

Key configurations in `.env`:
```bash
GOOGLE_CLOUD_PROJECT=instagram-ads-472021
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
ARTIFACTS_BUCKET=gs://project-facilitador-logs-data  # Optional
LANGEXTRACT_API_KEY=your-gemini-key  # Optional

# Performance tuning for StoryBrand analysis
STORYBRAND_TRUNCATE_LIMIT_CHARS=12000  # 0 disables, 8-12k recommended
STORYBRAND_EXTRACTION_PASSES=1
STORYBRAND_MAX_WORKERS=4
STORYBRAND_MAX_CHAR_BUFFER=1500
```

## Current Issues & Solutions

### StoryBrand Analysis Performance
If experiencing latency with landing page analysis:
1. Adjust environment variables (see above)
2. Check logs: `make logs-storybrand`
3. Monitor timing metrics in logs

### Port Conflicts
The Makefile automatically kills processes on ports 8000 and 5173 before starting.

## API Endpoints

- `POST /run_preflight` - Validate input and get initial state
- `POST /run` - Execute agent synchronously
- `POST /run_sse` - Execute with Server-Sent Events streaming
- `POST /apps/{app_name}/users/{user_id}/sessions/{session_id}` - Create session
- `POST /feedback` - Submit feedback

## Access Points

- Frontend: http://localhost:5173/app/
- Backend API: http://localhost:8000/docs

## Models Used

- Worker agents: `gemini-2.5-flash`
- Critic agents: `gemini-2.5-pro`
- LangExtract: `gemini-2.5-flash` (via Vertex AI)