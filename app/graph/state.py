"""
TypedDict state definition for EdgeMind V2 LangGraph execution.
"""

from typing import TypedDict, Optional, Any
from app.editing.models import EditResponse


class EdgeMindState(TypedDict):
    user_query: str
    project_path: str
    file_path: str  # active/source file
    source_file: Optional[str]
    target_file: Optional[str]
    modified_file: Optional[str]  # file actually created or modified
    source_language: Optional[str]
    target_language: Optional[str]
    plan: list[dict]
    current_step: int
    current_task: str
    task_instruction: str
    operation: Optional[str]
    selected_model: str
    retry_count: int
    max_retry: int
    result: str
    execution_success: bool
    memory_context: str
    analysis_result: Optional[str]  # captured insights from prior analyze/search/debug steps
    edit_response: Optional[EditResponse]
    discovered_files: list[str]
    review_status: Optional[dict]
    change_summary: Optional[dict]
