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


def test_edit_models_canonical_paths_and_operation_types(tmp_path):
    from app.editing.models import OperationType, EditResponse

    # Test operation enum normalization
    req = EditRequest(
        file_path="src/utils.py",
        instruction="Refactor helper",
        operation="create",
        target_file="src/utils_v2.py",
    )
    assert req.operation == OperationType.CREATE
    assert req.canonical_source_path == "src/utils.py"
    assert req.canonical_target_path == "src/utils_v2.py"
    assert req.output_file == "src/utils_v2.py"

    # Test serialization
    dict_repr = req.to_dict()
    assert dict_repr["operation"] == "create"
    assert dict_repr["file_path"] == "src/utils.py"

    # Test EditResponse destination_path property
    resp = EditResponse(
        success=True,
        file_path="src/utils.py",
        original_code="old",
        modified_code="new",
        diff="---",
        validation_message="Passed",
        backup_path=None,
        error=None,
        operation="create",
        output_file="src/utils_v2.py",
    )
    assert resp.operation == OperationType.CREATE
    assert resp.destination_path == "src/utils_v2.py"
    assert resp.to_dict()["operation"] == "create"


def test_editing_optimistic_concurrency_protection(tmp_path, monkeypatch):
    import pytest
    monkeypatch.chdir(tmp_path)
    test_file = tmp_path / "concurrent.py"
    test_file.write_text("initial = 1\n", encoding="utf-8")

    req = EditRequest(
        file_path=str(test_file),
        instruction="Update initial to 2",
        operation="modify",
    )
    service = EditingService()
    monkeypatch.setattr("app.editing.editing_service.modify_code", lambda request: "initial = 2\n")

    resp = service.prepare_edit(req)
    assert resp.success is True
    assert resp.source_hash is not None
    assert resp.modified_hash is not None

    # Simulate concurrent external edit on disk after preview was prepared
    test_file.write_text("initial = 999  # External conflict\n", encoding="utf-8")

    # Attempting to apply edit should raise concurrency conflict
    with pytest.raises(ValueError, match="Concurrency conflict"):
        service.apply_edit(resp, str(test_file))

    # Applying with force=True should bypass the check
    applied = service.apply_edit(resp, str(test_file), force=True)
    assert applied is True
    assert "initial = 2" in test_file.read_text(encoding="utf-8")


def test_scoped_editing_line_range_and_ast_symbol(tmp_path, monkeypatch):
    from app.editing.scope import EditScopeType
    monkeypatch.chdir(tmp_path)

    # 1. Test AST Symbol Scoped Editing
    code_content = (
        "def helper_one():\n"
        "    return 1\n\n"
        "def target_function(x):\n"
        "    return x\n\n"
        "def helper_two():\n"
        "    return 2\n"
    )
    test_file = tmp_path / "multi_func.py"
    test_file.write_text(code_content, encoding="utf-8")

    req_symbol = EditRequest(
        file_path=str(test_file),
        instruction="Multiply x by 10",
        target_symbol="target_function",
        operation="modify",
    )
    assert req_symbol.scope.scope_type == EditScopeType.SYMBOL
    assert req_symbol.scope.target_symbol == "target_function"

    service = EditingService()
    # Mock LLM generation to return only the modified symbol
    monkeypatch.setattr(
        "app.editing.code_modifier.generate_response",
        lambda **kwargs: "def target_function(x):\n    return x * 10\n",
    )

    resp = service.prepare_edit(req_symbol)
    assert resp.success is True
    assert resp.scope is not None
    assert resp.scope.target_symbol == "target_function"

    # Verify diff only changes target_function and keeps helper_one/two intact
    assert "helper_one" in resp.original_code
    assert "helper_two" in resp.original_code

    applied = service.apply_edit(resp, str(test_file))
    assert applied is True

    disk_text = test_file.read_text(encoding="utf-8")
    assert "def helper_one():\n    return 1" in disk_text
    assert "return x * 10" in disk_text
    assert "def helper_two():\n    return 2" in disk_text

    # 2. Test Line Range Scoping
    range_file = tmp_path / "range_test.py"
    range_file.write_text("line1 = 1\nline2 = 2\nline3 = 3\nline4 = 4\n", encoding="utf-8")

    req_range = EditRequest(
        file_path=str(range_file),
        instruction="Change lines 2 to 3",
        start_line=2,
        end_line=3,
        operation="modify",
    )
    assert req_range.scope.scope_type == EditScopeType.LINE_RANGE
    assert req_range.start_line == 2
    assert req_range.end_line == 3

    monkeypatch.setattr(
        "app.editing.code_modifier.generate_response",
        lambda **kwargs: "line2 = 200\nline3 = 300\n",
    )
    resp_range = service.prepare_edit(req_range)
    assert resp_range.success is True
    applied_range = service.apply_edit(resp_range, str(range_file))
    assert applied_range is True

    disk_range_text = range_file.read_text(encoding="utf-8")
    assert "line1 = 1" in disk_range_text
    assert "line2 = 200" in disk_range_text
    assert "line3 = 300" in disk_range_text
    assert "line4 = 4" in disk_range_text

    # 3. Test explicit scope_type string initialization
    req_explicit = EditRequest(
        file_path=str(range_file),
        instruction="Modify",
        scope_type="line_range",
        start_line=1,
        end_line=2,
    )
    assert req_explicit.scope.scope_type == EditScopeType.LINE_RANGE
    assert req_explicit.scope_type == EditScopeType.LINE_RANGE


