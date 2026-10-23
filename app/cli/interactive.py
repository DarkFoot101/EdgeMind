"""
EdgeMind V2.1 Interactive CLI Shell

Provides a polished, Claude-Code style interactive coding assistant interface.
Real-time Activity Streaming, Context-Aware Intent Routing, Conversational Companion mode,
Autonomous file discovery, structured Change Review summaries, and robust SQLite session memory.
"""

import re
import shutil
import time
import sys
from pathlib import Path

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

from app.cli.banner import print_banner
from app.cli.commands import (
    clear_terminal,
    install_extension_command,
    show_help,
    show_memory,
    show_status,
)
from app.cli.session import SessionState
from app.events.activity_stream import ActivityStream, EventType, ActivityEvent
from app.graph.workflow import workflow
from app.routing.conversation_handler import handle_conversational, handle_follow_up
from app.routing.intent_router import IntentType, detect_intent
from app.tools.file_discovery import resolve_best_file
from app.editing.diff_generator import colorize_diff
from app.editing.editing_service import EditingService


def format_change_review(state: dict, result_data: dict) -> str:
    """
    Generate Claude-Code style output report:
    - Files Overview (Created / Modified / Preserved)
    - Important changes summary points
    - Verification & Review checkmarks
    - Formatted unified diff output
    """
    output = []
    output.append("\n" + "━" * 60)
    output.append("EdgeMind V2.1 Execution Summary")
    output.append("━" * 60 + "\n")

    # Step Checkmarks
    plan = result_data.get("plan", [])
    if plan:
        output.append("Workflow Execution:")
        for idx, task in enumerate(plan, 1):
            tool = task.get("tool", "")
            op = task.get("operation", "")
            target = task.get("target_file") or task.get("source_file") or ""
            target_basename = Path(target).name if target else "project"
            output.append(f"  ✓ Step {idx}: [{op.upper()}] {tool} {target_basename}".strip())
        output.append("")

    # Files Overview
    source_file = result_data.get("source_file") or result_data.get("file_path") or ""
    modified_file = result_data.get("modified_file") or ""
    operation = result_data.get("operation") or "modify"

    src_name = Path(source_file).name if source_file else "None"
    mod_name = Path(modified_file).name if modified_file else "None"

    created = "None"
    modified = "None"
    preserved = "None"

    if operation == "create" and modified_file:
        created = f"{mod_name} (NEW FILE)"
        if source_file and Path(source_file).name != mod_name:
            preserved = f"{src_name} (UNTOUCHED)"
    elif operation == "modify" and modified_file:
        modified = f"{mod_name} (MODIFIED FILE)"
    elif source_file:
        preserved = f"{src_name}"

    output.append("Files Status:")
    output.append(f"  Created  : {created}")
    output.append(f"  Modified : {modified}")
    output.append(f"  Preserved: {preserved}")

    # Verification & Review Status
    review = result_data.get("review_status") or {}
    review_details = review.get("details", [])
    output.append("\nValidation & Review:")
    if review_details:
        for detail in review_details:
            output.append(f"  {detail}")
    else:
        success = result_data.get("execution_success", False)
    # Telemetry & Performance Metrics
    edit_resp = result_data.get("edit_response")
    metrics = getattr(edit_resp, "metrics", None) if edit_resp else None
    if metrics:
        output.append("\nExecution Telemetry:")
        output.append(f"  Duration : {metrics.inference_time_seconds:.2f}s")
        if metrics.total_tokens:
            output.append(f"  Tokens   : {metrics.total_tokens} (Prompt: {metrics.prompt_tokens}, Eval: {metrics.completion_tokens})")
        if metrics.lines_added or metrics.lines_deleted:
            output.append(f"  Delta    : +{metrics.lines_added} / -{metrics.lines_deleted} lines")
        if metrics.peak_memory_mb:
            output.append(f"  Memory   : {metrics.peak_memory_mb:.1f} MB (RSS)")

    # Result / Diff Content Output
    res_str = result_data.get("result", "")
    output.append("\nProposed Changes (Colorized Diff Preview):")
    output.append("-" * 60)
    output.append(colorize_diff(res_str) if res_str else "(No text output)")
    output.append("-" * 60 + "\n")

    return "\n".join(output)


