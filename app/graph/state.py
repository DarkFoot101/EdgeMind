from typing import TypedDict
from app.editing.models import EditResponse

class EdgeMindState(TypedDict):
    user_query: str
    project_path: str
    file_path: str
    plan: list[str]
    current_step: int
    current_task: str
    task_instruction: str
    selected_model: str
    retry_count : int
    max_retry : int 
    result: str
    execution_success: bool
    memory_context: str
    edit_response: EditResponse | None
    modified_file: str | None
    target_file: str | None
    operation: str | None
