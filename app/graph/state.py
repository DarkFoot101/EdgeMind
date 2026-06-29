from typing import TypedDict
 
class EdgeMindState(TypedDict):
    user_query: str
    current_step : str
    current_task: str
    selected_model: str
    file_path: str
    result: str