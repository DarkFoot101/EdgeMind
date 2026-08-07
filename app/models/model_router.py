from app.resources.system_monitor import get_system_resources


def select_model(task: str) -> str:
    """
    Selects the most appropriate LLM based on the task.
    Future versions will also consider RAM, CPU,
    battery level and thermal constraints.
    """
    resources = get_system_resources()
    ram = resources["ram_available_gb"]

    if task == "planner":
        return "qwen2.5-coder:3b"
        
    if task == "analyze":
        return "qwen2.5-coder:3b"

    elif task == "deployment":
        return "qwen2.5-coder:3b"

    elif task == "debug":
        return "qwen2.5-coder:3b"

    elif task == "explain":
        return "qwen2.5-coder:3b"

    elif task == "edit":
        return "qwen2.5-coder:3b"

    return "phi3:mini"
