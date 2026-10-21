"""
Unit tests for Phase 1:
1. Framework & Stack Context Detection (FastAPI, Flask, Django, Pydantic, SQLAlchemy)
2. Recursive File Resolution (resolving 'models.py' -> 'app/models.py')
3. Bare Stem Matching ('models' -> 'app/models.py')
4. Existing File Preference in Plan Refinement (forcing operation: modify)
"""

from pathlib import Path
import pytest

from app.tools.framework_detector import detect_framework_and_stack
from app.tools.file_discovery import resolve_best_file
from app.graph.nodes import _resolve_in_project, plan_refinement_node


def test_framework_detector_fastapi_pydantic(tmp_path):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    main_f = app_dir / "main.py"
    main_f.write_text(
        "from fastapi import FastAPI\nfrom pydantic import BaseModel\n\napp = FastAPI()\n",
        encoding="utf-8",
    )

    info = detect_framework_and_stack(str(tmp_path))
    assert info["framework"] == "FastAPI"
    assert info["models_library"] == "Pydantic"
    assert "FastAPI" in info["summary"]
    assert "app/main.py" in info["key_files"]


def test_framework_detector_flask(tmp_path):
    app_f = tmp_path / "app.py"
    app_f.write_text(
        "from flask import Flask\nimport flask_sqlalchemy\napp = Flask(__name__)\n",
        encoding="utf-8",
    )

    info = detect_framework_and_stack(str(tmp_path))
    assert info["framework"] == "Flask"
    assert "Flask" in info["summary"]


def test_recursive_file_resolution(tmp_path):
    sub = tmp_path / "app" / "internal"
    sub.mkdir(parents=True)
    target = sub / "models.py"
    target.write_text("class Post: pass\n", encoding="utf-8")

    # 1. Test resolve_best_file with query mentioning 'models.py'
    resolved = resolve_best_file("Add Post model in models.py", project_path=str(tmp_path))
    assert resolved is not None
    assert Path(resolved).resolve() == target.resolve()

    # 2. Test resolve_best_file with query mentioning bare stem 'models'
    resolved_stem = resolve_best_file("Update post crud in models", project_path=str(tmp_path))
    assert resolved_stem is not None
    assert Path(resolved_stem).resolve() == target.resolve()

    # 3. Test _resolve_in_project with simple relative name
    resolved_p = _resolve_in_project("models.py", project_path=str(tmp_path))
    assert resolved_p is not None
    assert resolved_p.resolve() == target.resolve()


def test_plan_refinement_prefers_modify_when_file_exists(tmp_path):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    mod_f = app_dir / "models.py"
    mod_f.write_text("class ExistingModel: pass\n", encoding="utf-8")

    state = {
        "user_query": "create a new Post model in models.py",
        "project_path": str(tmp_path),
        "source_file": None,
        "file_path": None,
        "plan": [
            {
                "tool": "edit",
                "operation": "create",
                "instruction": "create a new Post model in models.py",
                "source_file": None,
                "target_file": "models.py",
            }
        ],
    }

    refined_state = plan_refinement_node(state)
    refined_plan = refined_state["plan"]
    assert len(refined_plan) == 1

    # Because app/models.py already exists, it MUST NOT create a new file; it must modify existing file!
    assert refined_plan[0]["operation"] == "modify"
    assert Path(refined_plan[0]["source_file"]).resolve() == mod_f.resolve()
    assert refined_plan[0]["target_file"] is None
