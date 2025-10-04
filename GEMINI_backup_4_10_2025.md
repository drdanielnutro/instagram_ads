# GEMINI.md

This document provides a comprehensive guide for interacting with the Instagram Ads Generation System.

## Project Overview

This is a multi-agent system built on the Google Agent Development Kit (ADK) designed to automate the creation of Instagram ad campaigns. It takes user input—such as a landing page URL, campaign objective, and target audience—and generates a complete ad package in JSON format, including ad copy (headlines, body text) and detailed descriptions for visual assets.

The system uses a sequential pipeline of AI agents to process input, analyze web content, plan, and execute the ad creation process.

### High-Level Architecture

1.  **Frontend**: A React+TypeScript application (located in `frontend/`) provides the user interface for submitting ad requests.
2.  **Backend**: A Python backend using the FastAPI framework (in `app/`) orchestrates the agent pipeline.
3.  **Agent Pipeline (ADK)**: The core logic resides in a series of agents defined in `app/agent.py`. Key stages include:
    *   **Preflight**: An initial step (`/run_preflight` endpoint in `app/server.py`) validates user input, analyzes the provided `landing_page_url` using a StoryBrand framework (`app/tools/langextract_sb7.py`), and selects a pre-defined execution plan from `app/plan_models/fixed_plans.py`. This bypasses dynamic planning for efficiency.
    *   **Execution**: Agents execute tasks for strategy, copy drafting, visual drafting, and quality assurance based on the selected plan and format specifications (`app/format_specifications.py`).
    *   **Assembly & Validation**: The final agent assembles the generated content into three distinct ad variations and validates the output against the required JSON schema.
4.  **Persistence**: Final JSON outputs are saved locally to `artifacts/ads_final/` and can be optionally uploaded to a Google Cloud Storage bucket.

### Technology Stack

*   **Backend**: Python, FastAPI, Google ADK, Pydantic
*   **Frontend**: React, TypeScript, Vite, npm
*   **AI Models**: `gemini-2.5-pro` and `gemini-2.5-flash` via Vertex AI
*   **Infrastructure**: Google Cloud Run, Google Cloud Storage, Terraform
*   **Tooling**: `uv` for Python environment, `pytest` for testing, `ruff` & `mypy` for code quality.

## Common Development Commands

The project uses a `Makefile` to streamline common tasks.

### Starting the Development Environment

To start the frontend and backend services with automatic port cleaning:
```bash
make dev
```
- **Backend API**: `http://localhost:8000/docs`
- **Frontend App**: `http://localhost:5173/app/`

For quieter logging:
```bash
make dev-quiet
```

### Running Tests

To run the entire test suite (unit and integration):
```bash
make test
```
To run tests with a coverage report:
```bash
pytest tests/ --cov=app --cov-report=html
```

### Code Quality

To run all linters and format checkers (`ruff`, `mypy`, `codespell`):
```bash
make lint
```

### Deployment

To deploy the backend service to Google Cloud Run:
```bash
make backend
```
To set up the GCP development environment using Terraform:
```bash
make setup-dev-env
```

## Development Conventions

*   **Agent Logic**: The core agent pipeline is defined in `app/agent.py`.
*   **API Endpoints**: The main API, including the critical `/run_preflight` endpoint, is in `app/server.py`.
*   **Fixed Plans**: For consistency and performance, the agent uses fixed execution plans stored in `app/plan_models/fixed_plans.py`.
*   **StoryBrand Analysis**: The `app/tools/langextract_sb7.py` tool is responsible for analyzing landing page content. It has known performance issues, and its behavior can be tuned with environment variables (see `README.md`).
*   **Input/Output**: The system expects specific input fields (`landing_page_url`, `objetivo_final`, etc.) and produces a JSON file with three ad variations.
*   **Dependencies**: Python dependencies are managed with `uv` (`pyproject.toml`, `uv.lock`), and frontend dependencies with `npm` (`package.json`).
