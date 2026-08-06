"""
Environment checks for EdgeMind.
"""

import shutil
import sqlite3
import subprocess
from pathlib import Path

import ollama

from app.resources.system_monitor import get_system_resources
from app.setup.models import REQUIRED_MODELS


def check_python():
    return True

def check_ram():
    resources = get_system_resources()
    return resources["ram_available_gb"] >= 4


def check_disk():
    usage = shutil.disk_usage(Path.cwd())
    free_gb = usage.free / (1024 ** 3)
    return free_gb >= 5


def check_sqlite():
    try:
        sqlite3.connect(":memory:")
        return True
    except Exception:
        return False


def check_ollama():
    try:
        ollama.list()
        return True
    except Exception:
        return False


def start_ollama():
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def installed_models():
    try:
        response = ollama.list()
        if hasattr(response, "models"):
            return [model.model for model in response.models]

        # Old API
        return [model["name"] for model in response["models"]]

    except Exception:
        return []

def missing_models():
    installed = installed_models()
    missing = []
    for required in REQUIRED_MODELS:
        if required not in installed:
            missing.append(required)

    return missing