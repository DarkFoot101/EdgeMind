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


def test_sqlite_memory_telemetry_and_scope_persistence(tmp_path):
    from app.editing.models import ExecutionMetrics
    from app.memory.memory_manager import get_last_execution

    proj_dir = str(tmp_path / "telemetry_proj")
    metrics = ExecutionMetrics(
        inference_time_seconds=0.42,
        prompt_tokens=150,
        completion_tokens=60,
        total_tokens=210,
        lines_added=5,
        lines_deleted=2,
        peak_memory_mb=64.2,
    )

    state = {
        "user_query": "Optimize fibonacci",
        "project_path": proj_dir,
        "current_task": "edit",
        "intent": "execution",
        "file_path": "math.py",
        "source_file": "math.py",
        "target_file": "math.py",
        "operation": "modify",
        "selected_model": "qwen2.5-coder:3b",
        "result": "Fibonacci function optimized",
        "execution_success": True,
        "metrics": metrics,
        "scope_type": "symbol",
        "source_hash": "a1b2c3d4e5f6",
        "modified_hash": "f6e5d4c3b2a1",
    }

    save_execution(state)
    rec = get_last_execution(proj_dir)

    assert rec is not None
    assert rec["user_query"] == "Optimize fibonacci"
    assert rec["scope_type"] == "symbol"
    assert rec["source_hash"] == "a1b2c3d4e5f6"
    assert rec["modified_hash"] == "f6e5d4c3b2a1"
    assert rec["metrics"] is not None
    assert rec["metrics"]["inference_time_seconds"] == 0.42
    assert rec["metrics"]["total_tokens"] == 210
    assert rec["metrics"]["peak_memory_mb"] == 64.2
    assert rec["metrics"]["lines_added"] == 5


def test_session_state_telemetry_recording(capsys):
    from app.cli.session import SessionState
    from app.cli.commands import show_status

    session = SessionState(project_path="/tmp/test_session")
    assert session.last_metrics is None
    assert session.last_scope is None

    session.remember(
        query="Refactor utils.py",
        result="Success",
        file_path="utils.py",
        metrics={"inference_time_seconds": 0.85, "total_tokens": 300, "peak_memory_mb": 55.4},
        scope="line_range",
        source_hash="1122334455667788",
        modified_hash="8877665544332211",
    )

    assert session.last_metrics["inference_time_seconds"] == 0.85
    assert session.last_scope == "line_range"
    assert session.last_source_hash == "1122334455667788"

    # Test show_status prints the telemetry without error
    show_status(session)
    captured = capsys.readouterr().out
    assert "Last Latency    : 0.85s (300 tokens)" in captured
    assert "Peak RSS Memory : 55.4 MB" in captured
    assert "Last Edit Scope : line_range" in captured
    assert "Source SHA-256  : 112233445566..." in captured

    # Test clear resets telemetry
    session.clear()
    assert session.last_metrics is None
    assert session.last_scope is None
    assert session.last_source_hash is None