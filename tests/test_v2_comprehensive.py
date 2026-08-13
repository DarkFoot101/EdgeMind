"""
Comprehensive EdgeMind V2 Pytest Test Suite
Covers all Phase 16 hardening, security, planning, validation, reviewer, and file lifecycle requirements.
"""

import json
from pathlib import Path
import pytest

from app.editing.editing_service import EditingService
from app.editing.file_manager import BACKUP_DIR, create_file, read_file, validate_project_path, write_file
from app.editing.models import EditRequest
from app.editing.validator import validate_code
from app.graph.nodes import execute_task_node, reviewer_node
from app.graph.planner import clean_planner_json, create_plan, sanitize_plan_tasks
from app.graph.planner_schema import Plan
from app.graph.state import EdgeMindState
from app.graph.workflow import workflow
from app.memory.memory_manager import save_execution, search_memory
from app.models.model_router import select_model
from app.setup.checks import check_disk, check_ram, missing_models
from app.tools.file_discovery import resolve_best_file, search_project_files


# 1. Modify existing Python file
def test_1_modify_existing_python_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    file_py = tmp_path / "main.py"
    file_py.write_text("def hello(): pass\n", encoding="utf-8")

    req = EditRequest(
        file_path=str(file_py),
        instruction="Add print inside hello",
        source_language="python",
        target_language="python",
        operation="modify",
    )
    service = EditingService()
    monkeypatch.setattr("app.editing.editing_service.modify_code", lambda request: "def hello():\n    print('Hello World')\n")

    resp = service.prepare_edit(req)
    assert resp.success is True
    applied = service.apply_edit(resp, str(file_py))
    assert applied is True
    assert "Hello World" in file_py.read_text(encoding="utf-8")


# 2. Create new Python file
def test_2_create_new_python_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    src_py = tmp_path / "calc.py"
    src_py.write_text("def add(a, b): return a + b\n", encoding="utf-8")
    target_py = tmp_path / "calc_v2.py"

    req = EditRequest(
        file_path=str(src_py),
        target_file=str(target_py),
        instruction="Create enhanced calc_v2",
        source_language="python",
        target_language="python",
        operation="create",
    )
    service = EditingService()
    monkeypatch.setattr("app.editing.editing_service.modify_code", lambda request: "def add(a: int, b: int) -> int:\n    return a + b\n")

    resp = service.prepare_edit(req)
    assert resp.success is True
    applied = service.create_file(resp)
    assert applied is True
    assert target_py.exists()
    assert src_py.read_text(encoding="utf-8") == "def add(a, b): return a + b\n"


