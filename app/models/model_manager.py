"""
EdgeMind V2.1 Intelligent Model Manager

Discovers installed local Ollama models, categorizes model capabilities,
evaluates system resources, and selects the optimal local model without
forcing unnecessary multi-GB downloads.
"""

import shutil
from typing import Dict, List, Optional, Tuple
import ollama

from app.resources.system_monitor import get_system_resources

PREFERRED_CODING_PATTERNS = [
    "coder", "code", "starcoder", "deepseek-coder", "codellama", "qwen2.5-coder"
]

PREFERRED_GENERAL_PATTERNS = [
    "phi3", "phi", "llama3", "llama", "mistral", "gemma", "qwen"
]


class ModelManager:
    @staticmethod
    def is_ollama_installed() -> bool:
        """Check if ollama CLI binary exists in PATH."""
        return shutil.which("ollama") is not None

    @staticmethod
    def is_ollama_running() -> bool:
        """Check if local Ollama daemon is active and responding."""
        try:
            ollama.list()
            return True
        except Exception:
            return False

    @staticmethod
    def list_installed_models() -> List[str]:
        """Return list of all locally installed model tags."""
        try:
            res = ollama.list()
            names = []
            models_list = getattr(res, "models", None) or res.get("models", [])
            for item in models_list:
                if hasattr(item, "model"):
                    names.append(item.model)
                elif isinstance(item, dict) and "name" in item:
                    names.append(item["name"])
                elif isinstance(item, dict) and "model" in item:
                    names.append(item["model"])
            return names
        except Exception:
            return []

    @classmethod
    def get_coding_models(cls) -> List[str]:
        """Return installed models suitable for code generation and editing."""
        installed = cls.list_installed_models()
        coding = []
        for m in installed:
            m_lower = m.lower()
            if any(pat in m_lower for pat in PREFERRED_CODING_PATTERNS):
                coding.append(m)

        # Fallback to any installed model if no explicit coding model found
        return coding if coding else installed

    @classmethod
    def get_general_models(cls) -> List[str]:
        """Return installed models suitable for lightweight conversation and planning."""
        installed = cls.list_installed_models()
        general = []
        for m in installed:
            m_lower = m.lower()
            if any(pat in m_lower for pat in PREFERRED_GENERAL_PATTERNS):
                general.append(m)

        return general if general else installed

    @classmethod
    def select_best_model(cls, task: str) -> str:
        """
        Dynamically selects the best installed local model for a task.
        Does NOT mandate downloading a new model if a suitable model already exists locally.
        """
        task_norm = (task or "").lower()
        installed = cls.list_installed_models()

        if not installed:
            # Fallback default if no model installed
            return "qwen2.5-coder:3b"

        coding_models = cls.get_coding_models()
        general_models = cls.get_general_models()

        # Tasks requiring specialized coding capability
        if task_norm in {"edit", "modify", "create", "debug", "deployment"}:
            if coding_models:
                # Prefer explicitly labeled coder models
                for m in coding_models:
                    if "coder" in m.lower() or "code" in m.lower():
                        return m
                return coding_models[0]
            return installed[0]

        # Tasks requiring lightweight planning / search / explanation / conversation
        if task_norm in {"planner", "search", "explain", "conversational", "follow_up", "analyze"}:
            if general_models:
                # Prefer lightweight models like phi3 or llama
                for m in general_models:
                    if "phi3" in m.lower() or "mini" in m.lower():
                        return m
                return general_models[0]
            return installed[0]

        return installed[0]

    @classmethod
    def recommend_default_model(cls) -> Tuple[str, str]:
        """
        Recommends appropriate fallback coding model based on available RAM resources.
        Returns (model_name, size_estimate_str).
        """
        resources = get_system_resources()
        ram_gb = resources.get("ram_available_gb", 8.0)

        if ram_gb >= 8.0:
            return ("qwen2.5-coder:3b", "~2.0 GB")
        elif ram_gb >= 4.0:
            return ("qwen2.5-coder:3b", "~2.0 GB")
        else:
            return ("phi3:mini", "~2.2 GB")
