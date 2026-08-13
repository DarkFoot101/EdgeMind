"""
Environment checks for EdgeMind V2.
"""

import shutil
import sqlite3
import subprocess
from pathlib import Path

import ollama

from app.resources.system_monitor import get_system_resources
from app.setup.models import REQUIRED_MODELS


def check_python() -> bool:
    return True


def check_ram() -> bool:
    resources = get_system_resources()
    return resources["ram_available_gb"] >= 4.0


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
    try:
        ollama.list()
        return True
    except Exception:
        return False


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


def installed_models() -> list[str]:
    try:
        response = ollama.list()
        names = []
        models_list = getattr(response, "models", None) or response.get("models", [])
        for item in models_list:
            if hasattr(item, "model"):
                names.append(item.model)
            elif isinstance(item, dict) and "name" in item:
                names.append(item["name"])
            elif isinstance(item, dict) and "model" in item:
                names.append(item["model"])
        return names
    except Exception:
        return []


def missing_models() -> list[str]:
    installed = installed_models()
    missing = []
    for required in REQUIRED_MODELS:
        # Match required string prefix (e.g., phi3:mini matches phi3:mini:latest or phi3:mini)
        req_clean = required.split(":")[0] + ":" + required.split(":")[1] if ":" in required else required
        found = False
        for inst in installed:
            if inst == required or inst.startswith(req_clean):
                found = True
                break
        if not found:
            missing.append(required)

    return missing