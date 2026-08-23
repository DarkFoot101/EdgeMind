"""
EdgeMind CLI Banner
Displays the startup screen for EdgeMind.
"""

from pathlib import Path
from app.resources.system_monitor import get_system_resources

def print_banner() -> None:
    """
    Display the EdgeMind startup banner.
    """

    resources = get_system_resources()

    print("\n")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("                    EdgeMind v1.0.4")
    print("      Resource-Aware Agentic Coding Assistant")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    print(f"\nProject          : {Path.cwd().name}")
    print("Memory           : Enabled")
    print("Current File     : None")
    print("Session          : Active")
    print("Planner          : Ready")
    print("LangGraph        : Ready")

    print(f"CPU Usage        : {resources['cpu_percent']} %")
    print(f"Available RAM    : {resources['ram_available_gb']:.2f} GB")

    print("\nType 'help' to view commands.")
    print("Type 'exit' to quit.")

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")