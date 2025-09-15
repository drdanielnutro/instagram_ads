import os
from dataclasses import dataclass

import google.auth

# Projeto adaptado para geração de Anúncios Instagram (JSON) em arquitetura multiagente ADK.

# Seleção de backend: AI Studio (chave de API) ou Vertex AI (projeto GCP)
if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "True").lower() == "false":
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "ai-studio-project")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
else:
    try:
        _, project_id = google.auth.default()
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
    except Exception:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "default-project")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")


@dataclass
class DevelopmentConfiguration:
    """Configuration for agent models and parameters."""
    critic_model: str = "gemini-2.5-pro"
    worker_model: str = "gemini-2.5-flash"

    # Iteration limits
    max_search_iterations: int = 5
    max_task_iterations: int = 20
    max_code_review_iterations: int = 3  # Modo fixo: loops concisos
    max_plan_review_iterations: int = 1  # Planejamento será bypass quando plano fixo existir

    # Flags
    enable_detailed_logging: bool = True
    enable_readme_generation: bool = False  # não aplicável a Ads

    # Preferences
    code_style: str = "standard"
    parallel_task_execution: bool = False
    cache_generated_code: bool = True

    # Legacy (sem uso direto em Ads, mantido por compatibilidade)
    min_code_coverage: float = 0.8
    max_cyclomatic_complexity: int = 10

    # Landing Page Analysis com StoryBrand
    max_web_fetch_retries: int = 3
    enable_landing_page_analysis: bool = True
    enable_storybrand_analysis: bool = True
    web_fetch_timeout: int = 30
    cache_landing_pages: bool = True
    min_storybrand_completeness: float = 0.6


config = DevelopmentConfiguration()

# Overrides via env vars (mantidos para compatibilidade)
if os.getenv("FLUTTER_AGENT_CRITIC_MODEL"):
    config.critic_model = os.getenv("FLUTTER_AGENT_CRITIC_MODEL")

if os.getenv("FLUTTER_AGENT_WORKER_MODEL"):
    config.worker_model = os.getenv("FLUTTER_AGENT_WORKER_MODEL")

if os.getenv("FLUTTER_AGENT_MAX_TASKS"):
    config.max_task_iterations = int(os.getenv("FLUTTER_AGENT_MAX_TASKS"))

if os.getenv("FLUTTER_AGENT_ENABLE_README"):
    config.enable_readme_generation = os.getenv("FLUTTER_AGENT_ENABLE_README").lower() == "true"
