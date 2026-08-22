"""Small adapter around Ollama's local chat API."""

import logging
import time
from typing import Optional

import ollama

logger = logging.getLogger(__name__)


def generate_response(
    prompt: str,
    model: str = "qwen2.5-coder:3b",
    system_prompt: Optional[str] = None,
    options: Optional[dict] = None,
    keep_alive: str = "10m",
) -> str:
    """Generate a response from a local Ollama model."""

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    start = time.perf_counter()

    chat_kwargs = {
        "model": model,
        "messages": messages,
        "keep_alive": keep_alive,
    }
    if options:
        chat_kwargs["options"] = options

    response = ollama.chat(**chat_kwargs)

    end = time.perf_counter()

    logger.info("Inference time: %.2fs", end - start)

    return response["message"]["content"]
