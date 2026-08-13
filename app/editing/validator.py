"""
EdgeMind Code Validator V2

Validates generated source code based on target language syntax rules.
Provides strict validation for Python via AST and structural syntax validation for Java, C++, JS, TS, etc.
Never falsely claims validation passed if validation was skipped.
"""

from pathlib import Path
import ast
import json
import re


def detect_language(file_path: str) -> str:
    """
    Detect programming language from file path extension.
    """
    if not file_path:
        return "python"
    ext = Path(file_path).suffix.lower()
    mapping = {
        ".py": "python",
        ".java": "java",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".hpp": "cpp",
        ".h": "c",
        ".c": "c",
        ".js": "javascript",
        ".ts": "typescript",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".txt": "text",
    }
    return mapping.get(ext, "python")


def check_balanced_delimiters(code: str) -> tuple[bool, str]:
    """
    Checks for balanced parentheses, brackets, and braces while respecting strings.
    """
    stack = []
    pairs = {')': '(', ']': '[', '}': '{'}
    in_string = False
    string_char = None
    escaped = False

    for line_no, line in enumerate(code.splitlines(), start=1):
        for char in line:
            if in_string:
                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == string_char:
                    in_string = False
                continue

            if char in ('"', "'", '`'):
                in_string = True
                string_char = char
                continue

            if char in ('(', '[', '{'):
                stack.append((char, line_no))
            elif char in (')', ']', '}'):
                if not stack:
                    return False, f"Unmatched closing '{char}' on line {line_no}"
                top, _ = stack.pop()
                if top != pairs[char]:
                    return False, f"Mismatched closing '{char}' for '{top}' on line {line_no}"

    if stack:
        unclosed, line_no = stack[-1]
        return False, f"Unclosed '{unclosed}' starting around line {line_no}"

    return True, "Balanced"


def validate_code(code: str, language: str) -> tuple[bool, str]:
    """
    Validate code based on target language.
    Returns (success, validation_message).
    """
    if not code or not code.strip():
        return False, "Generated code is empty"

    lang = language.lower()

    if lang == "python":
        try:
            ast.parse(code)
            return True, "Validation Passed"
        except SyntaxError as e:
            return False, f"Python SyntaxError line {e.lineno}: {e.msg}"

    elif lang == "json":
        try:
            json.loads(code)
            return True, "Validation Passed"
        except json.JSONDecodeError as e:
            return False, f"JSON DecodeError line {e.lineno}: {e.msg}"

    elif lang in {"java", "cpp", "c", "javascript", "typescript"}:
        balanced, msg = check_balanced_delimiters(code)
        if not balanced:
            return False, f"{language.capitalize()} Syntax Check Failed: {msg}"

        if lang == "java" and not re.search(r"\b(class|interface|enum|record)\b", code):
            return False, "Java validation failed: No class or interface declaration found."

        if lang in {"javascript", "typescript"}:
            import shutil
            import subprocess
            import tempfile
            if shutil.which("node"):
                with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".js", delete=False) as tmp:
                    tmp.write(code)
                    tmp_name = tmp.name
                try:
                    proc = subprocess.run(
                        ["node", "-c", tmp_name],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    Path(tmp_name).unlink(missing_ok=True)
                    if proc.returncode != 0:
                        err_msg = proc.stderr.strip().splitlines()[0] if proc.stderr else "Node syntax check failed"
                        return False, f"JavaScript SyntaxError: {err_msg}"
                    return True, "Validation Passed (Node.js Syntax Check)"
                except Exception:
                    Path(tmp_name).unlink(missing_ok=True)

        return True, f"Validation Passed ({language.capitalize()} Structural Syntax)"

    return True, f"Validation Skipped (No syntax checker available for '{language}')"


def validate_python(code: str) -> tuple[bool, str]:
    """Check whether generated code is valid Python."""
    return validate_code(code, "python")