def update_session_context(session: SessionState, query: str):
    """
    Update active session working context from user prompt.
    Supports natural language pronouns ("it", "that", "this file", "what changed?").
    """
    session.project_path = str(Path.cwd())

    best_file = resolve_best_file(query, session.project_path, active_file=session.active_file)
    if best_file:
        session.active_file = best_file
        session.active_directory = str(Path(best_file).parent)


def create_state(session: SessionState, query: str) -> dict:
    return {
        "user_query": query,
        "project_path": session.project_path,
        "file_path": session.active_file or "",
        "source_file": session.active_file or None,
        "target_file": None,
        "modified_file": None,
        "source_language": None,
        "target_language": None,
        "intent": "execution",
        "plan": [],
        "current_step": 0,
        "current_task": "",
        "task_instruction": "",
        "operation": None,
        "selected_model": "",
        "retry_count": 0,
        "max_retry": 2,
        "result": "",
        "execution_success": False,
        "memory_context": "",
        "edit_response": None,
        "discovered_files": [],
        "review_status": None,
        "change_summary": None,
        "target_symbol": None,
        "start_line": None,
        "end_line": None,
        "scope_type": None,
        "search_block": None,
        "replace_block": None,
        "require_approval": getattr(session, "require_approval", True),
        "approval_pending": False,
    }


def open_gui_diff(original_path: str, proposed_code: str) -> bool:
    """Attempt to open an editor GUI side-by-side diff in VS Code, Cursor, or Antigravity IDE."""
    import tempfile
    import subprocess
    import shutil

    suffix = Path(original_path).suffix or ".txt"
    try:
        temp_f = tempfile.NamedTemporaryFile("w", delete=False, suffix=f"_edgemind_proposed{suffix}", encoding="utf-8")
        temp_f.write(proposed_code)
        temp_f.close()
    except Exception:
        return False

    cli_candidates = [
        shutil.which("antigravity"),
        shutil.which("code"),
        shutil.which("cursor"),
        "/Applications/Antigravity IDE.app/Contents/Resources/app/bin/code",
        "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
        "/Applications/Cursor.app/Contents/Resources/app/bin/cursor",
    ]
    for cand in cli_candidates:
        if cand and Path(cand).exists():
            try:
                subprocess.Popen([str(cand), "--diff", str(original_path), temp_f.name])
                return True
            except Exception:
                continue
    return False


def prompt_user_approval(result_data: dict, project_path: str = ".") -> bool:
    """
    Prompt user to accept or reject the proposed code modification.
    Returns True if changes were applied, False if rejected.
    """
    edit_resp = result_data.get("edit_response")
    if not edit_resp:
        return True

    dest_file = edit_resp.destination_path or edit_resp.file_path
    print("━" * 60)
    print(f"Interactive Review: {Path(dest_file).name}")
    print("━" * 60)
    print("  [a]ccept : Write and apply changes to disk")
    print("  [r]eject : Discard changes (leave original file untouched)")
    print("  [v]iew   : Display full proposed code in terminal")
    print("  [d]iff   : Open side-by-side visual diff in editor GUI")
    print("━" * 60)
    print("💡 Tip: For native GUI with inline red/green preview and floating [✓ Accept] / [↶ Reject]")
    print("   buttons directly in your editor tab, press Cmd+I (or Ctrl+I) on any code file.\n")

    while True:
        try:
            choice = input("Accept changes? [A/r/v/d]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nOperation cancelled.")
            return False

        if choice in {"a", "accept", "y", "yes", ""}:
            service = EditingService()
            if result_data.get("operation") == "create":
                service.create_file(edit_resp, project_path=project_path)
            else:
                service.apply_edit(edit_resp, edit_resp.destination_path, project_path=project_path)
            print(f"\n✓ Changes applied to: {dest_file}\n")
            return True
        elif choice in {"r", "reject", "n", "no"}:
            print(f"\n✗ Changes rejected. File '{dest_file}' was left untouched.\n")
            return False
        elif choice in {"v", "view"}:
            print(f"\n--- Proposed Full Code for {dest_file} ---")
            lines = (edit_resp.modified_code or "").splitlines()
            for idx, line in enumerate(lines, 1):
                print(f"{idx:4d} | {line}")
            print("-" * 50 + "\n")
        elif choice in {"d", "diff"}:
            opened = open_gui_diff(dest_file, edit_resp.modified_code or "")
            if opened:
                print(f"\n✓ Opened GUI side-by-side visual diff in editor for '{Path(dest_file).name}'.")
            else:
                print("\nDisplaying colorized diff preview:")
                print(colorize_diff(edit_resp.diff or ""))
            print("Return here and enter 'a' to accept or 'r' to reject.\n")
        else:
            print("Invalid input. Please enter 'a' to accept, 'r' to reject, 'v' to view, or 'd' for GUI diff.")


