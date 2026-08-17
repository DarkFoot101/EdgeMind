"""
Persistence and retrieval of project execution memory for EdgeMind V2.1.
"""

import json
from contextlib import closing
from typing import Any, Dict, List, Optional, Tuple

from app.memory.database import get_connection, get_project_path
from app.memory.schema import initialize_database


def save_execution(state: dict[str, Any]) -> None:
    """Persist one completed task and execution metadata for the project that ran it."""
    initialize_database()
    result_text = str(state.get("result", ""))
    if len(result_text) > 2000:
        result_text = result_text[:2000] + "\n...[truncated]"

    plan_json_str = ""
    if state.get("plan"):
        try:
            plan_json_str = json.dumps(state["plan"])
        except Exception:
            plan_json_str = str(state["plan"])

    diff_str = ""
    edit_resp = state.get("edit_response")
    if edit_resp and getattr(edit_resp, "diff", None):
        diff_str = str(edit_resp.diff)

    with closing(get_connection()) as connection, connection:
        connection.execute(
            """
            INSERT INTO task_history
            (
                project_path,
                user_query,
                task,
                intent,
                file_path,
                source_file,
                target_file,
                operation,
                selected_model,
                plan_json,
                result,
                diff_text,
                success
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                get_project_path(state.get("project_path", ".")),
                state.get("user_query", "Unknown"),
                state.get("current_task", "Unknown"),
                state.get("intent", "execution"),
                state.get("file_path") or "",
                state.get("source_file") or "",
                state.get("target_file") or "",
                state.get("operation") or "",
                state.get("selected_model", "Unknown"),
                plan_json_str,
                result_text,
                diff_str,
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


def get_last_execution(project_path: str = ".") -> Optional[Dict[str, Any]]:
    """Retrieve the single most recent execution record for a project."""
    initialize_database()
    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT user_query, task, intent, file_path, source_file, target_file, operation, selected_model, plan_json, result, diff_text, success
            FROM task_history
            WHERE project_path = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (get_project_path(project_path),),
        ).fetchone()

        if not row:
            return None

        return {
            "user_query": row[0],
            "task": row[1],
            "intent": row[2],
            "file_path": row[3],
            "source_file": row[4],
            "target_file": row[5],
            "operation": row[6],
            "selected_model": row[7],
            "plan_json": row[8],
            "result": row[9],
            "diff_text": row[10],
            "success": bool(row[11]),
        }
