"""Pytest suite for EdgeMind ReAct Verification & Reflection Loop."""

import ast
from pathlib import Path
from app.editing.models import EditResponse
from app.graph.evaluator import verify_react_step


def test_react_verification_detects_missing_requested_field():
    edit_resp = EditResponse(
        success=True,
        file_path="app/main.py",
        original_code="",
        modified_code="""
class Post:
    title: str
    content: str
""",
        diff="",
        validation_message="Valid",
        backup_path=None,
        error=None,
    )
    state = {
        "user_query": "add rating field to Post",
        "current_task": "edit",
        "edit_response": edit_resp,
        "target_language": "python",
        "react_iteration": 0,
        "max_react_iterations": 3,
    }

    res = verify_react_step(state)
    assert res["satisfied"] is False
    assert res["followup_needed"] is True
    assert "rating" in res["reason"]
    assert res["followup_task"]["tool"] == "edit"


def test_react_verification_detects_duplicate_model_in_main(tmp_path):
    # Setup project with app/models.py defining Post
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True)
    models_file = app_dir / "models.py"
    models_file.write_text("class Post:\n    title: str\n    author: str\n", encoding="utf-8")

    # main.py still defines duplicate Post
    main_code = """
class Post:
    title: str
    content: str

def get_posts():
    return []
"""
    edit_resp = EditResponse(
        success=True,
        file_path=str(app_dir / "main.py"),
        original_code="",
        modified_code=main_code,
        diff="",
        validation_message="Valid",
        backup_path=None,
        error=None,
    )
    state = {
        "user_query": "refactor main.py to use models from models.py",
        "project_path": str(tmp_path),
        "source_file": str(app_dir / "main.py"),
        "current_task": "edit",
        "edit_response": edit_resp,
        "target_language": "python",
        "react_iteration": 0,
        "max_react_iterations": 3,
    }

    res = verify_react_step(state)
    assert res["satisfied"] is False
    assert res["followup_needed"] is True
    assert "duplicate" in res["reason"].lower()
    assert "Post" in res["reason"]


def test_react_verification_bounded_by_max_iterations():
    edit_resp = EditResponse(
        success=True,
        file_path="app/main.py",
        original_code="",
        modified_code="x = 10\n",
        diff="",
        validation_message="Valid",
        backup_path=None,
        error=None,
    )
    state = {
        "user_query": "add rating field to Post",
        "current_task": "edit",
        "edit_response": edit_resp,
        "target_language": "python",
        "react_iteration": 3,
        "max_react_iterations": 3,
    }

    res = verify_react_step(state)
    assert res["satisfied"] is True
    assert res["followup_needed"] is False
    assert "Maximum ReAct iterations reached" in res["reason"]
