"""
EdgeMind Code Modifier

Generates modified source code using a local LLM.

This module NEVER writes files.
"""

from app.models.ollama_client import query_model
from app.editing.models import EditRequest

SYSTEM_PROMPT = """
You are an expert Python software engineer.
Your task is to modify existing source code.
Rules
- Return ONLY the complete updated file.
- Do NOT explain.
- Do NOT use markdown.
- Do NOT wrap inside ``` blocks.
- Preserve formatting.
- Preserve comments whenever possible.
- Only modify what the instruction requests.
- Never truncate code.
"""

def modify_code(
    request: EditRequest
) -> str:
    """
    Generate updated source code.
    """
    prompt = f"""
        User Instruction:
        {request.instruction}
        Original Source Code:
        {request.source_code}
        Return the complete modified source code.
    """

    response = query_model(
        prompt=prompt,
        model=request.model,
        system_prompt=SYSTEM_PROMPT,
    )

    return response.strip()