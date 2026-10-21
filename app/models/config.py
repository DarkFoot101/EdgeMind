"""
EdgeMind User Configuration & Model Preference Manager.

Stores persistent user preferences in ~/.edgemind/config.json.
Allows users to switch active LLM models across CLI, API, and IDE extensions.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import ollama

CONFIG_DIR = Path.home() / ".edgemind"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _read_config() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_config(data: Dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def get_configured_model() -> Optional[str]:
    """Return user's explicitly selected model tag, or None if using auto-routing."""
    cfg = _read_config()
    model = cfg.get("selected_model")
    return str(model).strip() if model else None


def set_configured_model(model_name: str) -> str:
    """Set and persist user's chosen model tag."""
    clean_name = model_name.strip()
    cfg = _read_config()
    cfg["selected_model"] = clean_name
    _write_config(cfg)
    return clean_name


def clear_configured_model() -> None:
    """Clear explicit model override and revert to dynamic resource-aware routing."""
    cfg = _read_config()
    if "selected_model" in cfg:
        del cfg["selected_model"]
        _write_config(cfg)


def get_model_catalog() -> List[Dict[str, Any]]:
    """
    Return all installed Ollama models with parameter sizes, disk footprint, and active status.
    """
    active = get_configured_model()
    try:
        res = ollama.list()
        raw_list = getattr(res, "models", None) or res.get("models", [])
        catalog = []
        for item in raw_list:
            name = getattr(item, "model", None) or (item.get("model") if isinstance(item, dict) else str(item))
            if not name and isinstance(item, dict):
                name = item.get("name", "")
            if not name:
                continue

            size_bytes = getattr(item, "size", None) or (item.get("size") if isinstance(item, dict) else 0) or 0
            size_gb = round(size_bytes / (1024 ** 3), 2)

            details = getattr(item, "details", None) or (item.get("details") if isinstance(item, dict) else {}) or {}
            param_size = getattr(details, "parameter_size", None) or (details.get("parameter_size") if isinstance(details, dict) else "")

            catalog.append({
                "model": name,
                "size_gb": f"{size_gb} GB",
                "parameter_size": param_size or "N/A",
                "is_active": (name == active) if active else False,
            })

        # If no explicit active model, mark the default first coding model as active
        if catalog and not any(m["is_active"] for m in catalog):
            catalog[0]["is_active"] = True

        return catalog
    except Exception:
        fallback = active or "qwen2.5-coder:3b"
        return [{
            "model": fallback,
            "size_gb": "~2.0 GB",
            "parameter_size": "3B",
            "is_active": True,
        }]
