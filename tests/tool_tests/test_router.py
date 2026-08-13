"""Pytest test suite for Model Router V2."""

from app.models.model_router import select_model


def test_model_router_selection():
    assert select_model("planner") == "phi3:mini"
    assert select_model("search") == "phi3:mini"
    assert select_model("explain") == "phi3:mini"
    assert select_model("edit") == "qwen2.5-coder:3b"
    assert select_model("debug") == "qwen2.5-coder:3b"
    assert select_model("deployment") == "qwen2.5-coder:3b"