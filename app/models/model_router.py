"""
EdgeMind Resource-Aware Model Router V2

Selects local Ollama LLMs dynamically based on task requirements,
available RAM, and CPU resources.
"""

from app.resources.system_monitor import get_system_resources


def select_model(task: str) -> str:
    """
    Selects the most appropriate LLM based on task complexity and resource availability.
    - phi3:mini for lightweight tasks (planning, search, explanation, lightweight analysis)
    - qwen2.5-coder:3b for heavy code generation, editing, debugging, and deployment
    """
    resources = get_system_resources()
    available_ram = resources.get("ram_available_gb", 8.0)

    task_normalized = (task or "").lower()

    # Heavy code generation & editing tasks require specialized coder model
    if task_normalized in {"edit", "modify", "create", "debug", "deployment"}:
        return "qwen2.5-coder:3b"

    # For lighter tasks (planning, search, explain, analyze), if RAM is low (< 4GB), prefer phi3:mini
    if available_ram < 4.0:
        return "phi3:mini"

    # Default model assignment by task category
    if task_normalized in {"planner", "search", "explain"}:
        return "phi3:mini"
    elif task_normalized in {"analyze"}:
        return "phi3:mini"

    return "qwen2.5-coder:3b"
