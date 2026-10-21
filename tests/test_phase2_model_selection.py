"""
Unit tests for Phase 2: User Model Selection & Orchestration Override.
1. Persistent config get/set/clear.
2. Model catalog discovery.
3. Model router respects user-configured model override.
4. JSON-RPC get_models and set_model endpoints.
5. CLI show_model_menu selection logic.
"""

from pathlib import Path
import pytest

from app.models.config import (
    clear_configured_model,
    get_configured_model,
    get_model_catalog,
    set_configured_model,
)
from app.models.model_router import select_model
from app.cli.rpc import handle_request
from app.editing.editing_service import EditingService
from app.cli.session import SessionState
from app.cli.commands import show_model_menu


def test_config_model_get_set_clear(tmp_path, monkeypatch):
    test_cfg_dir = tmp_path / ".edgemind"
    test_cfg_file = test_cfg_dir / "config.json"
    monkeypatch.setattr("app.models.config.CONFIG_DIR", test_cfg_dir)
    monkeypatch.setattr("app.models.config.CONFIG_FILE", test_cfg_file)

    # 1. Default should be None
    assert get_configured_model() is None

    # 2. Set model
    chosen = set_configured_model("qwen2.5-coder:7b")
    assert chosen == "qwen2.5-coder:7b"
    assert get_configured_model() == "qwen2.5-coder:7b"

    # 3. Router should now return the configured model
    assert select_model("edit") == "qwen2.5-coder:7b"
    assert select_model("planner") == "qwen2.5-coder:7b"

    # 4. Clear model
    clear_configured_model()
    assert get_configured_model() is None


def test_model_catalog_structure(tmp_path, monkeypatch):
    catalog = get_model_catalog()
    assert isinstance(catalog, list)
    assert len(catalog) > 0
    first = catalog[0]
    assert "model" in first
    assert "size_gb" in first
    assert "parameter_size" in first
    assert "is_active" in first


def test_rpc_model_endpoints(tmp_path, monkeypatch):
    test_cfg_dir = tmp_path / ".edgemind"
    test_cfg_file = test_cfg_dir / "config.json"
    monkeypatch.setattr("app.models.config.CONFIG_DIR", test_cfg_dir)
    monkeypatch.setattr("app.models.config.CONFIG_FILE", test_cfg_file)

    service = EditingService()

    # 1. get_models
    get_req = {"id": 10, "method": "get_models", "params": {}}
    res = handle_request(get_req, service)
    assert res["id"] == 10
    assert "active_model" in res["result"]
    assert "catalog" in res["result"]

    # 2. set_model
    set_req = {"id": 11, "method": "set_model", "params": {"model": "custom-coder:14b"}}
    res_set = handle_request(set_req, service)
    assert res_set["id"] == 11
    assert res_set["result"]["active_model"] == "custom-coder:14b"
    assert get_configured_model() == "custom-coder:14b"


def test_cli_show_model_menu_direct_args(tmp_path, monkeypatch):
    test_cfg_dir = tmp_path / ".edgemind"
    test_cfg_file = test_cfg_dir / "config.json"
    monkeypatch.setattr("app.models.config.CONFIG_DIR", test_cfg_dir)
    monkeypatch.setattr("app.models.config.CONFIG_FILE", test_cfg_file)

    session = SessionState()

    # 1. Select by direct name
    show_model_menu(session, "qwen2.5-coder:3b")
    assert session.selected_model == "qwen2.5-coder:3b"
    assert get_configured_model() == "qwen2.5-coder:3b"

    # 2. Reset to auto
    show_model_menu(session, "auto")
    assert session.selected_model == "Auto-Routing"
    assert get_configured_model() is None

    # 3. Model tag with "model" in name
    show_model_menu(session, "custom-model:latest")
    assert session.selected_model == "custom-model:latest"
    assert get_configured_model() == "custom-model:latest"


def test_cli_command_prefix_slicing(tmp_path, monkeypatch):
    test_cfg_dir = tmp_path / ".edgemind"
    test_cfg_file = test_cfg_dir / "config.json"
    monkeypatch.setattr("app.models.config.CONFIG_DIR", test_cfg_dir)
    monkeypatch.setattr("app.models.config.CONFIG_FILE", test_cfg_file)

    session = SessionState()

    for cmd in ["/model model-expert:7b", "model model-expert:7b"]:
        if cmd.startswith("/model"):
            arg = cmd[len("/model"):].strip()
        else:
            arg = cmd[len("model"):].strip()
        show_model_menu(session, arg)
        assert session.selected_model == "model-expert:7b"
        assert get_configured_model() == "model-expert:7b"

