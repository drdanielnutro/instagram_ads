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

"""Type definitions for the Flutter development agent."""

import uuid
from typing import Literal, List, Optional

from google.adk.events.event import Event
from google.genai.types import Content
from pydantic import BaseModel, Field


class Request(BaseModel):
    """Represents the input for a chat request with optional configuration."""

    message: Content
    events: list[Event]
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    model_config = {"extra": "allow"}


class Feedback(BaseModel):
    """Represents feedback for a conversation."""

    score: int | float
    text: str | None = ""
    invocation_id: str
    log_type: Literal["feedback"] = "feedback"
    service_name: Literal["facilitador"] = "facilitador"
    user_id: str = ""


# New models for Flutter development agent

class DocumentSet(BaseModel):
    """Represents the three reference documents needed for feature implementation."""
    
    especificacao_tecnica_da_ui: str = Field(
        description="Technical specification for UI architecture (Riverpod, widgets, etc.)"
    )
    contexto_api: str = Field(
        description="API context documentation with endpoints and data structures"
    )
    fonte_da_verdade_ux: str = Field(
        description="UX source of truth with user flows and design specifications"
    )


class FeatureRequest(BaseModel):
    """Represents a feature implementation request."""
    
    feature_snippet: str = Field(
        description="Description of the feature to implement"
    )
    documents: Optional[DocumentSet] = Field(
        None,
        description="Reference documents (can be provided separately)"
    )
    priority: Literal["low", "medium", "high"] = Field(
        "medium",
        description="Implementation priority"
    )
    estimated_complexity: Optional[Literal["simple", "moderate", "complex"]] = Field(
        None,
        description="Estimated complexity of the feature"
    )


class ImplementationResult(BaseModel):
    """Represents the result of a feature implementation."""
    
    feature_name: str = Field(description="Name of the implemented feature")
    status: Literal["success", "partial", "failed"] = Field(description="Implementation status")
    files_created: List[str] = Field(description="List of files created/modified")
    total_tasks: int = Field(description="Total number of tasks executed")
    completed_tasks: int = Field(description="Number of successfully completed tasks")
    implementation_time: str = Field(description="Estimated time for implementation")
    readme_generated: bool = Field(description="Whether a README was generated")
    code_snippets: List[dict] = Field(description="List of generated code snippets")
    errors: Optional[List[str]] = Field(None, description="Any errors encountered")
    warnings: Optional[List[str]] = Field(None, description="Any warnings or suggestions")


class CodeQualityMetrics(BaseModel):
    """Represents code quality metrics for generated code."""
    
    total_lines: int = Field(description="Total lines of code generated")
    comment_ratio: float = Field(description="Ratio of comments to code")
    cyclomatic_complexity: Optional[float] = Field(None, description="Average cyclomatic complexity")
    test_coverage_estimate: Optional[float] = Field(None, description="Estimated test coverage needed")
    follows_conventions: bool = Field(description="Whether code follows Flutter/Dart conventions")
    performance_optimized: bool = Field(description="Whether code includes performance optimizations")


class FeatureMetadata(BaseModel):
    """Metadata about a feature implementation session."""
    
    session_id: str = Field(description="Unique session identifier")
    feature_id: str = Field(description="Unique feature identifier")
    start_time: str = Field(description="When implementation started")
    end_time: Optional[str] = Field(None, description="When implementation completed")
    user_id: str = Field(description="User who requested the feature")
    total_llm_calls: int = Field(0, description="Total LLM API calls made")
    total_tokens_used: Optional[int] = Field(None, description="Total tokens consumed")
    iteration_count: int = Field(0, description="Number of refinement iterations")