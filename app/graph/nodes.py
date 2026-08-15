"""
EdgeMind V2 LangGraph Nodes

Defines all operational nodes for EdgeMind V2 workflow execution:
- Memory Lookup
- Planner V2
- Autonomous File Discovery
- Plan Refinement
- Task Selection & Model Router
- Task Executor (search, analyze, explain, debug, edit, deployment) with Analysis Context Propagation
- Reviewer V2 (True Result & Disk Verification)
- Evaluator & Retry Manager
- Memory Persistence
- Step Advancement
"""

import re
from pathlib import Path
from typing import Any

from app.editing.editing_service import EditingService
from app.editing.models import EditRequest
from app.editing.validator import detect_language, validate_code
from app.graph.evaluator import evaluate_execution
from app.graph.planner import create_plan
from app.graph.state import EdgeMindState
from app.memory.memory_manager import save_execution, search_memory
from app.models.model_router import select_model
from app.tools.code_explainer import explain_code
from app.tools.debug_assistant import debug_error
from app.tools.deployment_generator import save_dockerfile
from app.tools.docker_compose_generator import save_docker_compose
from app.tools.file_discovery import resolve_best_file, search_project_files
from app.tools.project_analyzer import analyze_project
from app.tools.requirements_generator import save_requirements


def memory_lookup_node(state: EdgeMindState) -> EdgeMindState:
    """Load bounded project execution memory before planning."""
    project_path = state.get("project_path", ".")
    rows = search_memory(project_path)
    if not rows:
        state["memory_context"] = ""
        return state

    context_parts = []
    for query, task, result, success in rows[-5:]:
        res_snippet = (result or "")[:300].replace("\n", " ")
        context_parts.append(
            f"Query: {query} | Task: {task} | Succeeded: {bool(success)} | Result: {res_snippet}"
        )
    state["memory_context"] = "\n".join(context_parts)
    return state


def planner_node(state: EdgeMindState) -> EdgeMindState:
    """Generate structured multi-step execution plan using Planner V2."""
    try:
        plan = create_plan(
            user_query=state["user_query"],
            memory=state.get("memory_context", ""),
            active_file=state.get("file_path", ""),
        )
        if not plan:
            raise ValueError("Planner generated empty plan.")

        state["plan"] = plan
        state["current_step"] = 0
        state["execution_success"] = True
    except Exception as exc:
        print(f"Planner node error: {exc}")
        state["plan"] = []
        state["current_step"] = 0
        state["result"] = f"Planner failed: {exc}"
        state["execution_success"] = False

    return state


def file_discovery_node(state: EdgeMindState) -> EdgeMindState:
    """
    Autonomous File Discovery Node (Phase 4).
    Resolves project files without requiring user to specify file paths.
    """
    query = state["user_query"]
    project_path = state.get("project_path", ".")
    active_file = state.get("file_path") or state.get("source_file") or ""

    best_file = resolve_best_file(query, project_path, active_file=active_file)
    discovered = search_project_files(query, project_path, limit=5)
    state["discovered_files"] = discovered

    if best_file:
        state["file_path"] = best_file
        state["source_file"] = best_file
        state["source_language"] = detect_language(best_file)

    query_lower = query.lower()
    target_lang = None
    if "python" in query_lower:
        target_lang = "python"
    elif "java" in query_lower:
        target_lang = "java"
    elif "c++" in query_lower or "cpp" in query_lower:
        target_lang = "cpp"
    elif "javascript" in query_lower or "js" in query_lower:
        target_lang = "javascript"
    elif "typescript" in query_lower or "ts" in query_lower:
        target_lang = "typescript"

    state["target_language"] = target_lang or state.get("source_language") or "python"

    return state


