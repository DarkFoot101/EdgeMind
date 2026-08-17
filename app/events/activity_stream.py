"""
EdgeMind V2.1 Real-Time Activity Event Streaming System

Provides structured, safe, user-facing agent activity events during graph execution
and conversational processing without exposing hidden model chain-of-thought.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional


class EventType(str, Enum):
    INFO = "info"
    PROGRESS = "progress"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    ACTION = "action"


@dataclass
class ActivityEvent:
    message: str
    event_type: EventType = EventType.INFO
    stage: str = "general"
    detail: Optional[str] = None
    icon: Optional[str] = None

    def formatted(self) -> str:
        """Format event message with Claude-Code style visual indicators."""
        if self.icon:
            prefix = self.icon
        elif self.event_type == EventType.SUCCESS:
            prefix = "✓"
        elif self.event_type == EventType.PROGRESS:
            prefix = "●"
        elif self.event_type == EventType.ACTION:
            prefix = "→"
        elif self.event_type == EventType.WARNING:
            prefix = "⚠"
        elif self.event_type == EventType.ERROR:
            prefix = "✗"
        else:
            prefix = "●"

        if self.detail:
            return f"{prefix} {self.message} ({self.detail})"
        return f"{prefix} {self.message}"


class ActivityStream:
    _listeners: List[Callable[[ActivityEvent], None]] = []

    @classmethod
    def subscribe(cls, listener: Callable[[ActivityEvent], None]) -> None:
        """Register a callback for streaming activity events."""
        if listener not in cls._listeners:
            cls._listeners.append(listener)

    @classmethod
    def unsubscribe(cls, listener: Callable[[ActivityEvent], None]) -> None:
        """Unregister an event listener."""
        if listener in cls._listeners:
            cls._listeners.remove(listener)

    @classmethod
    def emit(
        cls,
        message: str,
        event_type: EventType = EventType.INFO,
        stage: str = "general",
        detail: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> ActivityEvent:
        """Emit a user-facing activity event to all registered listeners."""
        event = ActivityEvent(
            message=message,
            event_type=event_type,
            stage=stage,
            detail=detail,
            icon=icon,
        )
        for listener in cls._listeners:
            try:
                listener(event)
            except Exception:
                pass
        return event

    @classmethod
    def clear_listeners(cls) -> None:
        """Clear all active listeners."""
        cls._listeners.clear()
