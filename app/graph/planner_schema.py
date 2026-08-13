"""
Planner output schema for EdgeMind V2.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class Task(BaseModel):
    tool: Optional[
        Literal[
            "analyze",
            "edit",
            "debug",
            "deployment",
            "explain",
            "search",
            "test",
            "verify",
            "translate",
        ]
    ] = Field(default="edit", description="The primary tool to execute")

    operation: Optional[
        Literal[
            "inspect",
            "search",
            "analyze",
            "modify",
            "create",
            "test",
            "verify",
        ]
    ] = Field(default="modify", description="Valid operational mode")

    instruction: str = Field(default="", description="Specific task instruction for execution")
    source_file: Optional[str] = Field(default=None, description="Path to source file if known")
    target_file: Optional[str] = Field(default=None, description="Path to target output file if distinct")
    source_language: Optional[str] = Field(default=None, description="Source programming language")
    target_language: Optional[str] = Field(default=None, description="Target programming language")
    verification_requirements: Optional[str] = Field(default=None, description="Optional verification criteria")


class Plan(BaseModel):
    tasks: list[Task] = Field(..., description="List of tasks to execute in order")