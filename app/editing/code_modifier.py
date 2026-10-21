"""
EdgeMind Code Modifier V2.1

Generates modified, converted, or scoped source code using local Ollama LLMs.
Supports:
- Full file modification / conversion
- Targeted line range editing
- Symbol-level AST editing (functions/classes)
- Search-and-replace block substitution
Never writes files directly.
"""

import re
from typing import List, Optional

from app.editing.models import EditRequest
from app.editing.scope import (
    EditScopeType,
    apply_search_and_replace,
    extract_code_slice,
    extract_symbol_range,
    splice_code_slice,
)
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


def modify_code(request: EditRequest, options: Optional[dict] = None) -> str:
    """
    Generate updated or converted source code via local LLM.
    Dispatches to targeted scope handlers if scoped editing is specified.
    """
    scope = getattr(request, "scope", None)
    scope_type = scope.scope_type if scope else EditScopeType.FULL_FILE

    # 1. Handle targeted search-and-replace
    if scope_type == EditScopeType.SEARCH_REPLACE and scope and scope.search_block:
        if scope.replace_block is not None:
            success, spliced = apply_search_and_replace(
                request.source_code,
                scope.search_block,
                scope.replace_block,
            )
            if success:
                return spliced

        # Generate replacement for search_block via LLM
        prompt = f"""User Instruction:
{request.instruction}

Target Code Block to Modify:
```{request.source_language}
{scope.search_block}
```

Return ONLY the replacement code for this block.
"""
        system_prompt = (
            "You are a Senior Software Engineer. Modify the provided code block according to instructions. "
            "Return ONLY the replacement block. No markdown, no explanations."
        )
        kwargs = {"prompt": prompt, "model": request.model, "system_prompt": system_prompt}
        if options:
            kwargs["options"] = options
        raw = generate_response(**kwargs)
        cleaned_replacement = clean_generated_code(raw)
        success, spliced = apply_search_and_replace(
            request.source_code,
            scope.search_block,
            cleaned_replacement,
        )
        if success:
            return spliced

    # 2. Handle targeted line range editing
    if scope_type == EditScopeType.LINE_RANGE and scope and scope.start_line is not None:
        total_lines = len(request.source_code.splitlines())
        start_ln = max(1, scope.start_line)
        end_ln = min(total_lines, scope.end_line or scope.start_line)
        target_slice = extract_code_slice(request.source_code, start_ln, end_ln)

        prompt = f"""User Instruction:
{request.instruction}

Target Code Slice (Lines {start_ln}-{end_ln} of {request.file_path}):
```{request.source_language}
{target_slice}
```

Return ONLY the updated replacement lines for lines {start_ln} to {end_ln}.
Preserve indentation and do not include code from outside this line range.
"""
        system_prompt = (
            f"You are modifying lines {start_ln} to {end_ln} of a {request.source_language} file. "
            "Output ONLY the replacement code for this slice. No markdown fences, no explanation."
        )
        kwargs = {"prompt": prompt, "model": request.model, "system_prompt": system_prompt}
        if options:
            kwargs["options"] = options
        raw = generate_response(**kwargs)
        cleaned_slice = clean_generated_code(raw)
        return splice_code_slice(request.source_code, cleaned_slice, start_ln, end_ln)

    # 3. Handle targeted AST symbol editing
    if scope_type == EditScopeType.SYMBOL and scope and scope.target_symbol:
        rng = extract_symbol_range(request.source_code, scope.target_symbol, request.source_language)
        if rng:
            start_ln, end_ln = rng
            symbol_code = extract_code_slice(request.source_code, start_ln, end_ln)

            prompt = f"""User Instruction:
{request.instruction}

Target Symbol Definition '{scope.target_symbol}' (Lines {start_ln}-{end_ln}):
```{request.source_language}
{symbol_code}
```

Return ONLY the modified implementation of '{scope.target_symbol}'.
"""
            system_prompt = (
                f"You are modifying the definition of {scope.target_symbol} in a {request.source_language} file. "
                "Output ONLY the complete modified symbol definition. No markdown fences, no commentary."
            )
            kwargs = {"prompt": prompt, "model": request.model, "system_prompt": system_prompt}
            if options:
                kwargs["options"] = options
            raw = generate_response(**kwargs)
            cleaned_symbol = clean_generated_code(raw)
            return splice_code_slice(request.source_code, cleaned_symbol, start_ln, end_ln)

    framework_rule = ""
    framework_context = ""
    if request.project_framework:
        framework_rule = f"\n6. ARCHITECTURAL GUARDRAIL: Adhere strictly to the project architecture: {request.project_framework}. Do NOT introduce incompatible frameworks (e.g., do NOT use Flask syntax in a FastAPI project)."
        framework_context = f"\nProject Architecture & Framework Context:\n<framework-context>\n{request.project_framework}\n</framework-context>\n"

    system_prompt = f"""You are a Principal Software Engineer.
Your task is to modify or convert source code strictly according to user instructions.

Original Language: {request.source_language}
Target Language: {request.target_language}
Operation Mode: {str(request.operation).upper()}

RULES:
1. Return ONLY the complete updated/converted target source code.
2. Do NOT include markdown code block formatting (```).
3. Do NOT include explanations, introduction, or commentary.
4. Preserve existing comments, structure, and formatting wherever appropriate.
5. Never truncate code or leave placeholders like '// TODO: rest of code'.{framework_rule}
"""

    analysis_context = ""
    if request.analysis_result:
        analysis_context = f"\nPrior Analysis Findings & Bug Diagnosis:\n<analysis-findings>\n{request.analysis_result[:2000]}\n</analysis-findings>\n"

    prompt = f"""User Instruction:
{request.instruction}
{framework_context}{analysis_context}
Operation: {"Create a new target file from source" if request.operation == "create" else "Modify existing file in-place"}
Source File Path: {request.file_path}
Target File Path: {request.target_file or request.file_path}

Source Code Data:
<{request.source_language}-source>
{request.source_code}
</{request.source_language}-source>

Return the complete modified or converted source code in target language ({request.target_language}).
"""

    kwargs = {"prompt": prompt, "model": request.model, "system_prompt": system_prompt}
    if options:
        kwargs["options"] = options
    raw_response = generate_response(**kwargs)

    return clean_generated_code(raw_response)


def generate_candidate_patches(request: EditRequest, count: int = 1) -> List[str]:
    """
    Generate multiple candidate patches using local LLM with varying temperature schedules.
    Provides Best-of-N candidate sampling.
    """
    if count <= 1:
        return [modify_code(request)]

    candidates: List[str] = []
    # Primary deterministic generation
    primary = modify_code(request)
    candidates.append(primary)

    temps = [0.3, 0.6, 0.8, 1.0]
    for i in range(1, count):
        temp = temps[(i - 1) % len(temps)]
        try:
            cand = modify_code(request, options={"temperature": temp})
            if cand:
                candidates.append(cand)
        except Exception:
            break

    return candidates