def run():
    # Handle version query immediately
    if len(sys.argv) > 1 and sys.argv[1].lower() in {"--version", "-v", "version"}:
        from app import __version__
        print(f"EdgeMind v{__version__}")
        return

    # Handle dedicated CLI subcommands / flags
    if len(sys.argv) > 1 and sys.argv[1].lower() in {
        "install-extension",
        "--install-extension",
        "vscode",
        "--vscode",
        "setup-vscode",
        "/vscode",
    }:
        install_extension_command()
        return

    from app.models.model_manager import ModelManager
    from app.setup.checks import (
        check_disk,
        check_ollama,
        check_ram,
        missing_models,
        start_ollama,
    )
    from app.setup.installer import run_setup

    # 1. Ollama installation check
    if not ModelManager.is_ollama_installed():
        print("\nError: Ollama binary not found. Please install Ollama (https://ollama.com) and ensure it is in your PATH.")
        return

    # 2. Ollama running state check
    if not check_ollama():
        print("\nOllama is not running.")
        answer = input("Start it now? (Y/N): ").strip().lower()
        if answer in {"y", "yes"}:
            if not start_ollama():
                print("Unable to start Ollama automatically. Please run 'ollama serve' in a separate terminal.")
                return

            print("Starting Ollama", end="", flush=True)
            for _ in range(10):
                time.sleep(1)
                print(".", end="", flush=True)
                if check_ollama():
                    print(" Running!")
                    break
            else:
                print("\nOllama is taking too long to start. Please check 'ollama serve' output.")
                return
        else:
            print("Ollama must be running to execute EdgeMind. Exiting.")
            return

    # 3. Model availability check
    missing = missing_models()
    if missing:
        rec_model, size_est = ModelManager.recommend_default_model()
        print("\nEdgeMind Setup")
        print("✓ Python detected")
        print("✓ Ollama detected")
        print("✓ Ollama running")
        print("No compatible coding model found.")
        print(f"Recommended model:\n  {rec_model}")
        print(f"Model size: {size_est}")

        answer = input("\nDownload model? [Y/n]: ").strip().lower()
        if answer in {"", "y", "yes"}:
            import ollama
            print(f"Downloading {rec_model}...")
            try:
                ollama.pull(rec_model)
                print(f"✓ Successfully pulled {rec_model}")
            except Exception as e:
                print(f"✗ Failed to pull {rec_model}: {e}")
                return
        else:
            print("Required model missing. Exiting.")
            return

    # Check and auto-deploy bundled VS Code extension if available
    try:
        from app.extension.installer import ensure_extension_installed
        ext_res = ensure_extension_installed()
        if ext_res.get("success") and not ext_res.get("already_installed"):
            print("✓ EdgeMind VS Code & Cursor extension installed automatically.\n")
    except Exception:
        pass

    print_banner()
    session = SessionState()

    def print_event(event: ActivityEvent):
        print(f"  {event.formatted()}")

    ActivityStream.subscribe(print_event)

    while True:
        try:
            query = input("EdgeMind > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.\n")
            break

        if not query:
            continue

        command = query.lower()
        if command == "exit":
            print("\nGoodbye.\n")
            break

        if command == "help":
            show_help()
            continue

        if command in {"version", "/version", "--version", "-v"}:
            from app import __version__
            print(f"\nEdgeMind v{__version__}\n")
            continue

        if command in {"/vscode", "vscode", "/extension", "extension"}:
            install_extension_command()
            continue

        if command == "status":
            show_status(session)
            continue

        if command == "memory":
            show_memory(session)
            continue

        if command == "clear":
            session.clear()
            clear_terminal()
            print_banner()
            continue

        if command == "setup":
            run_setup()
            continue

        if command in {"what changed", "what changed?", "show diff"}:
            if session.last_result:
                print("\nLast Execution Output / Diff:\n")
                print(colorize_diff(session.last_result))
            else:
                print("\nNo recent changes in session.\n")
            continue

        if command in {"/review on", "review on", "/approval on", "approval on"}:
            session.require_approval = True
            print("\n✓ Interactive Review Mode ENABLED. All code modifications will display a red/green diff for manual approval.\n")
            continue

        if command in {"/review off", "review off", "/approval off", "approval off"}:
            session.require_approval = False
            print("\n⚠ Interactive Review Mode DISABLED. Code modifications will be applied automatically.\n")
            continue

        if command.startswith("/model") or command == "model" or command.startswith("model "):
            from app.cli.commands import show_model_menu
            if command.startswith("/model"):
                arg = command[len("/model"):].strip()
            else:
                arg = command[len("model"):].strip()
            show_model_menu(session, arg)
            continue


        update_session_context(session, query)

        # Detect intent (EXECUTION vs FOLLOW_UP vs CONVERSATIONAL)
        intent, confidence = detect_intent(query, has_previous_turn=bool(session.last_query))

        print()

        try:
            if intent == IntentType.FOLLOW_UP:
                result_data = handle_follow_up(query, session)
                print(f"\n{result_data['result']}\n")
                session.remember(
                    query=query,
                    result=result_data["result"],
                    file_path=session.active_file,
                    model=result_data.get("selected_model"),
                )

            elif intent == IntentType.CONVERSATIONAL:
                result_data = handle_conversational(query, session)
                print(f"\n{result_data['result']}\n")
                session.remember(
                    query=query,
                    result=result_data["result"],
                    file_path=session.active_file,
                    model=result_data.get("selected_model"),
                )

            else:
                # EXECUTION INTENT -> LangGraph workflow execution
                state = create_state(session, query)
                result_data = workflow.invoke(state)

                formatted_report = format_change_review(state, result_data)
                print(formatted_report)

                # Interactive confirmation gate if approval is pending
                if result_data.get("approval_pending"):
                    accepted = prompt_user_approval(result_data, project_path=session.project_path)
                    if not accepted:
                        result_data["execution_success"] = False
                        result_data["result"] = "Changes were rejected by user."

                active_file = (
                    result_data.get("modified_file")
                    or result_data.get("source_file")
                    or result_data.get("file_path")
                    or session.active_file
                )

                edit_resp = result_data.get("edit_response")
                metrics_dict = None
                if edit_resp and getattr(edit_resp, "metrics", None):
                    metrics_dict = (
                        edit_resp.metrics.to_dict()
                        if hasattr(edit_resp.metrics, "to_dict")
                        else edit_resp.metrics
                    )
                elif isinstance(result_data.get("metrics"), dict):
                    metrics_dict = result_data.get("metrics")

                scope_val = (
                    (
                        edit_resp.scope.scope_type.value
                        if hasattr(edit_resp.scope.scope_type, "value")
                        else str(edit_resp.scope.scope_type)
                    )
                    if edit_resp and getattr(edit_resp, "scope", None)
                    else result_data.get("scope_type")
                )

                src_h = (
                    getattr(edit_resp, "source_hash", None)
                    if edit_resp
                    else result_data.get("source_hash")
                )
                mod_h = (
                    getattr(edit_resp, "modified_hash", None)
                    if edit_resp
                    else result_data.get("modified_hash")
                )

                session.remember(
                    query=query,
                    result=result_data.get("result", ""),
                    file_path=active_file,
                    plan=result_data.get("plan"),
                    model=result_data.get("selected_model"),
                    last_edited_file=result_data.get("modified_file"),
                    last_created_file=result_data.get("modified_file") if result_data.get("operation") == "create" else None,
                    metrics=metrics_dict,
                    scope=scope_val,
                    source_hash=src_h,
                    modified_hash=mod_h,
                )
                print(f"✓ Completed task using {session.selected_model or 'Ollama'}\n")

        except Exception as e:
            print(f"\nExecution failed: {e}\n")


if __name__ == "__main__":
    run()