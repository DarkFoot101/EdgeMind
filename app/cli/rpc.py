"""
EdgeMind JSON-RPC Standard I/O Bridge.

Provides a lightweight, zero-dependency IPC bridge for IDE extensions (VS Code, JetBrains).
Reads JSON-RPC messages from stdin and outputs responses to stdout.
Requires zero external networking or third-party web frameworks.
"""

import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict

# Enforce EdgeMind root priority and isolate 'app' package against workspace collisions
_edgemind_root = str(Path(__file__).resolve().parent.parent.parent)
if _edgemind_root in sys.path:
    sys.path.remove(_edgemind_root)
sys.path.insert(0, _edgemind_root)

import app
_edgemind_app_dir = str(Path(__file__).resolve().parent.parent)
app.__path__ = [_edgemind_app_dir]

if "app.models" in sys.modules and not hasattr(sys.modules["app.models"], "__path__"):
    del sys.modules["app.models"]

from app.editing.editing_service import EditingService
from app.editing.models import EditRequest, EditResponse


def handle_request(req_data: Dict[str, Any], service: EditingService) -> Dict[str, Any]:
    req_id = req_data.get("id")
    method = req_data.get("method")
    params = req_data.get("params", {})

    if method == "ping":
        return {"id": req_id, "result": {"status": "ok", "message": "EdgeMind RPC daemon active"}}

    elif method == "prepare_edit":
        file_path = params.get("file_path", "")
        instruction = params.get("instruction", "")
        project_path = params.get("project_path", ".")
        target_symbol = params.get("target_symbol")
        start_line = params.get("start_line")
        end_line = params.get("end_line")
        candidates_count = params.get("candidates_count", 1)
        from app.tools.framework_detector import detect_framework_and_stack
        stack_info = detect_framework_and_stack(project_path)

        req = EditRequest(
            file_path=file_path,
            project_path=project_path,
            instruction=instruction,
            target_symbol=target_symbol,
            start_line=start_line,
            end_line=end_line,
            candidates_count=candidates_count,
            project_framework=stack_info.get("summary"),
        )

        resp = service.prepare_edit(req)
        return {
            "id": req_id,
            "result": {
                "success": resp.success,
                "file_path": resp.file_path,
                "original_code": resp.original_code,
                "modified_code": resp.modified_code,
                "diff": resp.diff,
                "validation_message": resp.validation_message,
                "error": resp.error,
                "operation": str(resp.operation),
                "source_hash": resp.source_hash,
                "modified_hash": resp.modified_hash,
                "metrics": resp.metrics.to_dict() if resp.metrics else None,
                "selected_candidate_id": resp.selected_candidate_id,
            },
        }

    elif method == "apply_edit":
        file_path = params.get("file_path", "")
        modified_code = params.get("modified_code", "")
        source_hash = params.get("source_hash")
        project_path = params.get("project_path", ".")
        force = params.get("force", False)

        resp = EditResponse(
            success=True,
            file_path=file_path,
            original_code="",
            modified_code=modified_code,
            diff="",
            validation_message="OK",
            backup_path=None,
            error=None,
            source_hash=source_hash,
        )

        applied = service.apply_edit(resp, file_path, force=force, project_path=project_path)
        return {"id": req_id, "result": {"success": applied}}

    elif method == "get_models":
        from app.models.config import get_configured_model, get_model_catalog
        return {
            "id": req_id,
            "result": {
                "active_model": get_configured_model() or "qwen2.5-coder:3b",
                "catalog": get_model_catalog(),
            },
        }

    elif method == "set_model":
        model_name = params.get("model", "").strip()
        from app.models.config import set_configured_model
        chosen = set_configured_model(model_name)
        return {"id": req_id, "result": {"active_model": chosen}}

    else:
        return {"id": req_id, "error": f"Unknown RPC method: {method}"}


def main():
    service = EditingService()
    # Read newline-delimited JSON messages from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req_data = json.loads(line)
            response = handle_request(req_data, service)
        except Exception as e:
            response = {
                "id": None,
                "error": f"RPC Exception: {type(e).__name__}: {str(e)}",
                "traceback": traceback.format_exc(),
            }

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
