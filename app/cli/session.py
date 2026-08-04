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
    current_file: str | None = None
    selected_model: str | None = None

    # Previous interaction
    last_query: str = ""
    last_result: str = ""
    last_plan: list[str] = field(default_factory=list)

    # Runtime
    memory_enabled: bool = True
    conversation_history: list[tuple[str, str]] = field(
        default_factory=list
    )

    def remember(
        self,
        query: str,
        result: str,
    ):
        self.last_query = query
        self.last_result = result
        self.conversation_history.append(
            (
                query,
                result,
            )
        )

    def clear(self):
        self.current_file = None
        self.selected_model = None
        self.last_query = ""
        self.last_result = ""
        self.last_plan.clear()
        self.conversation_history.clear()