def test_scope_utilities():
    from app.editing.scope import (
        extract_code_slice,
        splice_code_slice,
        extract_symbol_range,
        apply_search_and_replace,
    )

    code = "line1\nline2\nline3\nline4\n"
    assert extract_code_slice(code, 2, 3) == "line2\nline3"
    spliced = splice_code_slice(code, "new_line2\nnew_line3", 2, 3)
    assert spliced == "line1\nnew_line2\nnew_line3\nline4\n"

    py_code = "def foo():\n    return 1\n\ndef bar(x):\n    return x + 1\n"
    rng = extract_symbol_range(py_code, "bar", "python")
    assert rng == (4, 5)

    java_code = "public class A {\n    public int calc() {\n        return 42;\n    }\n}\n"
    java_rng = extract_symbol_range(java_code, "calc", "java")
    assert java_rng == (2, 4)

    success, rep = apply_search_and_replace(code, "line2\nline3", "replaced")
    assert success is True
    assert "replaced" in rep
    assert "line1\nreplaced\nline4" in rep


def test_execution_telemetry_metrics(tmp_path, monkeypatch):
    from app.editing.diff_generator import compute_diff_stats
    from app.editing.models import ExecutionMetrics
    monkeypatch.chdir(tmp_path)

    # 1. Test diff stats calculation
    sample_diff = (
        "--- file.py (original)\n"
        "+++ file.py (modified)\n"
        "@@ -1,3 +1,4 @@\n"
        "-line1\n"
        "+line1_mod\n"
        "+line1_extra\n"
        " line2\n"
    )
    added, deleted = compute_diff_stats(sample_diff)
    assert added == 2
    assert deleted == 1

    # 2. Test ExecutionMetrics serialization
    m = ExecutionMetrics(
        inference_time_seconds=0.45,
        prompt_tokens=120,
        completion_tokens=45,
        total_tokens=165,
        lines_added=2,
        lines_deleted=1,
        peak_memory_mb=48.5,
    )
    d = m.to_dict()
    assert d["inference_time_seconds"] == 0.45
    assert d["total_tokens"] == 165
    assert d["peak_memory_mb"] == 48.5

    # 3. Test telemetry generation during prepare_edit
    test_f = tmp_path / "telemetry_test.py"
    test_f.write_text("x = 1\n", encoding="utf-8")

    req = EditRequest(
        file_path=str(test_f),
        instruction="Change x to 10",
        operation="modify",
    )
    service = EditingService()
    monkeypatch.setattr(
        "app.editing.editing_service.modify_code",
        lambda request: "x = 10\n",
    )

    resp = service.prepare_edit(req)
    assert resp.success is True
    assert resp.metrics is not None
    assert resp.metrics.inference_time_seconds >= 0.0
    assert resp.metrics.peak_memory_mb > 0.0
    assert resp.metrics.lines_added == 1
    assert resp.metrics.lines_deleted == 1
    assert resp.to_dict()["metrics"]["lines_added"] == 1


def test_candidate_evaluator_and_ranking():
    from app.editing.candidate_ranker import evaluate_candidate, rank_candidates

    req = EditRequest(
        file_path="math_ops.py",
        instruction="Implement add_numbers",
        target_symbol="add_numbers",
        target_language="python",
        operation="modify",
    )
    original_code = "def existing():\n    return 42\n"

    # Candidate 1: Broken Python syntax
    cand1 = "def add_numbers(a, b):\n    return a + ((\n"
    # Candidate 2: Valid Python syntax with target_symbol
    cand2 = "def existing():\n    return 42\n\ndef add_numbers(a, b):\n    return a + b\n"
    # Candidate 3: Valid Python syntax but wipes existing code and lacks symbol
    cand3 = "x = 100\n"

    res1 = evaluate_candidate(1, cand1, req, original_code)
    assert res1.syntax_valid is False
    assert "SyntaxError" in res1.validation_message

    res2 = evaluate_candidate(2, cand2, req, original_code)
    assert res2.syntax_valid is True
    assert res2.score > res1.score

    best, all_cands = rank_candidates([cand1, cand2, cand3], req, original_code)
    assert best.candidate_id == 2
    assert best.syntax_valid is True
    assert "def add_numbers(a, b):" in best.content
    assert len(all_cands) == 3


