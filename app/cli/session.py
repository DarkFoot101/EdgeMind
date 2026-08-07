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
        query,
        result,
        file_path=None,
    ):
        if file_path:
            self.active_file = file_path
            self.active_directory = str(
                Path(file_path).parent
            )

    def clear(self):
        self.active_file = None
        self.active_directory = None
        self.selected_model = None
        self.last_query = ""
        self.last_result = ""
        self.last_plan.clear()
        self.conversation_history.clear()