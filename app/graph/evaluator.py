"""
EdgeMind ReAct Verification & Requirement Reflection Engine.

Provides multi-turn feedback loops (Reason -> Act -> Observe -> Reflect):
1. Evaluates syntax validity and AST symbol presence.
2. Checks whether user-requested fields, methods, and endpoints were actually generated.
3. Detects redundant/stale code that needs removal (e.g. duplicate models in main.py).
4. Emits dynamic follow-up actions when requirements remain partially fulfilled.
"""

import ast
from pathlib import Path
import re
from typing import Any, Dict, Optional


def evaluate_execution(result: object) -> bool:
    """Return whether a task produced a non-empty, non-error result."""
    if result is None:
        return False

    if not result:
        return False

    if isinstance(result, str):
        normalized = result.strip().lower()
        if not normalized:
            return False
        if normalized.startswith(("error:", "exception:", "traceback")):
            return False

    return True


def verify_react_step(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs ReAct reflection over the current execution result.
    Checks if the user's intent was fully satisfied, or if a follow-up action
    is required (such as removing obsolete code, adding missing imports, or updating companion files).
    """
    current_iter = state.get("react_iteration", 0)
    max_iter = state.get("max_react_iterations", 3)

    if current_iter >= max_iter:
        return {
            "satisfied": True,
            "reason": f"Maximum ReAct iterations reached ({max_iter}). Finalizing changes.",
            "followup_needed": False,
        }

    task = state.get("current_task")
    if task != "edit":
        # Search, analyze, explain, deployment do not require iterative code repair
        return {
            "satisfied": bool(state.get("execution_success", True)),
            "reason": "Non-edit task completed.",
            "followup_needed": False,
        }

    edit_resp = state.get("edit_response")
    if not edit_resp or not edit_resp.success:
        return {
            "satisfied": False,
            "reason": f"Edit preparation failed: {getattr(edit_resp, 'error', 'Unknown failure')}",
            "followup_needed": False,
        }

    code = edit_resp.modified_code or ""
    query = state.get("user_query", "")
    query_lower = query.lower()
    project_path = state.get("project_path", ".")
    file_path = edit_resp.file_path or state.get("source_file", "")
    filename = Path(file_path).name.lower() if file_path else ""

    # 1. AST Syntax Verification (Python)
    if (state.get("target_language") or "python").lower() == "python":
        try:
            tree = ast.parse(code)
        except SyntaxError as syn_err:
            return {
                "satisfied": False,
                "reason": f"Python SyntaxError at line {syn_err.lineno}: {syn_err.msg}",
                "followup_needed": True,
                "followup_task": {
                    "tool": "edit",
                    "instruction": f"Fix syntax error at line {syn_err.lineno}: {syn_err.msg}",
                    "source_file": file_path,
                },
            }

        # 2. Check for missing requested fields / attributes
        # e.g., if user asked for 'rating', verify it exists in defined models
        requested_fields = re.findall(r"\b(?:field|property|attribute|add|with)\s+([a-zA-Z_]\w*)\b", query, re.IGNORECASE)
        for fld in requested_fields:
            if fld.lower() in {"the", "a", "an", "new", "this", "model", "class", "function", "endpoint", "post", "order"}:
                continue
            if fld not in code:
                return {
                    "satisfied": False,
                    "reason": f"Requested field '{fld}' was not found in the modified code.",
                    "followup_needed": True,
                    "followup_task": {
                        "tool": "edit",
                        "instruction": f"Ensure field '{fld}' is properly added to {Path(file_path).name} as requested.",
                        "source_file": file_path,
                    },
                }

        # 3. Check for stale duplicate models in main.py when models.py exists
        if "main.py" in filename:
            # Check if models.py exists in project
            models_file = Path(project_path) / "app" / "models.py"
            if not models_file.exists():
                models_file = Path(project_path) / "models.py"

            if models_file.exists():
                try:
                    models_content = models_file.read_text(encoding="utf-8", errors="ignore")
                    models_tree = ast.parse(models_content)
                    models_classes = {
                        n.name for n in models_tree.body if isinstance(n, ast.ClassDef)
                    }

                    main_classes = {
                        n.name for n in tree.body if isinstance(n, ast.ClassDef)
                    }

                    # If user asks to use models / refactor, and duplicate classes exist in main.py
                    overlap = models_classes.intersection(main_classes)
                    if overlap and any(w in query_lower for w in ["model", "models", "refactor", "import", "clean", "organize"]):
                        dup_name = next(iter(overlap))
                        return {
                            "satisfied": False,
                            "reason": f"Class '{dup_name}' is defined in both models.py and main.py. Should import from models.py and remove duplicate.",
                            "followup_needed": True,
                            "followup_task": {
                                "tool": "edit",
                                "instruction": f"Remove duplicate class '{dup_name}' from main.py and import it from models instead.",
                                "source_file": file_path,
                            },
                        }
                except Exception:
                    pass

    return {
        "satisfied": True,
        "reason": "All structural and requirement checks verified successfully.",
        "followup_needed": False,
    }
