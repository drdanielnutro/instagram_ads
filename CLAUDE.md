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

Key configurations in `app/.env`:
```bash
GOOGLE_CLOUD_PROJECT=instagram-ads-472021
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
ARTIFACTS_BUCKET=gs://project-facilitador-logs-data  # Optional
LANGEXTRACT_API_KEY=your-gemini-key  # Optional

# Performance tuning for StoryBrand analysis
STORYBRAND_HARD_CHAR_LIMIT=20000
STORYBRAND_SOFT_CHAR_LIMIT=12000
STORYBRAND_TAIL_RATIO=0.2

# Vertex AI retry settings
VERTEX_CONCURRENCY_LIMIT=3
VERTEX_RETRY_MAX_ATTEMPTS=5
VERTEX_RETRY_INITIAL_BACKOFF=1.0
VERTEX_RETRY_MAX_BACKOFF=30.0
```

## Feature Flags

### Available Flags
- `ENABLE_STORYBRAND_FALLBACK`: Enable fallback pipeline when StoryBrand analysis is weak or fails (default: `false`)
- `ENABLE_NEW_INPUT_FIELDS`: Enable experimental input fields (default: `false`)
- `STORYBRAND_GATE_DEBUG`: Force fallback path for testing (default: `false`)
- `ENABLE_IMAGE_GENERATION`: Enable Gemini image generation (default: `true`)
- `PREFLIGHT_SHADOW_MODE`: Extract new fields without including in initial_state (default: `true`)

### Important Notes
**Fallback Activation Logic**: The StoryBrand fallback pipeline only runs when:
1. `ENABLE_STORYBRAND_FALLBACK=true` **AND** `ENABLE_NEW_INPUT_FIELDS=true` (both required)
2. AND one of:
   - `STORYBRAND_GATE_DEBUG=true` (forces fallback)
   - `force_storybrand_fallback=true` in state (set by error handlers)
   - StoryBrand score < `min_storybrand_completeness` (default 0.6)

See [app/agents/storybrand_gate.py:47-75](app/agents/storybrand_gate.py#L47-L75) for gate logic.

### Setting Flags Locally
Flags are loaded from `app/.env` via Makefile export. To modify:
1. Edit `app/.env`
2. Restart with `make dev` (automatically sources and exports vars)
3. Check startup logs for "Feature flags loaded on startup" to confirm values
4. Look for `storybrand_gate_decision` log entry with `fallback_enabled=True`

### Troubleshooting
If flags aren't being loaded:
- Verify `app/.env` exists and contains the flags
- Restart backend completely (kill ports with `make check-and-kill-ports`)
- Check startup logs immediately after `make dev`
- Test with: `uv run python -c "import os; from app.config import config; print(config.enable_storybrand_fallback)"`

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

## Subagent Usage Policy

This section defines **deterministic triggers** for mandatory use of specialized subagents from [.claude/agents/](.claude/agents/). These rules override general tool usage policies when conditions are met.

### Priority Rules

When processing user requests, apply this hierarchy:
1. **Deterministic subagent triggers** (defined below) - HIGHEST priority
2. **Specialized subagents** (when task matches agent description)
3. **General-purpose agents** (for complex multi-step tasks)

### Mandatory Subagent Triggers

#### 1. Plan Validation & Drift Detection
**Subagent**: [plan-code-validator](.claude/agents/plan-code-validator.md)

**MUST USE** when user request contains ANY of these terms:
- Portuguese: "revisar plano", "validar plano", "buscar inconsistências", "identificar inconsistências", "checar plano", "analisar drift", "verificar plano"
- English: "review plan", "validate plan", "find inconsistencies", "identify inconsistencies", "check plan", "analyze drift", "verify plan"

**Required Conditions**:
- Target file MUST have `.md` extension
- File should contain implementation plan (tasks, phases, dependencies, deliverables)

**Invocation**:
```python
Task tool with parameters:
- subagent_type: "plan-code-validator"
- prompt: "Validate the implementation plan in <file_path> against the codebase in <repo_root>"
```

**Examples**:
```markdown
✅ MUST use plan-code-validator:
user: "Revise o plano em docs/refactoring_plan.md"
user: "Validate the plan in docs/api_migration.md for inconsistencies"
user: "Buscar inconsistências no plano docs/feature_implementation.md"

❌ Do NOT use (wrong file type):
user: "Review the code in src/validators.py"
user: "Check the JSON in config/settings.json"
```

**Validation Scope**:
- Dependencies claimed to exist but not found in codebase (P0 blockers)
- Signature mismatches between plan and actual code (P1-P2)
- Missing libraries in requirements.txt (P3-Extended)
- State machine divergences, business rule conflicts

---

### Template for Additional Subagents

To add new deterministic triggers for other subagents in [.claude/agents/](.claude/agents/):

```markdown
#### N. [Subagent Purpose]
**Subagent**: [subagent-name](.claude/agents/subagent-name.md)

**MUST USE** when: [trigger keywords/patterns]

**Required Conditions**:
- [File type requirements]
- [Context requirements]

**Invocation**:
```python
Task tool with parameters:
- subagent_type: "subagent-name"
- prompt: "[specific instruction format]"
```

**Examples**: [concrete use cases]
```

### Available Specialized Subagents

Other subagents available for specialized tasks (add deterministic triggers as needed):

- [contextual-software-engineer](.claude/agents/contextual-software-engineer.md) - Project-specific solutions using context.md
- [solution-validator-expert](.claude/agents/solution-validator-expert.md) - Cross-validate AI solutions against codebase
- [ui-ux-auditor-typescript](.claude/agents/ui-ux-auditor-typescript.md) - Frontend UI/UX improvements
- [implementation-consistency-auditor](.claude/agents/implementation-consistency-auditor.md) - Compare deliverables vs plans
- [mobile-feature-mapper](.claude/agents/mobile-feature-mapper.md) - Mobile feature analysis
- [plan-drift-corrector](.claude/agents/plan-drift-corrector.md) - Apply validated corrections to plans