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
    print("model [name]            : View and switch active Ollama model")
    print("vscode / extension      : Install or update VS Code & Cursor extension")
    print("memory")
    print("clear")
    print("review on / review off  : Toggle manual red/green approval gate")
    print("setup")
    print("exit")

    print("\nExamples\n")

    print("/model qwen2.5-coder:3b")
    print("Analyze this project")
    print("Explain app/models/model_router.py")
    print("Debug tests/sample_error.txt")
    print("Generate Dockerfile")
    print("Modify tests/sample_code.py")
    print()


def show_model_menu(session, arg: str = ""):
    """View installed Ollama models and switch active model."""
    from app.models.config import clear_configured_model, get_configured_model, get_model_catalog, set_configured_model

    catalog = get_model_catalog()
    if not catalog:
        print("\nNo local Ollama models detected. Please run 'ollama pull qwen2.5-coder:3b'.\n")
        return

    arg_clean = arg.strip()
    if arg_clean:
        if arg_clean.lower() in {"auto", "default", "clear"}:
            clear_configured_model()
            session.selected_model = "Auto-Routing"
            print("\n✓ Active model reset to: Auto-Routing (Resource-aware dynamic selection)\n")
            return

        # Check if argument is a number
        if arg_clean.isdigit():
            idx = int(arg_clean) - 1
            if 0 <= idx < len(catalog):
                chosen = catalog[idx]["model"]
                set_configured_model(chosen)
                session.selected_model = chosen
                print(f"\n✓ Active model set to: {chosen}\n")
                return

        # Direct model name
        chosen = set_configured_model(arg_clean)
        session.selected_model = chosen
        print(f"\n✓ Active model set to: {chosen}\n")
        return

    # Interactive menu
    print("\n" + "━" * 50)
    print("EdgeMind AI Model Selector")
    print("━" * 50)
    print("Installed Local Ollama Models:\n")
    for idx, item in enumerate(catalog, 1):
        status_tag = " (Active)" if item["is_active"] else ""
        print(f"  [{idx}] {item['model']}{status_tag} [{item['parameter_size']}, ~{item['size_gb']}]")
    print("  [0] Auto-Routing (Dynamic selection based on task & RAM)")
    print("━" * 50)

    try:
        choice = input(f"\nSelect model [0-{len(catalog)}] or enter model tag: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nModel selection cancelled.\n")
        return

    if not choice:
        return

    if choice == "0" or choice.lower() in {"auto", "default"}:
        clear_configured_model()
        session.selected_model = "Auto-Routing"
        print("\n✓ Active model reset to: Auto-Routing\n")
        return

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(catalog):
            chosen = catalog[idx]["model"]
            set_configured_model(chosen)
            session.selected_model = chosen
            print(f"\n✓ Active model set to: {chosen}\n")
            return

    chosen = set_configured_model(choice)
    session.selected_model = chosen
    print(f"\n✓ Active model set to: {chosen}\n")


def show_status(session):

    resources = get_system_resources()
    rows = search_memory(session.project_path)

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("EdgeMind Status")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    print(f"\nProject         : {session.project_name}")
    print(f"Current File    : {session.active_file}")
    print(f"Last Query      : {session.last_query}")
    print(f"Conversation    : {len(session.conversation_history)} turns")
    print(f"Selected Model  : {session.selected_model}")
    print(f"Review Mode     : {'Enabled [Manual Accept/Reject]' if getattr(session, 'require_approval', True) else 'Disabled [Auto-Apply]'}")
    print(f"Memory Entries  : {len(rows)}")
    print(f"CPU Usage       : {resources['cpu_percent']} %")
    print(f"Available RAM   : {resources['ram_available_gb']:.2f} GB")
    if getattr(session, "last_metrics", None):
        inf_time = session.last_metrics.get("inference_time_seconds", 0.0)
        toks = session.last_metrics.get("total_tokens", 0)
        peak_mb = session.last_metrics.get("peak_memory_mb", 0.0)
        print(f"Last Latency    : {inf_time:.2f}s ({toks} tokens)")
        print(f"Peak RSS Memory : {peak_mb:.1f} MB")
    if getattr(session, "last_scope", None):
        print(f"Last Edit Scope : {session.last_scope}")
    if getattr(session, "last_source_hash", None):
        print(f"Source SHA-256  : {session.last_source_hash[:12]}...")
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


def install_extension_command():
    """Install or update the EdgeMind extension into local VS Code & Cursor IDE environments."""
    from app.extension.installer import install_extension

    print("\n" + "━" * 50)
    print("EdgeMind VS Code & Cursor Extension Installer")
    print("━" * 50)
    print("Installing extension into local IDE environments...")
    res = install_extension(force=True)
    if res.get("success"):
        for loc in res.get("locations", []):
            print(f"  ✓ Installed to: {loc}")
        if res.get("vsix_path"):
            print(f"  ✓ Standalone VSIX: {res['vsix_path']}")
        print("\nSetup complete! To activate:")
        print("  1. Open/Reload VS Code or Cursor.")
        print("  2. In any code file, press Cmd+I (macOS) or Ctrl+I (Windows/Linux) to edit inline.")
        print("  3. View the active model in the bottom status bar: $(sparkle) EdgeMind\n")
    else:
        print(f"\n✗ Extension installation failed: {res.get('error', 'Unknown error')}\n")