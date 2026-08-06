"""
Planner output schema for EdgeMind.
"""

from typing import Literal
from pydantic import BaseModel
from typing import List

class Task(BaseModel):
    tool: Literal[
        "analyze",
        "edit",
        "debug",
        "deployment",
        "explain",
    ]
    instruction: str = ""

class Plan(BaseModel):
    tasks: list[Task]