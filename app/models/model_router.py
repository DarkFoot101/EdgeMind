from app.resources.system_monitor import get_system_resources


def select_model(task: str):

    resources = get_system_resources()

    ram = resources["ram_available_gb"]

    if task == "analyze":
        return "phi3:mini"

    if task == "debug":
        return "qwen2.5-coder:3b"

    if task == "deployment":
        return "phi3:mini"

    if task == "explain":
        return "qwen2.5-coder:3b"
    
    return "phi3:mini"