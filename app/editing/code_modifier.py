# generates modified code
"""
EdgeMind Code Modifier

Generates modified source code using a local LLM.

Responsibilities
----------------
1. Read source code
2. Construct editing prompt
3. Generate modified code
4. Return generated code

This module NEVER writes files.
"""

from app.models.ollama_client import query_model 

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
    source_code : str, 
    instruction : str, 
    model : str = "qwen2.5-coder:3b"
) -> str :
    """
    Generate updated source code.

    Parameters
    ----------
    source_code : str
        Original file contents.

    instruction : str
        User editing request.

    model : str
        Local Ollama model.

    Returns
    -------
    str
        Modified source code.
    """

    prompt = f"""
        User Instruction:
        {instruction}
        Original Source Code:
        {source_code}
        Return the complete modified source code.
    """

    response = query_model(
        prompt = prompt,
        model= model,
        system_prompt = SYSTEM_PROMPT
    )
    return response.strip()