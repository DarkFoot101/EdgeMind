"""
Unit test for namespace collision resilience:
Verifies that when a target project has an 'app' directory (e.g. FastAPI / Flask project)
containing 'models.py', EdgeMind does not collide or crash with:
'ModuleNotFoundError: No module named app.models.ollama_client; app.models is not a package'.
"""

import sys
from pathlib import Path
import pytest


def test_namespace_isolation_against_user_app(tmp_path, monkeypatch):
    # Create fake user project at tmp_path mimicking /Users/akhi/api/app/models.py
    fake_project_app = tmp_path / "app"
    fake_project_app.mkdir(parents=True, exist_ok=True)
    fake_models_file = fake_project_app / "models.py"
    fake_models_file.write_text("class UserApiModel:\n    pass\n")

    # Simulate sys.path pollution by putting fake project at sys.path[0]
    monkeypatch.syspath_prepend(str(tmp_path))

    # Import EdgeMind rpc module
    import app.cli.rpc as rpc
    from app.editing.editing_service import EditingService

    service = EditingService()
    ping_resp = rpc.handle_request({"id": 1, "method": "ping", "params": {}}, service)
    assert ping_resp["id"] == 1
    assert ping_resp["result"]["status"] == "ok"

    # Ensure app.models.ollama_client and app.models.model_router can be imported
    from app.models.model_router import select_model
    model = select_model("edit")
    assert isinstance(model, str)
    assert len(model) > 0
