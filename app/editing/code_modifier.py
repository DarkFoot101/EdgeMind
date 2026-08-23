"""
EdgeMind Code Modifier V2

Generates modified or converted source code using local Ollama LLMs.
Never writes files directly.
"""

import re
from app.editing.models import EditRequest
from app.models.ollama_client import generate_response


def clean_generated_code(code: str) -> str:
    """
    Strips markdown code blocks, introductory text, and trailing commentary from LLM output.
    Returns clean, executable source code.
    """
    text = code.strip()

    # 1. Extract content inside markdown code block if present
    code_blocks = re.findall(r"```(?:[a-zA-Z0-9+#\-]+)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if code_blocks:
        # Pick the largest code block
        text = max(code_blocks, key=len).strip()
    elif "```" in text:
        # Code block without closing fence
        match = re.search(r"```(?:[a-zA-Z0-9+#\-]+)?\s*\n?(.*)", text, re.DOTALL)
        if match:
            text = match.group(1).strip()

    # 2. Strip closing XML/HTML tags (e.g. </javascript-source>, </code>, </python-source>)
    text = re.sub(r"</[a-zA-Z0-9_\-]+\s*>", "", text)

    # 3. Strip leading non-code conversational text before first valid code statement
    lines = text.splitlines()
    start_idx = 0
    code_start_pattern = r"^(?:import|from|def|async|class|public|private|protected|package|function|const|let|var|//|/\*|#|@|using|namespace|try|with|if|for|while|struct|enum|interface|include|void|type|export|\"\"\"|'''|[a-zA-Z_]\w*\s*[:=])"
    for idx, line in enumerate(lines):
        line_s = line.strip()
        if not line_s:
            continue
        if re.match(code_start_pattern, line_s):
            start_idx = idx
            break

    text = "\n".join(lines[start_idx:])

    # 4. Strip trailing conversational commentary
    text = re.sub(r"\n+(?:Hope this helps|Let me know|Enjoy|Feel free|Note:|Explanation:|Summary:).*$", "", text, flags=re.IGNORECASE | re.DOTALL)

    return text.strip()


def modify_code(request: EditRequest) -> str:
    """
    Generate updated or converted source code via local LLM.
    Propagates analysis findings into prompt if available.
    """
    system_prompt = f"""You are a Principal Software Engineer.
Your task is to modify or convert source code strictly according to user instructions.

Original Language: {request.source_language}
Target Language: {request.target_language}
Operation Mode: {request.operation.upper()}

RULES:
1. Return ONLY the complete updated/converted target source code.
2. Do NOT include markdown code block formatting (```).
3. Do NOT include explanations, introduction, or commentary.
4. Preserve existing comments, structure, and formatting wherever appropriate.
5. Never truncate code or leave placeholders like '// TODO: rest of code'.
"""

    analysis_context = ""
    if request.analysis_result:
        analysis_context = f"\nPrior Analysis Findings & Bug Diagnosis:\n<analysis-findings>\n{request.analysis_result[:2000]}\n</analysis-findings>\n"

    prompt = f"""User Instruction:
{request.instruction}
{analysis_context}
Operation: {"Create a new target file from source" if request.operation == "create" else "Modify existing file in-place"}
Source File Path: {request.file_path}
Target File Path: {request.target_file or request.file_path}

Source Code Data:
<{request.source_language}-source>
{request.source_code}
</{request.source_language}-source>

Return the complete modified or converted source code in target language ({request.target_language}).
"""

    raw_response = generate_response(
        prompt=prompt,
        model=request.model,
        system_prompt=system_prompt,
    )

    return clean_generated_code(raw_response)