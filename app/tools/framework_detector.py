"""
EdgeMind Framework & Project Context Detector.

Analyzes the target workspace to automatically identify:
1. Primary programming language and web framework (FastAPI, Flask, Django, Express, etc.).
2. Data modeling / ORM libraries (Pydantic, SQLAlchemy, Tortoise, etc.).
3. Project structure and existing key files (main.py, models.py, routes, etc.).

Prevents LLMs from hallucinating foreign frameworks (e.g., injecting Flask into FastAPI).
"""

from pathlib import Path
import re
from typing import Any, Dict, List, Optional

IGNORED_DIRS = {
    ".git",
    ".edgemind",
    "venv",
    ".venv",
    "node_modules",
    "__pycache__",
    "build",
    "dist",
    ".pytest_cache",
    "edgemind.egg-info",
}


def detect_framework_and_stack(project_path: str = ".") -> Dict[str, Any]:
    """
    Inspect project files to detect web framework, data models, and key architectural files.
    """
    root = Path(project_path).expanduser().resolve()
    if not root.is_dir():
        return {
            "framework": "Generic",
            "models_library": "None",
            "key_files": [],
            "summary": "Standard project",
        }

    detected_frameworks = set()
    detected_models = set()
    key_files: List[str] = []

    # Scan python files (limit to first 30 files for performance)
    scanned_count = 0
    for p in root.rglob("*.py"):
        if any(ign in p.parts for ign in IGNORED_DIRS) or p.name.endswith(".bak"):
            continue

        scanned_count += 1
        if scanned_count > 35:
            break

        rel_path = str(p.relative_to(root)).replace("\\", "/")
        key_files.append(rel_path)

        try:
            content = p.read_text(encoding="utf-8", errors="ignore")[:5000]
        except Exception:
            continue

        # Check Web Frameworks
        if "from fastapi" in content or "import fastapi" in content or "FastAPI(" in content:
            detected_frameworks.add("FastAPI")
        elif "from flask" in content or "import flask" in content or "Flask(" in content:
            detected_frameworks.add("Flask")
        elif "django" in content or "from django" in content:
            detected_frameworks.add("Django")

        # Check Data Models & ORM
        if "from pydantic" in content or "BaseModel" in content:
            detected_models.add("Pydantic")
        if "sqlalchemy" in content or "db.Column" in content or "declarative_base" in content:
            detected_models.add("SQLAlchemy")
        if "tortoise" in content:
            detected_models.add("Tortoise ORM")

    # Determine primary framework
    primary_framework = "Generic Python"
    if "FastAPI" in detected_frameworks:
        primary_framework = "FastAPI"
    elif "Flask" in detected_frameworks:
        primary_framework = "Flask"
    elif "Django" in detected_frameworks:
        primary_framework = "Django"

    primary_model_lib = "Pydantic" if "Pydantic" in detected_models else ("SQLAlchemy" if "SQLAlchemy" in detected_models else "Standard Classes")

    # Generate architectural summary prompt guidance
    summary_parts = [f"Web Framework: {primary_framework}"]
    if detected_models:
        summary_parts.append(f"Model/Schema Library: {', '.join(detected_models)}")

    key_summary = f"Identified Stack: {primary_framework} with {primary_model_lib}."
    if primary_framework == "FastAPI":
        key_summary += " Architecture Rule: Use FastAPI route decorators (@app.get, @app.post) and Pydantic BaseModel for data schemas. NEVER use Flask or Flask-SQLAlchemy syntax."
    elif primary_framework == "Flask":
        key_summary += " Architecture Rule: Use Flask application context and route decorators (@app.route)."

    return {
        "framework": primary_framework,
        "models_library": primary_model_lib,
        "key_files": sorted(key_files)[:15],
        "summary": key_summary,
    }
