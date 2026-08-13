"""
EdgeMind CLI Session State V2

Maintains interactive shell context between user turns.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SessionState:
    # Project info
    project_path: str = field(default_factory=lambda: str(Path.cwd()))
    project_name: str = field(default_factory=lambda: Path.cwd().name)

    # Context
    active_file: str | None = None
    active_directory: str | None = None
    selected_model: str | None = None

    # History & previous turns
    last_query: str = ""
    last_result: str = ""
    last_plan: list[dict] = field(default_factory=list)
    last_edited_file: str | None = None
    last_created_file: str | None = None

    # Conversation log
    memory_enabled: bool = True
    conversation_history: list[tuple[str, str]] = field(default_factory=list)

    def remember(
        self,
        query: str,
        result: str,
        file_path: str | None = None,
        plan: list | None = None,
        model: str | None = None,
        last_edited_file: str | None = None,
        last_created_file: str | None = None,
    ):
        self.last_query = query
        self.last_result = result
        if plan is not None:
            self.last_plan = plan
        if model is not None:
            self.selected_model = model
        if last_edited_file is not None:
            self.last_edited_file = last_edited_file
        if last_created_file is not None:
            self.last_created_file = last_created_file

        if file_path:
            self.active_file = file_path
            self.active_directory = str(Path(file_path).parent)

        self.conversation_history.append((query, result))

    def clear(self):
        self.active_file = None
        self.active_directory = None
        self.selected_model = None
        self.last_query = ""
        self.last_result = ""
        self.last_plan.clear()
        self.last_edited_file = None
        self.last_created_file = None
        self.conversation_history.clear()