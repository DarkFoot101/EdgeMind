"""
EdgeMind CLI Commands
Handles built-in commands.
No LangGraph logic should exist here.
"""

from pathlib import Path

from app.memory.memory_manager import search_memory
from app.resources.system_monitor import get_system_resources
from app.setup.installer import run_setup


def show_help():

    print("\nAvailable Commands\n")

    print("help")
    print("status")
    print("memory")
    print("clear")
    print("setup")
    print("exit")

    print("\nExamples\n")

    print("Analyze this project")
    print("Explain app/models/model_router.py")
    print("Debug tests/sample_error.txt")
    print("Generate Dockerfile")
    print("Modify tests/sample_code.py")
    print()


def show_status(session):

    resources = get_system_resources()
    rows = search_memory(session.project_path)

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("EdgeMind Status")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    print(f"\nProject         : {session.project_name}")
    print(f"Current File    : {session.current_file}")
    print(f"Last Query      : {session.last_query}")
    print(f"Conversation    : {len(session.conversation_history)} turns")
    print(f"Selected Model  : {session.selected_model}")
    print(f"Memory Entries  : {len(rows)}")
    print(f"CPU Usage       : {resources['cpu_percent']} %")
    print(f"Available RAM   : {resources['ram_available_gb']:.2f} GB")
    print("\nSQLite          : Connected")

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")


def show_memory(session):

    rows = search_memory(session.project_path)
    print()

    if not rows:
        print("No memory available.\n")
        return

    print("Recent Memory\n")
    for query, task, result, success in rows[-10:]:
        print("--------------------------------")
        print(f"Query   : {query}")
        print(f"Task    : {task}")
        print(f"Success : {bool(success)}")
        print("--------------------------------")

    print()


def clear_terminal():
    print("\033c", end="")