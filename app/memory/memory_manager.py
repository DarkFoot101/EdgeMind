"""Persistence and retrieval of project execution memory."""

from contextlib import closing
from typing import Any

from app.memory.database import get_connection, get_project_path
from app.memory.schema import initialize_database


def save_execution(state: dict[str, Any]) -> None:
    """Persist one completed task for the project that ran it."""

    initialize_database()
    with closing(get_connection()) as connection, connection:
        connection.execute(
            """
            INSERT INTO task_history
            (
                project_path,
                user_query,
                task,
                file_path,
                selected_model,
                result,
                success
            )

            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                get_project_path(state.get("project_path", ".")),
                state.get("user_query", "Unknown"),
                state.get("current_task", "Unknown"),
                state.get("file_path", ""),
                state.get("selected_model", "Unknown"),
                state.get("result", "Unknown"),
                state.get("execution_success", False),
            ),
        )


def get_recent_history(limit: int = 5) -> list[tuple[str, str, str, bool]]:
    """Return the most recent execution records across all projects."""

    if limit < 1:
        raise ValueError("History limit must be at least 1.")
    initialize_database()
    with closing(get_connection()) as connection:
        return connection.execute(
            """
            SELECT user_query, task, result, success
            FROM task_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()


def search_memory(project_path: str = ".") -> list[tuple[str, str, str, bool]]:
    """Retrieve the latest execution records for one project."""

    initialize_database()
    with closing(get_connection()) as connection:
        return connection.execute(
            """
            SELECT user_query, task, result, success
            FROM task_history
            WHERE project_path = ?
            ORDER BY id DESC
            LIMIT 5
            """,
            (get_project_path(project_path),),
        ).fetchall()
