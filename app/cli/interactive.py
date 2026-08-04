"""
EdgeMind Interactive CLI
Provides an interactive coding assistant
similar to Claude Code.
"""

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
            if Path(word).exists():
                session.current_file = word
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