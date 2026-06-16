from app.resources.system_monitor import get_system_resources


def select_model(task_type: str):

    resources = get_system_resources()

    ram = resources["ram_available_gb"]

    if task_type == "simple":
        return "qwen2.5-coder:3b"

    if ram < 4:
        return "qwen2.5-coder:3b"

    return "qwen2.5-coder:3b"