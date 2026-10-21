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
            "create",
            "modify",
            "refactor",
            "optimize",
            "fix",
            "convert",
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
    target_symbol: Optional[str] = Field(default=None, description="Target function, class, or symbol name")
    start_line: Optional[int] = Field(default=None, description="Target starting line number (1-indexed)")
    end_line: Optional[int] = Field(default=None, description="Target ending line number (1-indexed)")
    scope_type: Optional[str] = Field(default=None, description="Scoping granularity: full_file, line_range, symbol, search_replace")
    search_block: Optional[str] = Field(default=None, description="Search block for search-and-replace")
    replace_block: Optional[str] = Field(default=None, description="Replacement block for search-and-replace")


class Plan(BaseModel):
    tasks: list[Task] = Field(..., description="List of tasks to execute in order")