def test_editing_service_best_of_n_selection(tmp_path):
    src_file = tmp_path / "calc.py"
    src_file.write_text("def subtract(a, b):\n    return a - b\n", encoding="utf-8")

    # Supply multiple candidates via request metadata
    broken_candidate = "def multiply(a, b):\n    return a *  # incomplete syntax\n"
    valid_candidate = "def subtract(a, b):\n    return a - b\n\ndef multiply(a, b):\n    return a * b\n"

    req = EditRequest(
        file_path=str(src_file),
        project_path=str(tmp_path),
        instruction="Add multiply function",
        target_symbol="multiply",
        target_language="python",
        operation="modify",
        candidates_count=2,
        metadata={"candidates": [broken_candidate, valid_candidate]},
    )

    service = EditingService()
    resp = service.prepare_edit(req)

    assert resp.success is True
    assert resp.selected_candidate_id == 2
    assert resp.candidate_patches is not None
    assert len(resp.candidate_patches) == 2
    assert resp.candidate_patches[0].syntax_valid is False
    assert "def multiply(a, b):" in resp.modified_code
    assert resp.to_dict()["selected_candidate_id"] == 2
    assert len(resp.to_dict()["candidate_patches"]) == 2


def test_colorize_diff_ansi_formatting():
    from app.editing.diff_generator import colorize_diff

    sample_diff = (
        "--- auth.py (original)\n"
        "+++ auth.py (modified)\n"
        "@@ -10,3 +10,3 @@\n"
        "-def verify(): return False\n"
        "+def verify(): return True\n"
        " context line\n"
    )

    colored = colorize_diff(sample_diff)
    # Check ANSI codes for red on deletion, green on addition, cyan on hunk header
    assert "\033[91m-def verify(): return False\033[0m" in colored
    assert "\033[92m+def verify(): return True\033[0m" in colored
    assert "\033[96m@@ -10,3 +10,3 @@\033[0m" in colored
    assert "context line" in colored


def test_interactive_approval_gate(tmp_path, monkeypatch):
    from app.graph.nodes import execute_task_node
    from app.editing.editing_service import EditingService

    test_file = tmp_path / "protected.py"
    test_file.write_text("status = 'pending'\n", encoding="utf-8")

    state = {
        "user_query": "Change status to active",
        "project_path": str(tmp_path),
        "file_path": str(test_file),
        "source_file": str(test_file),
        "target_file": None,
        "operation": "modify",
        "current_task": "edit",
        "task_instruction": "Change status to active",
        "source_language": "python",
        "target_language": "python",
        "require_approval": True,
        "approval_pending": False,
        "selected_model": "qwen2.5-coder:3b",
    }

    monkeypatch.setattr(
        "app.editing.editing_service.modify_code",
        lambda request: "status = 'active'\n",
    )

    # 1. When require_approval is True, execute_task_node prepares preview but holds disk write
    result_state = execute_task_node(state)
    assert result_state["execution_success"] is True
    assert result_state["approval_pending"] is True
    # Disk file remains UNTOUCHED
    assert test_file.read_text(encoding="utf-8") == "status = 'pending'\n"

    # 2. When user accepts, apply_edit writes to disk
    resp = result_state["edit_response"]
    assert resp is not None
    service = EditingService()
    applied = service.apply_edit(resp, str(test_file), project_path=str(tmp_path))
    assert applied is True
    assert test_file.read_text(encoding="utf-8") == "status = 'active'\n"


def test_rpc_bridge_handlers(tmp_path, monkeypatch):
    import json
    from app.cli.rpc import handle_request
    from app.editing.editing_service import EditingService

    service = EditingService()

    # 1. ping
    ping_req = {"id": 1, "method": "ping", "params": {}}
    ping_resp = handle_request(ping_req, service)
    assert ping_resp["id"] == 1
    assert ping_resp["result"]["status"] == "ok"

    # 2. prepare_edit
    test_file = tmp_path / "rpc_sample.py"
    test_file.write_text("x = 10\n", encoding="utf-8")

    monkeypatch.setattr(
        "app.editing.editing_service.modify_code",
        lambda **kwargs: "x = 20\n",
    )

    prep_req = {
        "id": 2,
        "method": "prepare_edit",
        "params": {
            "file_path": str(test_file),
            "instruction": "Set x to 20",
            "project_path": str(tmp_path),
        },
    }
    prep_resp = handle_request(prep_req, service)
    assert prep_resp["id"] == 2
    assert prep_resp["result"]["success"] is True
    assert prep_resp["result"]["modified_code"] == "x = 20\n"

    # 3. apply_edit
    apply_req = {
        "id": 3,
        "method": "apply_edit",
        "params": {
            "file_path": str(test_file),
            "modified_code": "x = 20\n",
            "source_hash": prep_resp["result"]["source_hash"],
            "project_path": str(tmp_path),
        },
    }
    apply_resp = handle_request(apply_req, service)
    assert apply_resp["id"] == 3
    assert apply_resp["result"]["success"] is True
    assert test_file.read_text(encoding="utf-8") == "x = 20\n"

    # 4. unknown method
    err_req = {"id": 4, "method": "unknown_action", "params": {}}
    err_resp = handle_request(err_req, service)
    assert "error" in err_resp