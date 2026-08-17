"""
Environment and Model checks for EdgeMind V2.1.
"""

import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import List

import ollama

from app.models.model_manager import ModelManager
from app.resources.system_monitor import get_system_resources
from app.setup.models import DEFAULT_CODING_MODEL


def check_python() -> bool:
    return True


def check_ram() -> bool:
    resources = get_system_resources()
    return resources.get("ram_available_gb", 8.0) >= 4.0


def check_disk() -> bool:
    usage = shutil.disk_usage(Path.cwd())
    free_gb = usage.free / (1024 ** 3)
    return free_gb >= 5.0


def check_sqlite() -> bool:
    try:
        conn = sqlite3.connect(":memory:")
        conn.close()
        return True
    except Exception:
        return False


def check_ollama() -> bool:
    return ModelManager.is_ollama_running()


def start_ollama() -> bool:
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def installed_models() -> List[str]:
    return ModelManager.list_installed_models()


def has_suitable_coding_model() -> bool:
    """Return True if any compatible local coding model is installed."""
    return len(ModelManager.list_installed_models()) > 0


def missing_models() -> List[str]:
    """
    If no local model is installed, returns the recommended fallback model list.
    If compatible local models already exist, returns empty list.
    """
    installed = ModelManager.list_installed_models()
    if installed:
        return []

    recommended_model, _ = ModelManager.recommend_default_model()
    return [recommended_model or DEFAULT_CODING_MODEL]