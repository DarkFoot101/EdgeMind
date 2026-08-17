"""
EdgeMind Resource-Aware Model Router V2.1

Selects local Ollama LLMs dynamically based on task requirements,
installed local models, available RAM, and system resources.
"""

from app.models.model_manager import ModelManager


def select_model(task: str) -> str:
    """
    Selects the most appropriate installed local LLM based on task complexity and system capabilities.
    Prefers installed coding models (e.g. qwen2.5-coder) for code generation/editing/debugging.
    Prefers installed general models (e.g. phi3:mini) for planning, explanation, and conversation.
    Falls back deterministically when Ollama is offline or no models are detected (unit tests).
    """
    installed = ModelManager.list_installed_models()
    task_norm = (task or "").lower()

    if not installed:
        if task_norm in {"edit", "modify", "create", "debug", "deployment"}:
            return "qwen2.5-coder:3b"
        return "phi3:mini"

    return ModelManager.select_best_model(task)
