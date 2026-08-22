"""
EdgeMind V2.1 Feature & Regression Test Suite

Validates:
- Intent Routing (Execution vs Follow-Up vs Conversational)
- Read-only Follow-up response handling without file modification
- Conversational companion mode without workflow triggering
- Backup exclusion during file discovery
- ModelManager discovery and resource-aware selection
- First-run model setup checks
- Multi-language create vs modify inference
- SQLite memory enrichment
"""

import pytest
from pathlib import Path
import tempfile

from app.cli.session import SessionState
from app.events.activity_stream import ActivityStream, EventType
from app.models.model_manager import ModelManager
from app.routing.intent_router import IntentType, detect_intent
from app.routing.conversation_handler import handle_follow_up, handle_conversational
from app.tools.file_discovery import resolve_best_file
from app.memory.memory_manager import save_execution, get_last_execution


def test_intent_routing_classification():
    """Verify IntentRouter accurately classifies user query types."""

    # 1. Conversational Queries
    intent_conv, _ = detect_intent("what do you think about this architecture?")
    assert intent_conv == IntentType.CONVERSATIONAL

    intent_conv2, _ = detect_intent("why is this happening?")
    assert intent_conv2 == IntentType.CONVERSATIONAL

    intent_conv3, _ = detect_intent("haha this thing is driving me crazy")
    assert intent_conv3 == IntentType.CONVERSATIONAL

    # 2. Execution Queries
    intent_exec, _ = detect_intent("convert bad.java to Python")
    assert intent_exec == IntentType.EXECUTION

    intent_exec2, _ = detect_intent("fix the fibonacci function in algorithms.py")
    assert intent_exec2 == IntentType.EXECUTION

    # 3. Follow-Up Queries (with previous turn)
    intent_fu, _ = detect_intent("What did you change?", has_previous_turn=True)
    assert intent_fu == IntentType.FOLLOW_UP

    intent_fu2, _ = detect_intent("Why did you change it?", has_previous_turn=True)
    assert intent_fu2 == IntentType.FOLLOW_UP

    intent_fu3, _ = detect_intent("Explain that change", has_previous_turn=True)
    assert intent_fu3 == IntentType.FOLLOW_UP


@pytest.mark.ollama
def test_follow_up_handler_preserves_files():
    """Verify handle_follow_up produces an explanation without modifying files."""
    session = SessionState()
    session.active_file = "algorithms.py"
    session.remember(
        query="Fix algorithms.py",
        result="Successfully modified file: algorithms.py\n\n--- algorithms.py\n+++ algorithms.py\n@@ -1 +1 @@\n-def fib(): pass\n+def fib(n): return n",
        file_path="algorithms.py",
        last_edited_file="algorithms.py",
    )

    res = handle_follow_up("What did you change?", session)

    assert res["intent"] == "follow_up"
    assert res["execution_success"] is True
    assert res["modified_file"] is None  # NO FILE MODIFIED
    assert any(kw in res["result"].lower() for kw in ["algorithms.py", "change", "update", "modify", "fib", "function"])


@pytest.mark.ollama
def test_conversational_handler_preserves_files():
    """Verify handle_conversational responds conversationally without editing files."""
    session = SessionState()
    session.active_file = "main.py"

    res = handle_conversational("what do you think about this architecture?", session)

    assert res["intent"] == "conversational"
    assert res["execution_success"] is True
    assert res["modified_file"] is None  # NO FILE MODIFIED


def test_file_discovery_excludes_backups_and_internal_dirs():
    """Verify file discovery never selects .bak or .edgemind backups as active target."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        
        # Create normal source file
        src = tmp / "calculator.py"
        src.write_text("def add(a, b): return a + b\n")

        # Create backup directories & files
        bak_dir = tmp / ".edgemind" / "backups"
        bak_dir.mkdir(parents=True, exist_ok=True)
        bak_file = bak_dir / "calculator.py"
        bak_file.write_text("def add(a, b): return a + b # BACKUP\n")

        bak_file2 = tmp / "calculator.py.bak"
        bak_file2.write_text("def add(a, b): return a + b # BAK\n")

        # Resolve best file
        resolved = resolve_best_file("calculator.py", str(tmp))
        assert resolved is not None
        assert not str(resolved).endswith(".bak")
        assert ".edgemind" not in str(resolved)
        assert Path(resolved).resolve() == src.resolve()


def test_model_manager_discovery_and_selection():
    """Verify ModelManager listing and task routing logic."""
    installed = ModelManager.list_installed_models()
    assert isinstance(installed, list)

    best_coding = ModelManager.select_best_model("edit")
    assert isinstance(best_coding, str)
    assert len(best_coding) > 0

    best_general = ModelManager.select_best_model("explain")
    assert isinstance(best_general, str)
    assert len(best_general) > 0


def test_activity_stream_emission():
    """Verify ActivityStream emits formatted events to subscribers."""
    received_events = []

    def listener(event):
        received_events.append(event)

    ActivityStream.subscribe(listener)
    ActivityStream.emit("Testing activity event", EventType.SUCCESS, stage="test")

    assert len(received_events) > 0
    assert received_events[-1].message == "Testing activity event"
    assert received_events[-1].event_type == EventType.SUCCESS
    assert "✓" in received_events[-1].formatted()

    ActivityStream.unsubscribe(listener)


def test_sqlite_memory_rich_metadata():
    """Verify enriched SQLite memory schema stores intent, files, and diff text."""
    test_state = {
        "project_path": "/tmp/test-project",
        "user_query": "Fix bugs in algorithms.py",
        "current_task": "edit",
        "intent": "execution",
        "file_path": "/tmp/test-project/algorithms.py",
        "source_file": "/tmp/test-project/algorithms.py",
        "target_file": "/tmp/test-project/algorithms.py",
        "operation": "modify",
        "selected_model": "qwen2.5-coder:3b",
        "result": "Successfully modified algorithms.py",
        "execution_success": True,
    }

    save_execution(test_state)
    last_rec = get_last_execution("/tmp/test-project")

    assert last_rec is not None
    assert last_rec["user_query"] == "Fix bugs in algorithms.py"
    assert last_rec["intent"] == "execution"
    assert last_rec["source_file"] == "/tmp/test-project/algorithms.py"
    assert last_rec["success"] is True