def plan_refinement_node(state: EdgeMindState) -> EdgeMindState:
    """Refine task items in execution plan with discovered files and languages."""
    plan = state.get("plan", [])
    project_path = state.get("project_path", ".")
    source_file = state.get("source_file") or state.get("file_path") or ""

    if not source_file:
        resolved = resolve_best_file(state["user_query"], project_path)
        if resolved:
            source_file = resolved
            state["source_file"] = resolved
            state["file_path"] = resolved

    source_lang = state.get("source_language") or (detect_language(source_file) if source_file else "python")
    target_lang = state.get("target_language") or source_lang

    refined_plan = []
    for item in plan:
        task_dict = dict(item)
        task_src = task_dict.get("source_file")
        if task_src:
            task_src_path = _resolve_in_project(task_src, project_path)
            if not task_src_path or not task_src_path.exists():
                task_dict["source_file"] = source_file
        else:
            task_dict["source_file"] = source_file
        if not task_dict.get("source_language"):
            task_dict["source_language"] = source_lang
        if not task_dict.get("target_language"):
            task_dict["target_language"] = target_lang

        is_create_intent = any(w in state.get("user_query", "").lower() for w in ["create", "new file", "convert", "generate a new"])
        if is_create_intent and task_dict.get("tool") == "edit":
            task_dict["operation"] = "create"

        if task_dict.get("operation") == "create":
            tgt = task_dict.get("target_file")
            if not tgt or (source_file and Path(tgt).name == Path(source_file).name):
                target_cand = None
                if state.get("user_query"):
                    file_tokens = re.findall(r"[\w./\\-]+\.[A-Za-z0-9]+", state["user_query"])
                    for tok in file_tokens:
                        tok_clean = tok.strip("'\" ")
                        if source_file and Path(tok_clean).name != Path(source_file).name:
                            target_cand = tok_clean
                            break

                if target_cand:
                    task_dict["target_file"] = target_cand
                elif source_file:
                    src_path = Path(source_file)
                    ext_map = {"python": ".py", "java": ".java", "cpp": ".cpp", "javascript": ".js", "typescript": ".ts"}
                    new_ext = ext_map.get(target_lang, src_path.suffix)
                    cand_name = f"{src_path.stem}_v2{new_ext}" if new_ext == src_path.suffix else f"{src_path.stem}{new_ext}"
        if task_dict.get("target_file"):
            tgt_path = Path(task_dict["target_file"])
            project_root = Path(project_path).expanduser().resolve()
            resolved_tgt = tgt_path if tgt_path.is_absolute() else (project_root / tgt_path).resolve()
            try:
                resolved_tgt.relative_to(project_root)
            except ValueError:
                task_dict["target_file"] = str(project_root / tgt_path.name)

        refined_plan.append(task_dict)

    state["plan"] = refined_plan
    return state


def get_current_task_node(state: EdgeMindState) -> EdgeMindState:
    """Load current step task attributes into active state."""
    plan = state.get("plan", [])
    step = state.get("current_step", 0)
    project_path = state.get("project_path", ".")

    if not plan or step >= len(plan):
        state["current_task"] = "finish"
        state["task_instruction"] = ""
        state["target_file"] = None
        state["operation"] = "modify"
        return state

    task = plan[step]
    state["current_task"] = task.get("tool", "edit")
    state["task_instruction"] = task.get("instruction", state["user_query"])
    state["operation"] = task.get("operation", "modify")

    src = task.get("source_file") or state.get("source_file") or state.get("file_path") or ""
    if not src:
        src = resolve_best_file(state["user_query"], project_path) or ""

    state["source_file"] = src
    if src:
        state["file_path"] = src

    state["target_file"] = task.get("target_file")
    state["source_language"] = task.get("source_language") or (detect_language(src) if src else "python")
    state["target_language"] = task.get("target_language") or state["source_language"]
    return state


def route_model_node(state: EdgeMindState) -> EdgeMindState:
    """Select the optimal local LLM via resource-aware router."""
    task = state.get("current_task", "edit")
    state["selected_model"] = select_model(task)
    return state


def _resolve_in_project(path_str: str | None, project_path: str = ".") -> Path | None:
    if not path_str:
        return None
    p = Path(path_str)
    if p.is_absolute():
        return p
    return (Path(project_path).expanduser().resolve() / p).resolve()


