"""
EdgeMind Interactive CLI
Provides an interactive coding assistant
similar to Claude Code.
"""

import string 
import time
import shutil
import re 
from pathlib import Path

from app.cli.banner import print_banner
from app.cli.commands import (
    show_help,
    show_status,
    show_memory,
    clear_terminal,
)
from app.cli.session import SessionState
from app.graph.workflow import workflow


def resolve_file(
    filename: str,
    project_path: str,
    active_directory: str | None = None,
) -> str | None:
    """
    Search the project recursively for a file.
    """
    project = Path(project_path).resolve()
    
    # Clean filename of outer quotes/spaces
    filename = filename.strip("'\" ")
    
    IGNORED_DIRS = {
        ".git",
        ".edgemind",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        ".pytest_cache",
        "edgemind.egg-info",
        "build",
        "dist",
        "backups"
    }

    # 1. Direct path check
    direct_path = (project / filename).resolve()
    if direct_path.exists() and direct_path.is_file():
        if not any(ignored in direct_path.parts for ignored in IGNORED_DIRS):
            return str(direct_path)
            
    # 2. Recursive search
    matches = []
    search_pattern = Path(filename).name
    
    for path in project.rglob(search_pattern):
        path = path.resolve()
        if not path.is_file():
            continue
        if any(ignored in path.parts for ignored in IGNORED_DIRS):
            continue
            
        # Check relative path structure matching (e.g. tests/bad.java)
        if len(Path(filename).parts) > 1:
            try:
                rel = path.relative_to(project)
                if not str(rel).replace("\\", "/").endswith(filename.replace("\\", "/")):
                    continue
            except ValueError:
                continue
                
        matches.append(path)
        
    if not matches:
        return None
        
    # Sort matches deterministically
    matches = sorted(list(set(matches)))
    
    # Prefer active directory if provided
    if active_directory:
        active_dir_path = Path(active_directory).resolve()
        preferred_matches = []
        for m in matches:
            try:
                m.relative_to(active_dir_path)
                preferred_matches.append(m)
            except ValueError:
                pass
        if preferred_matches:
            return str(sorted(preferred_matches)[0])
            
    # If no preferred match in active directory, return the first deterministic match
    return str(matches[0])


def update_session_context(session: SessionState, query: str):
    """
    Update the active working context from the user's prompt.
    """
    session.project_path = str(Path.cwd())
    
    # Check if query references files
    files = re.findall(
        r"[\w./\\-]+\.[A-Za-z0-9]+",
        query,
    )

    resolved = None
    if files:
        for f in files:
            filename = f.strip(string.punctuation)
            res = resolve_file(
                filename,
                session.project_path,
                session.active_directory,
            )
            if res:
                resolved = res
                break
                
    if resolved:
        session.active_file = resolved
        session.active_directory = str(Path(resolved).parent)
        print(f"Resolved file: {resolved}")
    else:
        # Check if pronouns or continuation phrases are used
        pronouns = {"it", "that", "the file", "this code", "this file", "remaining bugs", "continue"}
        words = set(re.findall(r"\b\w+\b", query.lower()))
        has_pronoun = not words.isdisjoint(pronouns)
        
        if has_pronoun or not files:
            if session.active_file:
                print(f"Using active file: {session.active_file}")
            else:
                print("No active file.")
        else:
            print("No active file.")


def create_state(session: SessionState, query: str) -> dict:
    return {
        "user_query": query,
        "project_path": session.project_path,
        "file_path": session.active_file or "",
        "plan": [],
        "current_step": 0,
        "current_task": "",
        "task_instruction": "",
        "selected_model": "",
        "result": "",
        "execution_success": False,
        "memory_context": "",
        "edit_response": None,
        "modified_file": session.last_edited_file,
        "target_file": None,
        "operation": None,
        "retry_count": 0,
        "max_retry": 2,
    }


def run():
    from app.setup.checks import (
        check_ollama,
        check_ram,
        check_disk,
        missing_models,
        start_ollama,
    )
    from app.setup.installer import run_setup
    
    # 1. Detect whether Ollama exists in the system path
    if not shutil.which("ollama"):
        print("\nError: Ollama binary not found. Please install Ollama (https://ollama.com) and ensure it is in your PATH.")
        return

    # 2. Detect whether Ollama is running
    if not check_ollama():
        print("\nOllama is not running.")
        # 3. Offer to start it
        answer = input("Start it now? (Y/N): ").lower()
        if answer == "y":
            if not start_ollama():
                print("Unable to start Ollama automatically. Please run 'ollama serve' in a separate terminal.")
                return
            
            # Polling wait for Ollama to start
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
            print("Ollama must be running to execute models. Exiting.")
            return

    # 4 & 5. Detect and pull missing models
    missing = missing_models()
    if missing:
        print("\nMissing required Ollama models:")
        for model in missing:
            print(f"  - {model}")
            
        # 6. Display disk/RAM requirements
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

        try:
            result = workflow.invoke(state)
            
            print(result["result"])
            session.remember(
                query=query,
                result=result["result"],
                file_path=result.get("file_path") or state["file_path"],
                plan=result.get("plan"),
                model=result.get("selected_model"),
                last_edited_file=result.get("modified_file"),
            )
            print(
                f"\n✓ Completed using {session.selected_model}\n"
            )
        except Exception as e:
            print(f"\nExecution failed: {e}\n")
        print()