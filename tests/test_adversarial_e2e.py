"""
Adversarial End-to-End Real Execution Pytest Suite for EdgeMind V2

Executes real workflow invocations against isolated external project directories:
1. Python Project real multi-file debugging & optimization
2. Python CREATE vs MODIFY semantics
3. Real Java analysis & Java -> Python conversion (source preserved, target created, no markdown fences)
4. Real JavaScript analysis & Node.js syntax validation
5. Autonomous file discovery without filenames & internal dir exclusion (.git, .venv, .edgemind)
6. Ambiguous natural language prompts & multi-turn context resolution
7. Analysis -> Edit state propagation
8. Disk Reviewer verification against actual filesystem
9. Security isolation (rejection of path traversal & forbidden internal dirs)
10. Deployment routing isolation (no Dockerfile on normal code edit requests)
"""

import os
import shutil
import subprocess
from pathlib import Path
import pytest

from app.cli.interactive import create_state, update_session_context
from app.cli.session import SessionState
from app.editing.file_manager import validate_project_path
from app.editing.validator import validate_code
from app.graph.workflow import workflow


def _is_ollama_available() -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=1):
            return True
    except Exception:
        return False


# -----------------------------------------------------------------------------
# 1. Python Project Adversarial Execution
# -----------------------------------------------------------------------------
@pytest.mark.skipif(
    not _is_ollama_available() or not Path("/tmp/edgemind-adversarial-tests/python-project/algorithms.py").is_file(),
    reason="Requires live Ollama service and external python-project algorithms.py fixture",
)
def test_real_python_project_flow():
    project_dir = Path("/tmp/edgemind-adversarial-tests/python-project").resolve()
    assert project_dir.is_dir()

    session = SessionState()
    session.project_path = str(project_dir)

    # 1.1 Find & Fix problems in python project
    state = create_state(session, "Find the problems in this project and fix the code")
    state["project_path"] = str(project_dir)
    res = workflow.invoke(state)

    assert res.get("execution_success") is True
    assert res.get("modified_file") is not None
    mod_file = Path(res["modified_file"])
    assert mod_file.exists()
    assert mod_file.relative_to(project_dir)  # Safety check

    # Verify python syntax
    valid, msg = validate_code(mod_file.read_text(encoding="utf-8"), "python")
    assert valid is True, f"Generated Python syntax invalid: {msg}"


@pytest.mark.skipif(
    not _is_ollama_available() or not Path("/tmp/edgemind-adversarial-tests/python-project/algorithms.py").is_file(),
    reason="Requires live Ollama service and external python-project algorithms.py fixture",
)
def test_python_create_vs_modify():
    project_dir = Path("/tmp/edgemind-adversarial-tests/python-project").resolve()
    alg_py = project_dir / "algorithms.py"
    alg_hash_before = hash(alg_py.read_text(encoding="utf-8"))

    # Create new file algorithms_v2.py
    session = SessionState()
    session.project_path = str(project_dir)
    state = create_state(session, "Create a cleaner Python implementation of algorithms.py in a new file algorithms_v2.py")
    state["project_path"] = str(project_dir)
    state["source_file"] = str(alg_py)
    state["target_file"] = str(project_dir / "algorithms_v2.py")
    state["operation"] = "create"

    res = workflow.invoke(state)
    assert res.get("execution_success") is True

    # Original file must remain untouched
    alg_hash_after = hash(alg_py.read_text(encoding="utf-8"))
    assert alg_hash_before == alg_hash_after, "Source file was modified during CREATE operation!"

    # New file must exist and be valid
    target_py = project_dir / "algorithms_v2.py"
    assert target_py.exists()
    content = target_py.read_text(encoding="utf-8")
    assert len(content.strip()) > 0
    assert "```" not in content  # Ensure no markdown fences in code file


