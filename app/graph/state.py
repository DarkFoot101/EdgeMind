from typing import TypedDict
 
class EdgeMindState(TypedDict):
    user_query: str
    task_type: str
    selected_model: str
    file_path: str
    result: str