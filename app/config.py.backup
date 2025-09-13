# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from dataclasses import dataclass

import google.auth

# To use AI Studio credentials:
# 1. Create a .env file in the /app directory with:
#    GOOGLE_GENAI_USE_VERTEXAI=FALSE
#    GOOGLE_API_KEY=PASTE_YOUR_ACTUAL_API_KEY_HERE
# 2. This will override the default Vertex AI configuration

# Check if using AI Studio before trying Google Cloud auth
if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "True").lower() == "false":
    # Using AI Studio - no need for Google Cloud project
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "ai-studio-project")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
else:
    # Using Vertex AI - get project from default credentials
    try:
        _, project_id = google.auth.default()
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
    except Exception:
        # If no credentials, use a default
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "default-project")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")


@dataclass
class DevelopmentConfiguration:
    """Configuration for Flutter development agent models and parameters.

    This configuration controls the behavior of the multi-agent system
    for Flutter feature implementation.

    Attributes:
        critic_model (str): Model for evaluation tasks (code review, planning review).
        worker_model (str): Model for generation tasks (code generation, planning).
        max_search_iterations (int): Maximum iterations for web search refinement.
        max_task_iterations (int): Maximum number of tasks per feature implementation.
        max_code_review_iterations (int): Maximum review cycles per code task.
        max_plan_review_iterations (int): Maximum review cycles for implementation plans.
        enable_detailed_logging (bool): Enable verbose logging for debugging.
        enable_readme_generation (bool): Generate README.md for each feature.
        code_style (str): Code style preference ('standard', 'minimal', 'verbose').
    """

    # Model configuration
    critic_model: str = "gemini-2.5-pro"
    worker_model: str = "gemini-2.5-flash"
    
    # Iteration limits
    max_search_iterations: int = 5  # For web search refinement
    max_task_iterations: int = 20  # Maximum tasks per feature
    max_code_review_iterations: int = 3  # Reviews per code task
    max_plan_review_iterations: int = 3  # Reviews for implementation plan
    
    # Feature flags
    enable_detailed_logging: bool = True
    enable_readme_generation: bool = True  # Generate comprehensive documentation
    
    # Code generation preferences
    code_style: str = "standard"  # Options: 'standard', 'minimal', 'verbose'
    
    # Performance tuning
    parallel_task_execution: bool = False  # Future enhancement
    cache_generated_code: bool = True  # Cache snippets for reuse
    
    # Quality thresholds
    min_code_coverage: float = 0.8  # Minimum test coverage target
    max_cyclomatic_complexity: int = 10  # Maximum complexity per method


# Create default configuration instance
config = DevelopmentConfiguration()

# Allow environment variable overrides
if os.getenv("FLUTTER_AGENT_CRITIC_MODEL"):
    config.critic_model = os.getenv("FLUTTER_AGENT_CRITIC_MODEL")

if os.getenv("FLUTTER_AGENT_WORKER_MODEL"):
    config.worker_model = os.getenv("FLUTTER_AGENT_WORKER_MODEL")

if os.getenv("FLUTTER_AGENT_MAX_TASKS"):
    config.max_task_iterations = int(os.getenv("FLUTTER_AGENT_MAX_TASKS"))

if os.getenv("FLUTTER_AGENT_ENABLE_README"):
    config.enable_readme_generation = os.getenv("FLUTTER_AGENT_ENABLE_README").lower() == "true"