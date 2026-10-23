"""
EdgeMind V2.1 LangGraph Nodes

Defines all operational nodes for EdgeMind V2.1 workflow execution:
- Memory Lookup
- Planner V2
- Autonomous File Discovery & Activity Streaming
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
from app.editing.scope import infer_target_symbol_from_code
from app.editing.validator import detect_language, validate_code
from app.events.activity_stream import ActivityStream, EventType
from app.graph.evaluator import evaluate_execution, verify_react_step
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
    ActivityStream.emit("Understanding request...", EventType.PROGRESS, stage="planner")
    ActivityStream.emit("Creating execution plan...", EventType.PROGRESS, stage="planner")

    try:
        plan = create_plan(
            user_query=state["user_query"],
            memory=state.get("memory_context", ""),
            active_file=state.get("file_path", ""),
            project_path=state.get("project_path", "."),
        )
        if not plan:
            raise ValueError("Planner generated empty plan.")

        state["plan"] = plan
        state["current_step"] = 0
        state["execution_success"] = True

        task_tools = [t.get("tool", "") for t in plan if t.get("tool")]
        tools_str = " → ".join(t.capitalize() for t in task_tools) if task_tools else "Execute"
        ActivityStream.emit(f"{tools_str}", EventType.ACTION, stage="planner")
        ActivityStream.emit(f"{len(plan)} task{'s' if len(plan) != 1 else ''} planned", EventType.SUCCESS, stage="planner")

    except Exception as exc:
        state["plan"] = []
        state["current_step"] = 0
        state["result"] = f"Planner failed: {exc}"
        state["execution_success"] = False
        ActivityStream.emit(f"Planner failed: {exc}", EventType.ERROR, stage="planner")

    return state


def file_discovery_node(state: EdgeMindState) -> EdgeMindState:
    """
    Autonomous File Discovery Node (Phase 4).
    Resolves project files without requiring user to specify file paths.
    """
    ActivityStream.emit("Identifying source file...", EventType.PROGRESS, stage="file_discovery")

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
        ActivityStream.emit(f"Found {Path(best_file).name}", EventType.SUCCESS, stage="file_discovery")
    else:
        ActivityStream.emit("No specific source file required", EventType.INFO, stage="file_discovery")

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
    ActivityStream.emit("Determining requested operation...", EventType.PROGRESS, stage="plan_refinement")

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

        # Check if requested target_file (or source_file) already exists in project:
        target_name = task_dict.get("target_file") or task_dict.get("source_file") or source_file
        existing_target = _resolve_in_project(target_name, project_path) if target_name else None

        # Cross-language conversion check (e.g. Java -> Python)
        is_cross_language = bool(
            task_dict.get("source_language")
            and task_dict.get("target_language")
            and task_dict["source_language"] != task_dict["target_language"]
        )

        if existing_target and existing_target.exists() and existing_target.is_file() and not is_cross_language:
            # Existing file with same language -> IN-PLACE MODIFY
            task_dict["operation"] = "modify"
            task_dict["source_file"] = str(existing_target)
            task_dict["target_file"] = None
        else:
            # File creation logic (new file or cross-language conversion)
            is_create_intent = any(w in state.get("user_query", "").lower() for w in ["new file", "create a file", "create file", "convert to", "convert "])
            if (is_create_intent or is_cross_language) and task_dict.get("tool") == "edit":
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
                        task_dict["target_file"] = f"{src_path.stem}_v2{new_ext}" if new_ext == src_path.suffix else f"{src_path.stem}{new_ext}"

            if task_dict.get("target_file"):
                tgt_path = Path(task_dict["target_file"])
                project_root = Path(project_path).expanduser().resolve()
                resolved_tgt = tgt_path if tgt_path.is_absolute() else (project_root / tgt_path).resolve()
                try:
                    resolved_tgt.relative_to(project_root)
                except ValueError:
                    task_dict["target_file"] = str(project_root / tgt_path.name)

        # Infer scoped editing (symbol or line range) if not explicitly set
        if task_dict.get("tool") == "edit":
            if not task_dict.get("target_symbol"):
                sym_match = re.search(
                    r"\b(?:function|def|method|class|symbol)\s+([a-zA-Z_]\w*)\b",
                    state.get("user_query", ""),
                    re.IGNORECASE,
                )
                if not sym_match:
                    sym_match = re.search(
                        r"\b([a-zA-Z_]\w*)\s+(?:function|method|class)\b",
                        state.get("user_query", ""),
                        re.IGNORECASE,
                    )
                if sym_match:
                    cand_sym = sym_match.group(1).strip("() '\"")
                    if cand_sym.lower() not in {"the", "a", "an", "this", "that", "python", "java", "main", "new"}:
                        task_dict["target_symbol"] = cand_sym
                        task_dict["scope_type"] = "symbol"

                # If still not found, inspect AST of source_file against user_query
                if not task_dict.get("target_symbol") and task_dict.get("source_file"):
                    src_f = _resolve_in_project(task_dict["source_file"], project_path)
                    if src_f and src_f.exists() and src_f.is_file():
                        try:
                            src_text = src_f.read_text(encoding="utf-8", errors="ignore")
                            inferred_sym = infer_target_symbol_from_code(
                                src_text,
                                state.get("user_query", ""),
                                task_dict.get("source_language", "python")
                            )
                            if inferred_sym:
                                task_dict["target_symbol"] = inferred_sym
                                task_dict["scope_type"] = "symbol"
                                ActivityStream.emit(f"Scoped edit to symbol '{inferred_sym}'", EventType.PROGRESS, stage="plan_refinement")
                        except Exception:
                            pass

            if not task_dict.get("start_line"):
                range_match = re.search(
                    r"\blines?\s+(\d+)\s*(?:to|-)\s*(\d+)\b",
                    state.get("user_query", ""),
                    re.IGNORECASE,
                )
                if range_match:
                    task_dict["start_line"] = int(range_match.group(1))
                    task_dict["end_line"] = int(range_match.group(2))
                    task_dict["scope_type"] = "line_range"

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
        state["target_symbol"] = None
        state["start_line"] = None
        state["end_line"] = None
        state["scope_type"] = None
        state["search_block"] = None
        state["replace_block"] = None
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

    state["target_symbol"] = task.get("target_symbol")
    state["start_line"] = task.get("start_line")
    state["end_line"] = task.get("end_line")
    state["scope_type"] = task.get("scope_type")
    state["search_block"] = task.get("search_block")
    state["replace_block"] = task.get("replace_block")
    return state


def route_model_node(state: EdgeMindState) -> EdgeMindState:
    """Select the optimal local LLM via resource-aware router."""
    task = state.get("current_task", "edit")
    state["selected_model"] = select_model(task)
    return state


def _resolve_in_project(path_str: str | None, project_path: str = ".") -> Path | None:
    if not path_str:
        return None
    project_root = Path(project_path).expanduser().resolve()
    p = Path(path_str)
    if p.is_absolute():
        if p.exists():
            return p
        # Check recursive match for basename if absolute path does not exist
        search_name = p.name.lower()
        for match in project_root.rglob("*"):
            if match.is_file() and match.name.lower() == search_name:
                from app.tools.file_discovery import IGNORED_DIRS
                if not any(ign in match.parts for ign in IGNORED_DIRS) and not match.name.endswith(".bak"):
                    return match.resolve()
        return p

    # Direct relative check
    direct = (project_root / p).resolve()
    if direct.exists():
        return direct

    # Recursive check for basename in project subdirectories (e.g. models.py -> app/models.py)
    search_name = p.name.lower()
    for match in project_root.rglob("*"):
        if match.is_file() and match.name.lower() == search_name:
            from app.tools.file_discovery import IGNORED_DIRS
            if not any(ign in match.parts for ign in IGNORED_DIRS) and not match.name.endswith(".bak"):
                return match.resolve()

    return direct


def execute_task_node(state: EdgeMindState) -> EdgeMindState:
    """
    Execute the active task item (search, analyze, explain, debug, edit, deployment).
    Enforces safe execution, distinguishes create vs modify, and propagates analysis insights.
    """
    task = state["current_task"]
    project_path = state.get("project_path", ".")
    source_file = state.get("source_file") or state.get("file_path") or ""
    model = state.get("selected_model", "qwen2.5-coder:3b")
    src_name = Path(source_file).name if source_file else "project"

    try:
        if task == "search":
            ActivityStream.emit(f"Searching candidate files for '{state['user_query']}'...", EventType.PROGRESS, stage="executor")
            found = search_project_files(state["user_query"], project_path)
            res = f"Discovered candidate files: {', '.join(found) if found else 'None'}"
            state["result"] = res
            state["analysis_result"] = res
            state["execution_success"] = True
            ActivityStream.emit(f"Search complete: found {len(found)} candidate(s)", EventType.SUCCESS, stage="executor")
            return state

        elif task == "analyze":
            ActivityStream.emit(f"Analyzing {src_name}...", EventType.PROGRESS, stage="executor")
            report = analyze_project(project_path, selected_model=model)
            res = report.get("analysis", "Analysis completed.")
            state["result"] = res
            state["analysis_result"] = res
            state["execution_success"] = True
            ActivityStream.emit("Analysis complete", EventType.SUCCESS, stage="executor")
            return state

        elif task == "explain":
            src_path = _resolve_in_project(source_file, project_path)
            if not src_path or not src_path.exists():
                state["result"] = "Explain task failed: Source file not found."
                state["execution_success"] = False
                ActivityStream.emit("Explain failed: Source file not found", EventType.ERROR, stage="executor")
                return state

            ActivityStream.emit(f"Explaining {src_name}...", EventType.PROGRESS, stage="executor")
            res = explain_code(str(src_path), selected_model=model)
            state["result"] = res
            state["analysis_result"] = res
            state["execution_success"] = True
            ActivityStream.emit("Explanation generated", EventType.SUCCESS, stage="executor")
            return state

        elif task == "debug":
            src_path = _resolve_in_project(source_file, project_path)
            error_content = ""
            if src_path and src_path.exists():
                error_content = src_path.read_text(encoding="utf-8", errors="ignore")
            else:
                error_content = state["user_query"]

            ActivityStream.emit(f"Debugging {src_name}...", EventType.PROGRESS, stage="executor")
            res = debug_error(error_content, selected_model=model)
            state["result"] = res
            state["analysis_result"] = res
            state["execution_success"] = True
            ActivityStream.emit("Debug analysis complete", EventType.SUCCESS, stage="executor")
            return state

        elif task == "edit":
            src_path = _resolve_in_project(source_file, project_path)
            operation = state.get("operation", "modify")
            target_file = state.get("target_file")
            project_root = Path(project_path).expanduser().resolve()
            target_lang = state.get("target_language") or "python"

            if operation == "modify" and (not src_path or not src_path.exists()):
                state["result"] = f"Edit task failed: Valid source file is required for modify operation (resolved: {src_path})."
                state["execution_success"] = False
                ActivityStream.emit("Edit failed: Valid source file required", EventType.ERROR, stage="executor")
                return state

            resolved_target = None
            if operation == "create":
                if target_file:
                    target_path = Path(target_file)
                    resolved_target = target_path if target_path.is_absolute() else (project_root / target_path).resolve()
                elif src_path:
                    ext_map = {"python": ".py", "java": ".java", "cpp": ".cpp", "javascript": ".js", "typescript": ".ts"}
                    target_ext = ext_map.get(target_lang, src_path.suffix)
                    resolved_target = src_path.with_suffix(target_ext)

                if resolved_target:
                    try:
                        resolved_target.relative_to(project_root)
                    except ValueError:
                        state["result"] = "Edit failed: Security error - Target file must be inside project root."
                        state["execution_success"] = False
                        ActivityStream.emit("Edit failed: Security error", EventType.ERROR, stage="executor")
                        return state

                    if resolved_target.exists():
                        operation = "modify"
                        src_path = resolved_target
                        resolved_target = None

            lang_label = target_lang.capitalize() if target_lang else "Code"
            ActivityStream.emit(f"Generating {lang_label} implementation...", EventType.PROGRESS, stage="executor")

            from app.tools.framework_detector import detect_framework_and_stack
            stack_info = detect_framework_and_stack(project_path)

            edit_req = EditRequest(
                file_path=str(src_path) if src_path else str(project_root),
                instruction=state.get("task_instruction") or state["user_query"],
                model=model,
                source_language=state.get("source_language") or (detect_language(str(src_path)) if src_path else "python"),
                target_language=target_lang,
                target_file=str(resolved_target) if resolved_target else None,
                operation=operation,
                create_backup=(operation != "create"),
                analysis_result=state.get("analysis_result"),
                project_path=project_path,
                target_symbol=state.get("target_symbol"),
                start_line=state.get("start_line"),
                end_line=state.get("end_line"),
                scope_type=state.get("scope_type"),
                search_block=state.get("search_block"),
                replace_block=state.get("replace_block"),
                project_framework=stack_info.get("summary"),
            )

            service = EditingService()
            response = service.prepare_edit(edit_req)
            state["edit_response"] = response

            if not response.success:
                state["result"] = f"Edit preparation failed:\n{response.error}"
                state["execution_success"] = False
                ActivityStream.emit("Edit preparation failed", EventType.ERROR, stage="executor")
                return state

            # If user approval is required, hold disk write until interactive confirmation
            if state.get("require_approval", False):
                state["modified_file"] = response.destination_path
                state["result"] = response.diff
                state["approval_pending"] = True
                state["execution_success"] = True
                ActivityStream.emit("Edit preview prepared (pending user approval)", EventType.SUCCESS, stage="executor")
                return state

            if operation == "create":
                service.create_file(response, project_path=project_path)
                state["modified_file"] = response.output_file
                state["result"] = f"Successfully created file: {response.output_file}\n\n{response.diff}"
                ActivityStream.emit(f"Generated {Path(response.output_file).name}", EventType.SUCCESS, stage="executor")
            else:
                service.apply_edit(response, response.file_path, project_path=project_path)
                state["modified_file"] = response.file_path
                state["result"] = f"Successfully modified file: {response.file_path}\n\n{response.diff}"
                ActivityStream.emit(f"Modified {Path(response.file_path).name}", EventType.SUCCESS, stage="executor")

            ActivityStream.emit("Validating generated code...", EventType.PROGRESS, stage="executor")
            state["execution_success"] = True
            return state

        elif task == "deployment":
            ActivityStream.emit("Generating deployment files...", EventType.PROGRESS, stage="executor")
            query_lower = state["user_query"].lower()
            if "compose" in query_lower:
                state["result"] = save_docker_compose(project_path, selected_model=model)
            elif "requirements" in query_lower:
                pkgs = save_requirements(project_path)
                state["result"] = f"Generated requirements.txt with {len(pkgs)} packages."
            else:
                state["result"] = save_dockerfile(project_path, selected_model=model)

            state["execution_success"] = True
            ActivityStream.emit("Deployment files generated", EventType.SUCCESS, stage="executor")
            return state

        else:
            state["result"] = f"Unsupported task tool: {task}"
            state["execution_success"] = False
            return state

    except Exception as exc:
        state["result"] = f"Task execution failed: {type(exc).__name__}: {exc}"
        state["execution_success"] = False
        ActivityStream.emit(f"Task execution failed: {exc}", EventType.ERROR, stage="executor")
        return state


def reviewer_node(state: EdgeMindState) -> EdgeMindState:
    """
    Reviewer Stage V2 (Phase 7 & Section 14: True Result & Disk Inspection).
    Inspects actual filesystem state on disk and emits verification activity events.
    """
    ActivityStream.emit("Reviewing changes...", EventType.PROGRESS, stage="reviewer")

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
        review_details.append("✓ Analysis task completed without file modifications.")

    elif task == "edit":
        edit_resp = state.get("edit_response")
        if not edit_resp or not edit_resp.success:
            overall_success = False
            review_details.append("Edit preparation failed.")

        if state.get("approval_pending", False):
            if edit_resp and edit_resp.success:
                fname = mod_path.name if mod_path else (Path(source_file).name if source_file else "file")
                review_details.append(f"✓ Edit preview generated for {fname} (Pending User Approval)")
                if edit_resp.validation_message:
                    review_details.append(f"✓ Syntax validation passed: {edit_resp.validation_message}")
                ActivityStream.emit("Preview verified (awaiting approval)", EventType.SUCCESS, stage="reviewer")
            state["review_status"] = {
                "success": overall_success,
                "task": task,
                "operation": operation,
                "details": review_details,
            }
            return state

        if operation == "create":
            if src_path and src_path.exists():
                review_details.append(f"✓ Source file preserved: {src_path}")
                ActivityStream.emit("Source preserved", EventType.SUCCESS, stage="reviewer")
            else:
                overall_success = False
                review_details.append(f"✗ Source file missing or corrupted: {src_path}")

            if mod_path and mod_path.exists():
                actual_disk_content = mod_path.read_text(encoding="utf-8", errors="ignore")
                if actual_disk_content.strip():
                    review_details.append(f"✓ Target file created: {mod_path}")
                    ActivityStream.emit(f"Target file written: {mod_path.name}", EventType.SUCCESS, stage="reviewer")
                    valid, val_msg = validate_code(actual_disk_content, target_language)
                    if valid:
                        review_details.append(f"✓ Syntax validation passed: {val_msg}")
                        ActivityStream.emit(f"{target_language.capitalize()} syntax valid", EventType.SUCCESS, stage="reviewer")
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
            if mod_path and mod_path.exists():
                actual_disk_content = mod_path.read_text(encoding="utf-8", errors="ignore")
                valid, val_msg = validate_code(actual_disk_content, target_language)
                if valid:
                    review_details.append(f"✓ Modification syntax passed: {val_msg}")
                    ActivityStream.emit(f"{target_language.capitalize()} syntax valid", EventType.SUCCESS, stage="reviewer")
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
    """
    Evaluate overall execution, review status, and perform ReAct requirement reflection.
    If the requirement is partially satisfied or needs follow-up, triggers an iterative loop.
    """
    task = state.get("current_task")
    if task == "edit":
        review = state.get("review_status") or {}
        success = review.get("success", False)

        if success:
            react_res = verify_react_step(state)
            if not react_res.get("satisfied") and react_res.get("followup_needed"):
                iter_count = state.get("react_iteration", 0) + 1
                state["react_iteration"] = iter_count
                state["needs_react_followup"] = True
                ActivityStream.emit(
                    f"ReAct Reflection #{iter_count}: {react_res.get('reason')}",
                    EventType.PROGRESS,
                    stage="evaluator",
                )
                followup = react_res.get("followup_task")
                if followup:
                    cur_step = state.get("current_step", 0)
                    plan = list(state.get("plan", []))
                    plan.insert(cur_step + 1, followup)
                    state["plan"] = plan
            elif react_res.get("satisfied") and state.get("react_iteration", 0) > 0:
                ActivityStream.emit(
                    "ReAct Loop complete: all requirements and symbols satisfied",
                    EventType.SUCCESS,
                    stage="evaluator",
                )
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
    if state.get("needs_react_followup", False):
        state["needs_react_followup"] = False
        return "continue"

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
