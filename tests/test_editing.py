"""Pytest test suite for EdgeMind V2 Editing Subsystem."""

from pathlib import Path
from app.editing.editing_service import EditingService
from app.editing.models import EditRequest
from app.editing.file_manager import read_file, create_file


def test_editing_pipeline_create(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    src_file = tmp_path / "sample.java"
    src_file.write_text("public class Sample { public static int fib(int n) { return n <= 1 ? n : fib(n-1) + fib(n-2); } }", encoding="utf-8")

    req = EditRequest(
        file_path=str(src_file),
        target_file=str(tmp_path / "sample.py"),
        instruction="Convert Java fibonacci to Python",
        source_language="java",
        target_language="python",
        operation="create",
    )

    service = EditingService()
    # Mock modify_code output for testing isolated service logic
    monkeypatch.setattr("app.editing.editing_service.modify_code", lambda request: "def fib(n):\n    return n if n <= 1 else fib(n-1) + fib(n-2)\n")

    response = service.prepare_edit(req)
    assert response.success is True
    assert response.operation == "create"

    # Create file
    applied = service.create_file(response)
    assert applied is True

    # Verify target file exists and is valid Python
    target_py = tmp_path / "sample.py"
    assert target_py.exists()
    assert "def fib(n):" in target_py.read_text(encoding="utf-8")

    # Verify source file is untouched
    assert "public class Sample" in src_file.read_text(encoding="utf-8")


def test_editing_pipeline_modify(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target_file = tmp_path / "code.py"
    target_file.write_text("def add(a, b):\n    return a+b\n", encoding="utf-8")

    req = EditRequest(
        file_path=str(target_file),
        instruction="Add type hints",
        source_language="python",
        target_language="python",
        operation="modify",
    )

    service = EditingService()
    monkeypatch.setattr("app.editing.editing_service.modify_code", lambda request: "def add(a: int, b: int) -> int:\n    return a + b\n")

    response = service.prepare_edit(req)
    assert response.success is True

    applied = service.apply_edit(response, str(target_file))
    assert applied is True
    assert "a: int" in target_file.read_text(encoding="utf-8")