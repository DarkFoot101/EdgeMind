"""Pytest test suite for EdgeMind V2 SQLite Memory Subsystem."""

from datetime import datetime
from app.memory.memory_manager import save_execution, search_memory, get_recent_history


def test_sqlite_memory_persistence():
    query_str = f"Test query at {datetime.now().isoformat()}"
    sample_state = {
        "user_query": query_str,
        "project_path": ".",
        "current_task": "analyze",
        "file_path": "app/graph/planner.py",
        "selected_model": "phi3:mini",
        "result": "Project analyzed successfully.",
        "execution_success": True,
    }

    save_execution(sample_state)

    rows = search_memory(".")
    assert len(rows) > 0

    queries = [r[0] for r in rows]
    assert query_str in queries


def test_memory_result_truncation():
    large_result = "A" * 5000
    state = {
        "user_query": "Large test",
        "project_path": ".",
        "current_task": "edit",
        "result": large_result,
        "execution_success": True,
    }

    save_execution(state)
    rows = search_memory(".")
    latest_result = rows[0][2]
    assert len(latest_result) <= 2100
    assert "...[truncated]" in latest_result