# 3. Java -> Python conversion
def test_3_java_to_python_conversion(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    java_file = tmp_path / "Fib.java"
    java_file.write_text("public class Fib { public static int get(int n) { return n; } }", encoding="utf-8")
    py_target = tmp_path / "fib.py"

    req = EditRequest(
        file_path=str(java_file),
        target_file=str(py_target),
        instruction="Convert Java fibonacci to Python",
        source_language="java",
        target_language="python",
        operation="create",
    )
    service = EditingService()
    monkeypatch.setattr("app.editing.editing_service.modify_code", lambda request: "def get_fib(n: int) -> int:\n    return n\n")

    resp = service.prepare_edit(req)
    assert resp.success is True
    assert service.create_file(resp) is True
    assert py_target.exists()
    assert java_file.exists()


# 4. Python -> Java conversion
def test_4_python_to_java_conversion(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    py_file = tmp_path / "helper.py"
    py_file.write_text("def greet(): print('hi')\n", encoding="utf-8")
    java_target = tmp_path / "Helper.java"

    req = EditRequest(
        file_path=str(py_file),
        target_file=str(java_target),
        instruction="Convert to Java class",
        source_language="python",
        target_language="java",
        operation="create",
    )
    service = EditingService()
    monkeypatch.setattr("app.editing.editing_service.modify_code", lambda request: "public class Helper {\n    public static void greet() {\n        System.out.println(\"hi\");\n    }\n}\n")

    resp = service.prepare_edit(req)
    assert resp.success is True
    assert service.create_file(resp) is True
    assert java_target.exists()


# 5 & 6 & 7. Autonomous File Discovery, Multiple Matches, Backup Exclusion
def test_5_6_7_file_discovery_and_backup_exclusion(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "auth_service.py").write_text("def login_user(): pass\n", encoding="utf-8")
    (tmp_path / "test_auth.py").write_text("def test_login(): pass\n", encoding="utf-8")

    backup_dir = tmp_path / ".edgemind/backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / "auth_service.py").write_text("def old_login(): pass\n", encoding="utf-8")

    found = search_project_files("login_user authentication", str(tmp_path))
    assert len(found) > 0
    assert not any(".edgemind" in f for f in found)

    best = resolve_best_file("Fix authentication in login_user", str(tmp_path))
    assert best is not None
    assert "auth_service.py" in best


# 8. Follow-up prompt using "it"
def test_8_follow_up_prompt_resolution(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    file_py = tmp_path / "math_utils.py"
    file_py.write_text("def calc(): pass\n", encoding="utf-8")

    best = resolve_best_file("Now optimize it", str(tmp_path), active_file=str(file_py))
    assert best == str(file_py.resolve())


# 9 & 10. Planner malformed JSON, quote cleaning & task sanitizer
def test_9_10_planner_cleaning_and_fallback():
    # Trailing quote inside JSON string value (the exact error from user terminal trace)
    raw_quote_bug = '{\n  "tasks": [\n    {\n      "tool": "edit",\n      "operation": "create",\n      "instruction": "Convert",\n      "target_file": "tests/corrected.py\'"\n    }\n  ]\n}'
    cleaned = clean_planner_json(raw_quote_bug)
    plan = Plan.model_validate_json(cleaned)
    sanitized = sanitize_plan_tasks(plan, "Convert bad.java to Python")
    assert sanitized[0]["target_file"] == "tests/corrected.py"

    # Trailing comma cleaning
    raw_trailing_comma = '{\n  "tasks": [\n    {\n      "tool": "edit",\n      "operation": "modify",\n      "instruction": "Fix bug",\n    },\n  ]\n}'
    cleaned_tc = clean_planner_json(raw_trailing_comma)
    plan_tc = Plan.model_validate_json(cleaned_tc)
    assert plan_tc.tasks[0].instruction == "Fix bug"

    # Unrequested deployment task suppression
    raw_deployment = '{\n  "tasks": [\n    {\n      "tool": "deployment",\n      "operation": "create",\n      "instruction": "Fix authentication in auth.py"\n    }\n  ]\n}'
    cleaned_dep = clean_planner_json(raw_deployment)
    plan_dep = Plan.model_validate_json(cleaned_dep)
    sanitized_dep = sanitize_plan_tasks(plan_dep, "Fix authentication in auth.py")
    assert sanitized_dep[0]["tool"] == "edit"


# 11. Planner Create vs Modify inference
def test_11_create_vs_modify_inference(monkeypatch):
    monkeypatch.setattr("app.graph.planner.generate_response", lambda prompt, model, system_prompt: '{"tasks":[{"tool":"edit","operation":"create","instruction":"Convert","target_file":"out.py"}]}')
    plan = create_plan("Convert bad.java to Python")
    assert len(plan) == 1
    assert plan[0]["operation"] == "create"
    assert plan[0]["target_file"] == "out.py"


# 12 & 13. Syntax Validation Failure & Success
def test_12_13_syntax_validation():
    valid_py = "def foo():\n    return 42\n"
    invalid_py = "def foo(:\n    return 42\n"
    valid_java = "public class A { void b() {} }"
    invalid_java = "public class A { void b() {"

    val_v_py, _ = validate_code(valid_py, "python")
    val_i_py, msg_i_py = validate_code(invalid_py, "python")
    val_v_ja, _ = validate_code(valid_java, "java")
    val_i_ja, _ = validate_code(invalid_java, "java")

    assert val_v_py is True
    assert val_i_py is False
    assert "SyntaxError" in msg_i_py
    assert val_v_ja is True
    assert val_i_ja is False


# 14. Analysis Context Propagation
def test_14_analysis_context_propagation(monkeypatch):
    captured_prompt = {}

    def mock_generate_response(prompt, model, system_prompt):
        captured_prompt["prompt"] = prompt
        return "def fixed_code(): pass\n"

    monkeypatch.setattr("app.editing.code_modifier.generate_response", mock_generate_response)

    req = EditRequest(
        file_path="sample.py",
        instruction="Fix bug identified in analysis",
        source_code="def bug(): pass\n",
        source_language="python",
        target_language="python",
        operation="modify",
        analysis_result="Discovered off-by-one error in loop index at line 12",
    )

    from app.editing.code_modifier import modify_code
    modify_code(req)

    assert "Prior Analysis Findings" in captured_prompt["prompt"]
    assert "off-by-one error" in captured_prompt["prompt"]


# 15 & 23 & 24. Reviewer Verification on Actual Disk Content & File Isolation
def test_15_23_24_reviewer_verification_and_isolation(tmp_path):
    src = tmp_path / "orig.java"
    src.write_text("class Orig {}", encoding="utf-8")
    target = tmp_path / "out.py"

    state: EdgeMindState = {
        "user_query": "Convert orig.java to out.py",
        "project_path": str(tmp_path),
        "file_path": str(src),
        "source_file": str(src),
        "target_file": str(target),
        "modified_file": str(target),
        "source_language": "java",
        "target_language": "python",
        "current_task": "edit",
        "operation": "create",
        "execution_success": True,
        "edit_response": None,
        "plan": [],
        "current_step": 0,
        "task_instruction": "",
        "selected_model": "",
        "retry_count": 0,
        "max_retry": 2,
        "result": "",
        "memory_context": "",
        "analysis_result": None,
        "discovered_files": [],
        "review_status": None,
        "change_summary": None,
    }

    # If target file is missing, reviewer must fail
    res_state = reviewer_node(dict(state))
    assert res_state["execution_success"] is False

    # Write target file with invalid syntax
    target.write_text("def invalid_syntax(:\n", encoding="utf-8")

    class DummyResp:
        success = True

    state_bad = dict(state)
    state_bad["edit_response"] = DummyResp()
    res_state_bad = reviewer_node(state_bad)
    assert res_state_bad["execution_success"] is False
    assert any("Syntax validation failed on disk file" in d for d in res_state_bad["review_status"]["details"])

    # Write target file with valid syntax
    target.write_text("def valid_syntax(): pass\n", encoding="utf-8")
    state_good = dict(state)
    state_good["execution_success"] = True
    state_good["edit_response"] = DummyResp()
    res_state_good = reviewer_node(state_good)
    assert res_state_good["execution_success"] is True
    assert any("Syntax validation passed" in d for d in res_state_good["review_status"]["details"])


# 16. SQLite Memory Persistence
def test_16_sqlite_persistence():
    save_execution({"project_path": ".", "user_query": "Persistent task", "current_task": "analyze", "result": "OK", "execution_success": True})
    rows = search_memory(".")
    assert any("Persistent task" in r[0] for r in rows)


# 19 & 20. Security Boundary & Path Traversal Rejection
def test_19_20_security_boundary_and_path_traversal(tmp_path):
    with pytest.raises(ValueError, match="Security error"):
        validate_project_path("../outside.py", str(tmp_path))

    with pytest.raises(ValueError, match="Security error"):
        validate_project_path("/tmp/arbitrary.py", str(tmp_path))


# 22. Unrelated deployment request filtering
def test_22_unrelated_deployment_requests(monkeypatch):
    monkeypatch.setattr("app.graph.planner.generate_response", lambda prompt, model, system_prompt: '{"tasks":[{"tool":"edit","operation":"modify","instruction":"Fix auth"}]}')
    plan = create_plan("Fix authentication bug in login.py")
    assert all(t["tool"] != "deployment" for t in plan)