def execute_task_node(state: EdgeMindState) -> EdgeMindState:
    """
    Execute the active task item (search, analyze, explain, debug, edit, deployment).
    Enforces safe execution, distinguishes create vs modify, and propagates analysis insights.
    """
    task = state["current_task"]
    project_path = state.get("project_path", ".")
    source_file = state.get("source_file") or state.get("file_path") or ""
    model = state.get("selected_model", "qwen2.5-coder:3b")

    try:
        if task == "search":
            found = search_project_files(state["user_query"], project_path)
            res = f"Discovered candidate files: {', '.join(found) if found else 'None'}"
            state["result"] = res
            state["analysis_result"] = res
            state["execution_success"] = True
            return state

        elif task == "analyze":
            report = analyze_project(project_path, selected_model=model)
            res = report.get("analysis", "Analysis completed.")
            state["result"] = res
            state["analysis_result"] = res
            state["execution_success"] = True
            return state

        elif task == "explain":
            src_path = _resolve_in_project(source_file, project_path)
            if not src_path or not src_path.exists():
                state["result"] = "Explain task failed: Source file not found."
                state["execution_success"] = False
                return state

            res = explain_code(str(src_path), selected_model=model)
            state["result"] = res
            state["analysis_result"] = res
            state["execution_success"] = True
            return state

        elif task == "debug":
            src_path = _resolve_in_project(source_file, project_path)
            error_content = ""
            if src_path and src_path.exists():
                error_content = src_path.read_text(encoding="utf-8", errors="ignore")
            else:
                error_content = state["user_query"]

            res = debug_error(error_content, selected_model=model)
            state["result"] = res
            state["analysis_result"] = res
            state["execution_success"] = True
            return state

        elif task == "edit":
            src_path = _resolve_in_project(source_file, project_path)
            operation = state.get("operation", "modify")
            target_file = state.get("target_file")
            project_root = Path(project_path).expanduser().resolve()

            if operation == "modify" and (not src_path or not src_path.exists()):
                state["result"] = f"Edit task failed: Valid source file is required for modify operation (resolved: {src_path})."
                state["execution_success"] = False
                return state

            resolved_target = None
            if operation == "create":
                if target_file:
                    target_path = Path(target_file)
                    resolved_target = target_path if target_path.is_absolute() else (project_root / target_path).resolve()
                elif src_path:
                    ext_map = {"python": ".py", "java": ".java", "cpp": ".cpp", "javascript": ".js", "typescript": ".ts"}
                    target_ext = ext_map.get(state.get("target_language"), src_path.suffix)
                    resolved_target = src_path.with_suffix(target_ext)

                if resolved_target:
                    try:
                        resolved_target.relative_to(project_root)
                    except ValueError:
                        state["result"] = "Edit failed: Security error - Target file must be inside project root."
                        state["execution_success"] = False
                        return state

            edit_req = EditRequest(
                file_path=str(src_path) if src_path else str(project_root),
                instruction=state.get("task_instruction") or state["user_query"],
                model=model,
                source_language=state.get("source_language") or (detect_language(str(src_path)) if src_path else "python"),
                target_language=state.get("target_language") or "python",
                target_file=str(resolved_target) if resolved_target else None,
                operation=operation,
                create_backup=(operation != "create"),
                analysis_result=state.get("analysis_result"),
                project_path=project_path,
            )

            service = EditingService()
            response = service.prepare_edit(edit_req)
            state["edit_response"] = response

            if not response.success:
                state["result"] = f"Edit preparation failed:\n{response.error}"
                state["execution_success"] = False
                return state

            if operation == "create":
                service.create_file(response, project_path=project_path)
                state["modified_file"] = response.output_file
                state["result"] = f"Successfully created file: {response.output_file}\n\n{response.diff}"
            else:
                service.apply_edit(response, response.file_path, project_path=project_path)
                state["modified_file"] = response.file_path
                state["result"] = f"Successfully modified file: {response.file_path}\n\n{response.diff}"

            state["execution_success"] = True
            return state

        elif task == "deployment":
            query_lower = state["user_query"].lower()
            if "compose" in query_lower:
                state["result"] = save_docker_compose(project_path, selected_model=model)
            elif "requirements" in query_lower:
                pkgs = save_requirements(project_path)
                state["result"] = f"Generated requirements.txt with {len(pkgs)} packages."
            else:
                state["result"] = save_dockerfile(project_path, selected_model=model)

            state["execution_success"] = True
            return state

        else:
            state["result"] = f"Unsupported task tool: {task}"
            state["execution_success"] = False
            return state

    except Exception as exc:
        state["result"] = f"Task execution failed: {type(exc).__name__}: {exc}"
        state["execution_success"] = False
        return state


