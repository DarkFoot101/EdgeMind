"""
EdgeMind Interactive CLI
Provides an interactive coding assistant
similar to Claude Code.
"""

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


def update_session_context(
    session,
    query: str,
):
    """
    Extract useful context from the user's prompt.

    This allows follow-up prompts such as
    'modify it' or 'explain it again'
    without requiring the user to repeat
    the file path.
    """
    

    words = query.split()
    for word in words:
        if "." in words:
            session.project_path = "."
        if (
            word.endswith(".py")
            or word.endswith(".txt")
            or word.endswith(".json")
            or word.endswith(".yaml")
            or word.endswith(".yml")
            or word.endswith(".md")
        ):
            resolved = resolve_file(
                word,
                session.project_path,
            )   
            if resolved:
                session.current_file = resolved
                break


def create_state(session, query):

    return {

        "user_query": query,
        "project_path": session.project_path,
        "file_path": session.current_file or "",
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

        result = workflow.invoke(state)

        print(result["result"])
        session.selected_model = result["selected_model"]
        session.last_plan = result["plan"]
        session.last_result = result["result"]
        session.last_query = query
        session.remember(
            query,
            result["result"],
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
    Search the project recursively for a filename.
    """

    matches = list(
        Path(project_path).rglob(filename)
    )
    if len(matches) == 1:
        return str(matches[0])

    if len(matches) > 1:
        print(
            "\nMultiple files found:\n"
        )
        for index, file in enumerate(matches, 1):
            print(f"{index}. {file}")
        choice = input(
            "\nSelect file number: "
        )
        try:
            return str(matches[int(choice)-1])
        except Exception:
            return None
    return None