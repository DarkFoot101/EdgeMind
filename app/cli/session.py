"""
EdgeMind CLI Session

Maintains the interactive shell state.

The session remembers context between prompts
without storing anything permanently.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SessionState:
    # Project information
    project_path: str = str(Path.cwd())
    project_name: str = Path.cwd().name

    # Current context
    active_file: str | None = None
    active_directory: str | None = None
    selected_model: str | None = None

    # Previous interaction
    last_query: str = ""
    last_result: str = ""
    last_plan: list[str] = field(default_factory=list)
    last_edited_file: str | None = None 

    # Runtime
    memory_enabled: bool = True
    conversation_history: list[tuple[str, str]] = field(
        default_factory=list
    )

    def remember(
        self,
        query: str,
        result: str,
        file_path: str | None = None,
        plan: list = None,
        model: str | None = None,
        last_edited_file: str | None = None,
    ):
        self.last_query = query
        self.last_result = result
        if plan is not None:
            self.last_plan = plan
        if model is not None:
            self.selected_model = model
        if last_edited_file is not None:
            self.last_edited_file = last_edited_file
        if file_path:
            self.active_file = file_path
            self.active_directory = str(
                Path(file_path).parent
            )
        self.conversation_history.append((query, result))

    def clear(self):
        self.active_file = None
        self.active_directory = None
        self.selected_model = None
        self.last_query = ""
        self.last_result = ""
        self.last_plan.clear()
        self.last_edited_file = None
        self.conversation_history.clear()