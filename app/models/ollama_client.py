"""Small adapter around Ollama's local chat API with telemetry."""

from dataclasses import dataclass
import logging
import time
from typing import Optional

import ollama

logger = logging.getLogger(__name__)


@dataclass
class GenerationMetadata:
    """Detailed response content and performance telemetry."""

    content: str
    inference_time_seconds: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


def _extract_metric(obj, key, default=0):
    if hasattr(obj, key):
        return getattr(obj, key) or default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def generate_response_detailed(
    prompt: str,
    model: str = "qwen2.5-coder:3b",
    system_prompt: Optional[str] = None,
    options: Optional[dict] = None,
    keep_alive: str = "10m",
) -> GenerationMetadata:
    """Generate a response from a local Ollama model with timing and token telemetry."""
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
    elapsed = end - start

    logger.info("Inference time: %.2fs", elapsed)

    # Extract text content safely
    if isinstance(response, dict):
        msg = response.get("message", {})
        content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
    else:
        msg = getattr(response, "message", None)
        content = getattr(msg, "content", "") if msg else ""

    # Extract token metrics safely
    prompt_eval_count = _extract_metric(response, "prompt_eval_count", 0)
    eval_count = _extract_metric(response, "eval_count", 0)

    # If Ollama didn't populate tokens (e.g. in mocked test environments), provide approximate token estimate
    if prompt_eval_count == 0 and prompt:
        prompt_eval_count = max(1, int(len(prompt.split()) * 1.3))
    if eval_count == 0 and content:
        eval_count = max(1, int(len(content.split()) * 1.3))

    total_tokens = prompt_eval_count + eval_count

    return GenerationMetadata(
        content=content,
        inference_time_seconds=round(elapsed, 3),
        prompt_tokens=prompt_eval_count,
        completion_tokens=eval_count,
        total_tokens=total_tokens,
    )


def generate_response(
    prompt: str,
    model: str = "qwen2.5-coder:3b",
    system_prompt: Optional[str] = None,
    options: Optional[dict] = None,
    keep_alive: str = "10m",
) -> str:
    """Generate a response from a local Ollama model."""
    meta = generate_response_detailed(
        prompt=prompt,
        model=model,
        system_prompt=system_prompt,
        options=options,
        keep_alive=keep_alive,
    )
    return meta.content
