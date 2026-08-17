"""
EdgeMind V2.1 Interactive CLI Shell

Provides a polished, Claude-Code style interactive coding assistant interface.
Real-time Activity Streaming, Context-Aware Intent Routing, Conversational Companion mode,
Autonomous file discovery, structured Change Review summaries, and robust SQLite session memory.
"""

import re
import shutil
import time
from pathlib import Path

from app.cli.banner import print_banner
from app.cli.commands import (
    clear_terminal,
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
        output.append(f"  {'✓ Task executed successfully' if success else '✗ Execution failed'}")

    # Result / Diff Content Output
    res_str = result_data.get("result", "")
    output.append("\nResult Output:")
    output.append("-" * 60)
    output.append(res_str if res_str else "(No text output)")
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
    }


def run():
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
                print(session.last_result)
            else:
                print("\nNo recent changes in session.\n")
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

                active_file = (
                    result_data.get("modified_file")
                    or result_data.get("source_file")
                    or result_data.get("file_path")
                    or session.active_file
                )

                session.remember(
                    query=query,
                    result=result_data.get("result", ""),
                    file_path=active_file,
                    plan=result_data.get("plan"),
                    model=result_data.get("selected_model"),
                    last_edited_file=result_data.get("modified_file"),
                    last_created_file=result_data.get("modified_file") if result_data.get("operation") == "create" else None,
                )
                print(f"✓ Completed task using {session.selected_model or 'Ollama'}\n")

        except Exception as e:
            print(f"\nExecution failed: {e}\n")


if __name__ == "__main__":
    run()