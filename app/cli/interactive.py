"""
EdgeMind Interactive CLI
Provides an interactive coding assistant
similar to Claude Code.
"""

import string 
from app.graph import state
from app.cli import session
from app.setup.installer import run_setup
from app.cli.banner import print_banner
from app.cli.commands import (
    show_help,
    show_status,
    show_memory,
    clear_terminal,
)
from app.cli.session import SessionState
from app.graph.workflow import workflow
from pathlib import Path
import re 


def update_session_context(session, query):
    """
    Update the active working context from the user's prompt.
    """
    session.project_path = str(Path.cwd())
    files = re.findall(
        r"[\w./\\-]+\.[A-Za-z0-9]+",
        query,
    )

    # User mentioned a file
    if files:
        filename = files[0].strip(string.punctuation)
        resolved = resolve_file(
            filename,
            session.project_path,
        )

        if resolved:
            session.active_file = resolved
            session.active_directory = str(Path(resolved).parent)
            print(f"Resolved file: {resolved}")
            return

    # No filename → keep previous active file
    if session.active_file:
        print(
            f"Using active file: {session.active_file}"
        )
    else:
        print("No active file.")


def create_state(session, query):

    return {

        "user_query": query,
        "project_path": session.project_path,
        "file_path": session.active_file or "",
        "plan": [],
        "current_step": 0,
        "current_task": "",
        "selected_model": "",
        "result": "",
        "execution_success": False,
        "memory_context": "",
        "edit_response": None,
    }


def run():

    session = SessionState()
    from app.setup.checks import (
        check_ollama,
        missing_models,
    )
    if not check_ollama():
        print("\nOllama is not running.")
        answer = input(
            "Start it now? (Y/N): "
        ).lower()
        if answer == "y":
            from app.setup.checks import start_ollama
            if not start_ollama():
                print(
                    "Unable to start Ollama."
                )
                return

    missing = missing_models()
    if missing:
        print("\nMissing Models\n")
        for model in missing:
            print(model)
        print(
            "\nRun 'setup' to install missing models."
        )
        return

    print_banner()

    while True:
        query = input("EdgeMind > ").strip()
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
            clear_terminal()
            print_banner()
            continue
        
        if command == "setup":

            run_setup()

            continue
        
        update_session_context(
            session,
            query,
        )

        print("\nThinking...\n")

        state = create_state(
            session,
            query,
        )

        print("\n========== STATE ==========")
        print(f"Project Path : {state['project_path']}")
        print(f"File Path    : {state['file_path']}")
        print("===========================\n")      

        result = workflow.invoke(state)

        print(result["result"])
        session.selected_model = result["selected_model"]
        session.last_plan = result["plan"]
        session.last_result = result["result"]
        session.last_query = query
        session.remember(
            query,
            result["result"],
            state["file_path"]
        )
        print(
            f"\n✓ Completed using {session.selected_model}\n"
        )
        print()

def resolve_file(
    filename: str,
    project_path: str,
):
    """
    Search the project recursively for a file.
    """

    project = Path(project_path)
    IGNORED_DIRS = {
        ".git",
        ".edgemind",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
    }

    matches = []

    for path in project.rglob(filename):
        if any(
            ignored in path.parts
            for ignored in IGNORED_DIRS
        ):
            continue
        matches.append(path)
    
    print(f"\nSearching for: {filename}")
    print(f"Found {len(matches)} match(es).")

    for match in matches:
        print(match)  

    if len(matches) == 1:
        return str(matches[0])

    if len(matches) > 1:
        print("\nMultiple files found:\n")
        for i, file in enumerate(matches, 1):
            print(f"{i}. {file}")
        try:
            choice = int(
                input("\nSelect file: ")
            )
            return str(matches[choice - 1])
        except Exception:
            return None

    return None