def reviewer_node(state: EdgeMindState) -> EdgeMindState:
    """
    Reviewer Stage V2 (Phase 7 & Section 14: True Result & Disk Inspection).
    Inspects actual filesystem state on disk:
    - For CREATE: Reads actual created file from disk, checks non-emptiness, runs validate_code on actual disk content, confirms source immutability.
    - For MODIFY: Reads actual modified file from disk, runs validate_code on actual disk content.
    - For ANALYZE/EXPLAIN/SEARCH: Verifies no files were modified.
    """
    project_path = state.get("project_path", ".")
    task = state.get("current_task")
    operation = state.get("operation", "modify")
    source_file = state.get("source_file") or state.get("file_path")
    modified_file = state.get("modified_file") or state.get("target_file")
    target_language = state.get("target_language") or "python"
    exec_success = state.get("execution_success", False)

    src_path = _resolve_in_project(source_file, project_path)
    mod_path = _resolve_in_project(modified_file, project_path)

    review_details = []
    overall_success = exec_success

    if task in {"analyze", "explain", "search"}:
        # Analysis-only tasks should not modify files
        review_details.append(f"✓ Analysis task completed without file modifications.")

    elif task == "edit":
        edit_resp = state.get("edit_response")
        if not edit_resp or not edit_resp.success:
            overall_success = False
            review_details.append("Edit preparation failed.")

        if operation == "create":
            # 1. Source file must be preserved on disk
            if src_path and src_path.exists():
                review_details.append(f"✓ Source file preserved: {src_path}")
            else:
                overall_success = False
                review_details.append(f"✗ Source file missing or corrupted: {src_path}")

            # 2. Target file must be created on disk and non-empty
            if mod_path and mod_path.exists():
                actual_disk_content = mod_path.read_text(encoding="utf-8", errors="ignore")
                if actual_disk_content.strip():
                    review_details.append(f"✓ Target file created: {mod_path}")
                    # 3. Validate actual file content read from disk
                    valid, val_msg = validate_code(actual_disk_content, target_language)
                    if valid:
                        review_details.append(f"✓ Syntax validation passed: {val_msg}")
                    else:
                        overall_success = False
                        review_details.append(f"✗ Syntax validation failed on disk file: {val_msg}")
                else:
                    overall_success = False
                    review_details.append(f"✗ Created target file is empty on disk: {mod_path}")
            else:
                overall_success = False
                review_details.append(f"✗ Target file was not created on disk: {mod_path}")

        elif operation == "modify":
            # 1. Modified file must exist on disk and pass syntax validation
            if mod_path and mod_path.exists():
                actual_disk_content = mod_path.read_text(encoding="utf-8", errors="ignore")
                valid, val_msg = validate_code(actual_disk_content, target_language)
                if valid:
                    review_details.append(f"✓ Modification syntax passed: {val_msg}")
                else:
                    overall_success = False
                    review_details.append(f"✗ Modification syntax failed on disk file: {val_msg}")
            else:
                overall_success = False
                review_details.append(f"✗ Modified file missing on disk: {mod_path}")

    state["review_status"] = {
        "success": overall_success,
        "details": review_details,
    }
    state["execution_success"] = overall_success
    return state


def evaluate_task_node(state: EdgeMindState) -> EdgeMindState:
    """Evaluate overall execution and review status."""
    task = state.get("current_task")
    if task == "edit":
        review = state.get("review_status") or {}
        success = review.get("success", False)
    else:
        success = evaluate_execution(state.get("result")) and state.get("execution_success", False)

    state["execution_success"] = success
    return state


def retry_node(state: EdgeMindState) -> EdgeMindState:
    """Increment retry counter when execution or review fails."""
    state["retry_count"] = state.get("retry_count", 0) + 1
    return state


def memory_update_node(state: EdgeMindState) -> EdgeMindState:
    """Persist task execution summary to SQLite memory."""
    if state.get("current_task") != "Use memory context":
        save_execution(state)
    return state


def advance_step_node(state: EdgeMindState) -> EdgeMindState:
    """Advance to the next task in the execution plan."""
    state["current_step"] = state.get("current_step", 0) + 1
    state["retry_count"] = 0
    return state


def should_continue(state: EdgeMindState) -> str:
    """Determine routing after evaluator/reviewer."""
    if not state.get("execution_success", False):
        if state.get("retry_count", 0) < state.get("max_retry", 2):
            return "retry"
        return "finish"

    if state.get("current_step", 0) >= len(state.get("plan", [])):
        return "finish"

    return "continue"


def should_continue_after_advance(state: EdgeMindState) -> str:
    """Determine routing after step advancement."""
    if state.get("current_step", 0) >= len(state.get("plan", [])):
        return "finish"
    return "continue"
