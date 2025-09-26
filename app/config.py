import os
from dataclasses import dataclass

import google.auth

# Projeto adaptado para geração de Anúncios Instagram (JSON) em arquitetura multiagente ADK.

# Seleção de backend: AI Studio (chave de API) ou Vertex AI (projeto GCP)
if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "True").lower() == "false":
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "ai-studio-project")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
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
    enable_image_generation: bool = True
    enable_new_input_fields: bool = False
    enable_storybrand_fallback: bool = False
    preflight_shadow_mode: bool = True

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

    # Image generation (Gemini Image Preview)
    image_generation_timeout: int = 60
    image_generation_max_retries: int = 3
    image_transformation_steps: int = 3
    image_signed_url_ttl: int = 60 * 60 * 24  # 24h
    image_intermediate_prompt_template: str = (
        "Transform this scene to show the immediate positive action: {prompt_intermediario}. "
        "Keep the same person, clothing, environment, framing and lighting. Show determination and focus."  # noqa: E501
    )
    image_aspirational_prompt_template: str = (
        "Show the same person after some time has passed achieving the successful outcome: {prompt_aspiracional}. "
        "Preserve identity and core features while allowing improvements in environment, wardrobe and expression."  # noqa: E501
    )


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

if os.getenv("ENABLE_IMAGE_GENERATION"):
    config.enable_image_generation = os.getenv("ENABLE_IMAGE_GENERATION").lower() == "true"

if os.getenv("ENABLE_NEW_INPUT_FIELDS"):
    config.enable_new_input_fields = (
        os.getenv("ENABLE_NEW_INPUT_FIELDS").lower() == "true"
    )

if os.getenv("ENABLE_STORYBRAND_FALLBACK"):
    config.enable_storybrand_fallback = (
        os.getenv("ENABLE_STORYBRAND_FALLBACK").lower() == "true"
    )

if os.getenv("PREFLIGHT_SHADOW_MODE"):
    config.preflight_shadow_mode = (
        os.getenv("PREFLIGHT_SHADOW_MODE").lower() == "true"
    )

if os.getenv("IMAGE_GENERATION_TIMEOUT"):
    config.image_generation_timeout = int(os.getenv("IMAGE_GENERATION_TIMEOUT"))

if os.getenv("IMAGE_GENERATION_MAX_RETRIES"):
    config.image_generation_max_retries = int(os.getenv("IMAGE_GENERATION_MAX_RETRIES"))

if os.getenv("IMAGE_TRANSFORMATION_STEPS"):
    config.image_transformation_steps = int(os.getenv("IMAGE_TRANSFORMATION_STEPS"))

if os.getenv("IMAGE_SIGNED_URL_TTL"):
    config.image_signed_url_ttl = int(os.getenv("IMAGE_SIGNED_URL_TTL"))

if os.getenv("IMAGE_INTERMEDIATE_PROMPT_TEMPLATE"):
    config.image_intermediate_prompt_template = os.getenv("IMAGE_INTERMEDIATE_PROMPT_TEMPLATE")

if os.getenv("IMAGE_ASPIRATIONAL_PROMPT_TEMPLATE"):
    config.image_aspirational_prompt_template = os.getenv("IMAGE_ASPIRATIONAL_PROMPT_TEMPLATE")
