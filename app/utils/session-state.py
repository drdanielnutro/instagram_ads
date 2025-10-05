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

"""Strongly typed session state models for the Flutter development agent."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TaskInfo(BaseModel):
    """Information about a single implementation task."""
    
    id: str = Field(description="Unique task identifier (e.g., TASK-001)")
    category: str = Field(description="Task category: MODEL, PROVIDER, WIDGET, SERVICE, UTIL")
    title: str = Field(description="Short descriptive title")
    description: str = Field(description="Detailed description of what to implement")
    file_path: str = Field(description="Path where the code should be created/modified")
    action: str = Field(description="Action type: CREATE, MODIFY, EXTEND")
    dependencies: List[str] = Field(default_factory=list, description="List of task IDs this depends on")


class CodeSnippet(BaseModel):
    """Represents an approved code snippet."""

    task_id: str = Field(description="ID of the task this code implements")
    category: Optional[str] = Field(None, description="Task category at approval time")
    snippet_type: Optional[str] = Field(None, description="Logical snippet type (e.g., VISUAL_DRAFT)")
    status: Optional[str] = Field(None, description="Approval status for the snippet")
    approved_at: Optional[str] = Field(None, description="UTC timestamp when the snippet was approved")
    snippet_id: Optional[str] = Field(None, description="Stable identifier derived from the snippet content")
    task_description: str = Field(description="Description of what was implemented")
    file_path: str = Field(description="File path for this code")
    code: str = Field(description="The actual code content")

    model_config = ConfigDict(extra="allow")


class ImplementationPlan(BaseModel):
    """Complete implementation plan for a feature."""
    
    feature_name: str = Field(description="Name of the feature being implemented")
    estimated_time: str = Field(description="Estimated implementation time")
    implementation_tasks: List[TaskInfo] = Field(description="Ordered list of tasks to implement")


class SessionState(BaseModel):
    """Strongly typed session state for the Flutter development agent."""
    
    # Document references
    especificacao_tecnica_da_ui: Optional[str] = Field(None, description="Technical UI specification")
    contexto_api: Optional[str] = Field(None, description="API context documentation")
    fonte_da_verdade_ux: Optional[str] = Field(None, description="UX truth source")
    
    # Current feature context
    feature_snippet: Optional[str] = Field(None, description="Current feature being implemented")
    feature_briefing: Optional[str] = Field(None, description="Synthesized briefing for the feature")
    
    # Implementation plan
    implementation_plan: Optional[ImplementationPlan] = Field(None, description="Current implementation plan")
    implementation_tasks: List[TaskInfo] = Field(default_factory=list, description="Tasks from the plan")
    
    # Execution state
    current_task_index: int = Field(0, description="Index of current task being processed")
    current_task_info: Optional[TaskInfo] = Field(None, description="Current task being implemented")
    current_task_description: Optional[str] = Field(None, description="Description for code generator")
    
    # Code generation
    generated_code: Optional[str] = Field(None, description="Most recently generated code")
    code_review_result: Optional[Dict[str, Any]] = Field(None, description="Latest code review result")
    approved_code_snippets: List[CodeSnippet] = Field(default_factory=list, description="All approved code")
    approved_visual_drafts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Cached VISUAL_DRAFT snippets approved for deterministic validation",
    )
    
    # Pipeline states
    plan_review_result: Optional[Dict[str, Any]] = Field(None, description="Plan review feedback")
    orchestration_result: Optional[str] = Field(None, description="Final orchestration result")
    
    # Final outputs
    final_code_delivery: Optional[str] = Field(None, description="Final assembled code delivery")
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "allow"  # Allow extra fields for backward compatibility


# Helper functions for safe state access
def get_session_state(state_dict: Dict[str, Any]) -> SessionState:
    """Convert a dictionary state to typed SessionState."""
    return SessionState(**state_dict)


def update_session_state(
    state_dict: Dict[str, Any], 
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """Update session state with validation."""
    session_state = get_session_state(state_dict)
    
    for key, value in updates.items():
        if hasattr(session_state, key):
            setattr(session_state, key, value)
    
    return session_state.model_dump()


def get_current_task(state_dict: Dict[str, Any]) -> Optional[TaskInfo]:
    """Get the current task being processed."""
    session_state = get_session_state(state_dict)
    
    if (session_state.implementation_tasks and 
        session_state.current_task_index < len(session_state.implementation_tasks)):
        return session_state.implementation_tasks[session_state.current_task_index]
    
    return None


def add_approved_snippet(
    state_dict: Dict[str, Any],
    task_id: str,
    task_description: str,
    file_path: str,
    code: str,
    *,
    category: Optional[str] = None,
    snippet_type: Optional[str] = None,
    status: Optional[str] = None,
    approved_at: Optional[str] = None,
    snippet_id: Optional[str] = None,
    **extras: Any,
) -> Dict[str, Any]:
    """Add an approved code snippet to the state while preserving metadata."""

    session_state = get_session_state(state_dict)

    snippet_data = {
        "task_id": task_id,
        "category": category,
        "snippet_type": snippet_type,
        "status": status,
        "approved_at": approved_at,
        "snippet_id": snippet_id,
        "task_description": task_description,
        "file_path": file_path,
        "code": code,
    }
    snippet_data.update(extras)

    snippet = CodeSnippet(**snippet_data)
    session_state.approved_code_snippets.append(snippet)

    if snippet.snippet_type == "VISUAL_DRAFT" and snippet.status == "approved":
        visual_draft_entry = {
            "snippet_id": snippet.snippet_id,
            "task_id": snippet.task_id,
            "approved_at": snippet.approved_at,
            "code": snippet.code,
            "status": snippet.status,
            "snippet_type": snippet.snippet_type,
        }
        session_state.approved_visual_drafts.append(visual_draft_entry)

    return session_state.model_dump()