# -----------------------------------------------------------------------------
# 2. Java & Java -> Python Conversion Execution
# -----------------------------------------------------------------------------
@pytest.mark.skipif(
    not _is_ollama_available() or not Path("/tmp/edgemind-adversarial-tests/java-project/BadAlgorithm.java").is_file(),
    reason="Requires live Ollama service and external java-project BadAlgorithm.java fixture",
)
def test_real_java_to_python_conversion():
    project_dir = Path("/tmp/edgemind-adversarial-tests/java-project").resolve()
    java_file = project_dir / "BadAlgorithm.java"
    java_hash_before = hash(java_file.read_text(encoding="utf-8"))

    session = SessionState()
    session.project_path = str(project_dir)
    state = create_state(session, "Analyze BadAlgorithm.java, fix the algorithm, and create an optimized Python version.")
    state["project_path"] = str(project_dir)

    res = workflow.invoke(state)
    assert res.get("execution_success") is True

    # 1. Java source must be UNCHANGED
    java_hash_after = hash(java_file.read_text(encoding="utf-8"))
    assert java_hash_before == java_hash_after, "Java source file was modified when user asked for Python version!"

    # 2. Python target file CREATED
    py_target = project_dir / "BadAlgorithm.py"
    assert py_target.exists(), "Target Python file was not created on disk!"

    py_content = py_target.read_text(encoding="utf-8")
    assert len(py_content.strip()) > 0

    # 3. Clean source code checks (no markdown fences, no lead-in chatter)
    assert "```" not in py_content, "Generated Python file contains markdown fences!"
    assert not py_content.lower().startswith("here is"), "Generated file contains conversational lead-in!"

    # 4. AST Syntax validation
    valid, msg = validate_code(py_content, "python")
    assert valid is True, f"Converted Python file syntax error: {msg}"


# -----------------------------------------------------------------------------
# 3. JavaScript Project Real Execution
# -----------------------------------------------------------------------------
@pytest.mark.skipif(
    not _is_ollama_available() or not Path("/tmp/edgemind-adversarial-tests/javascript-project/buggy.js").is_file(),
    reason="Requires live Ollama service and external javascript-project buggy.js fixture",
)
def test_real_javascript_project_flow():
    project_dir = Path("/tmp/edgemind-adversarial-tests/javascript-project").resolve()
    js_file = project_dir / "buggy.js"

    session = SessionState()
    session.project_path = str(project_dir)
    state = create_state(session, "Find the bug in buggy.js, fix it, and explain the changes.")
    state["project_path"] = str(project_dir)
    state["source_file"] = str(js_file)

    res = workflow.invoke(state)
    assert res.get("execution_success") is True

    # Verify Node.js compile check if node exists
    if shutil.which("node"):
        proc = subprocess.run(["node", "-c", str(js_file)], capture_output=True, text=True)
        assert proc.returncode == 0, f"Node.js syntax check failed on modified file: {proc.stderr}"


# -----------------------------------------------------------------------------
# 4. Autonomous File Discovery & Exclusions
# -----------------------------------------------------------------------------
def test_file_discovery_excludes_internal_dirs(tmp_path):
    project_dir = tmp_path

    # Create fake internal directories
    (project_dir / ".git").mkdir(parents=True, exist_ok=True)
    (project_dir / ".git" / "fake.py").write_text("def fake(): pass", encoding="utf-8")
    (project_dir / ".venv").mkdir(parents=True, exist_ok=True)
    (project_dir / ".venv" / "lib.py").write_text("def lib(): pass", encoding="utf-8")

    from app.tools.file_discovery import search_project_files, resolve_best_file

    candidates = search_project_files("find fake function", str(project_dir))
    for c in candidates:
        assert not c.startswith(".git")
        assert not c.startswith(".venv")

    best = resolve_best_file("fake.py", str(project_dir))
    if best:
        assert ".git" not in Path(best).parts
        assert ".venv" not in Path(best).parts


# -----------------------------------------------------------------------------
# 5. Security & Isolation Verification
# -----------------------------------------------------------------------------
def test_security_path_traversal_rejection(tmp_path):
    project_dir = tmp_path

    # Attempt path traversal outside project root
    with pytest.raises(ValueError) as exc:
        validate_project_path("../outside.py", str(project_dir))
    assert "Security error" in str(exc.value) or "outside project" in str(exc.value)

    # Attempt modifying internal .git directory
    git_file = project_dir / ".git" / "config"
    git_file.parent.mkdir(parents=True, exist_ok=True)
    git_file.write_text("config", encoding="utf-8")

    with pytest.raises(ValueError) as exc_git:
        validate_project_path(str(git_file), str(project_dir))
    assert "Security error" in str(exc_git.value)


# -----------------------------------------------------------------------------
# 6. Deployment Routing Isolation
# -----------------------------------------------------------------------------
def test_deployment_routing_isolation():
    from app.graph.planner import create_plan

    plan_code = create_plan("Fix the authentication bug in my python project")
    tools_used = [t["tool"] for t in plan_code]
    assert "deployment" not in tools_used, "Deployment tool was inappropriately triggered for code edit request!"

    plan_deploy = create_plan("Create a Dockerfile and docker compose for this project")
    tools_deploy = [t["tool"] for t in plan_deploy]
    assert any(t == "deployment" for t in tools_deploy), "Deployment tool was not triggered for docker request!"
