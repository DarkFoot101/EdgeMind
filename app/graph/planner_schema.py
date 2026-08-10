"""
Planner output schema for EdgeMind.
"""

from typing import Literal, Optional
from pydantic import BaseModel

class Task(BaseModel):
    tool: Literal[
        "analyze",
        "edit",
        "debug",
        "deployment",
        "explain",
    ]
    instruction: str = ""
    target_file: Optional[str] = None
    operation: Optional[Literal["modify", "create"]] = "modify"

class Plan(BaseModel):
    tasks: list[Task]