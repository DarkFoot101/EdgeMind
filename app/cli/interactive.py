"""
EdgeMind V2 Interactive CLI Shell

Provides a polished, Claude-Code style interactive coding assistant interface.
Autonomous file discovery, structured step indicators, Change Review summaries,
and robust session context management.
"""

import re
import shutil
import string
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
from app.graph.workflow import workflow
from app.tools.file_discovery import resolve_best_file


def format_change_review(state: dict, result_data: dict) -> str:
    """
    Generate Claude-Code style output report:
    - Step execution checkmarks (✓ Source found, ✓ Plan created, etc.)
    - Summary of Created / Modified / Preserved files
    - Validation & Verification status
    - Formatted unified diff
    """
    output = []
    output.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    output.append("EdgeMind V2 Execution Summary")
    output.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    # Step Checkmarks
    plan = result_data.get("plan", [])
    output.append("Workflow Steps:")
    if plan:
        output.append(f"  ✓ Plan created ({len(plan)} tasks)")
        for idx, task in enumerate(plan, 1):
            tool = task.get("tool", "")
            op = task.get("operation", "")
            target = task.get("target_file") or task.get("source_file") or ""
            output.append(f"  ✓ Step {idx}: [{op.upper()}] {tool} {target}".strip())
    else:
        output.append("  ✓ Direct execution completed")

    # Files Overview
    source_file = result_data.get("source_file") or result_data.get("file_path") or ""
    modified_file = result_data.get("modified_file") or ""
    operation = result_data.get("operation") or "modify"

    created = "None"
    modified = "None"
    preserved = "None"

    if operation == "create" and modified_file:
        created = f"{modified_file} (NEW FILE)"
        if source_file and source_file != modified_file:
            preserved = f"{source_file} (UNTOUCHED)"
    elif operation == "modify" and modified_file:
        modified = f"{modified_file} (MODIFIED FILE)"
    elif source_file:
        preserved = f"{source_file}"

    output.append("\nFiles Status:")
    output.append(f"  Created  : {created}")
    output.append(f"  Modified : {modified}")
    output.append(f"  Preserved: {preserved}")

    # Validation & Verification
    review = result_data.get("review_status") or {}
    review_details = review.get("details", [])
    output.append("\nVerification & Review:")
    if review_details:
        for detail in review_details:
            output.append(f"  {detail}")
    else:
        success = result_data.get("execution_success", False)
        output.append(f"  {'✓ Task executed successfully' if success else '✗ Execution failed'}")

    # Result / Diff Content
    res_str = result_data.get("result", "")
    output.append("\nResult Output:")
    output.append("-------------------------------------------------------------")
    output.append(res_str if res_str else "(No text output)")
    output.append("-------------------------------------------------------------\n")

    return "\n".join(output)


def update_session_context(session: SessionState, query: str):
    """
    Update active session working context from user prompt.
    Support natural language pronouns ("it", "that", "this file", "what changed?").
    """
    session.project_path = str(Path.cwd())

    # Direct filename search in query
    best_file = resolve_best_file(query, session.project_path, active_file=session.active_file)

    if best_file:
        session.active_file = best_file
        session.active_directory = str(Path(best_file).parent)
    elif session.active_file:
        # Check pronoun references
        words = set(re.findall(r"\b\w+\b", query.lower()))
        pronouns = {"it", "that", "file", "code", "optimize", "fix", "convert", "again", "changed", "what"}
        if not words.isdisjoint(pronouns):
            pass  # keep session.active_file intact


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
    from app.setup.checks import (
        check_disk,
        check_ollama,
        check_ram,
        missing_models,
        start_ollama,
    )
    from app.setup.installer import run_setup

    # 1. Ollama installation check
    if not shutil.which("ollama"):
        print("\nError: Ollama binary not found. Please install Ollama (https://ollama.com) and ensure it is in your PATH.")
        return

    # 2. Ollama running state check
    if not check_ollama():
        print("\nOllama is not running.")
        answer = input("Start it now? (Y/N): ").lower()
        if answer == "y":
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
            print("Ollama must be running to execute EdgeMind V2. Exiting.")
            return

    # 3. Missing models check
    missing = missing_models()
    if missing:
        print("\nMissing required Ollama models:")
        for model in missing:
            print(f"  - {model}")

        print("\nSystem Requirements Check:")
        print(f"  - Available RAM: {'✓ OK' if check_ram() else '✗ Low RAM (requires >= 4GB)'}")
        print(f"  - Free Disk Space: {'✓ OK' if check_disk() else '✗ Low Disk Space (requires >= 5GB)'}")

        answer = input("\nDownload them now? (Y/N): ").lower()
        if answer == "y":
            import ollama

            for model in missing:
                print(f"Downloading {model}...")
                try:
                    ollama.pull(model)
                    print(f"✓ Successfully pulled {model}")
                except Exception as e:
                    print(f"✗ Failed to pull {model}: {e}")
                    return
        else:
            print("Required models are missing. Exiting.")
            return

    print_banner()
    session = SessionState()

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

        print("\nThinking...\n")
        state = create_state(session, query)

        try:
            result_data = workflow.invoke(state)

            formatted_report = format_change_review(state, result_data)
            print(formatted_report)

            # Update session context
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
            )
            print(f"\n✓ Completed task using {session.selected_model or 'Ollama'}\n")

        except Exception as e:
            print(f"\nExecution failed: {e}\n")


if __name__ == "__main__":
    run()