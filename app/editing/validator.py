# validates the edited code 
"""
EdgeMind Code Validator

Validates generated source code before
allowing it to overwrite existing files.
"""

from pathlib import Path


def detect_language(file_path: str) -> str:
    """
    Detect programming language from file path extension.
    """
    if not file_path:
        return "text"
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
    return mapping.get(ext, "text")


def validate_code(code: str, language: str) -> tuple[bool, str]:
    """
    Validate code based on target language.
    """
    if not code.strip():
        return (
            False,
            "Generated code is empty"
        )

    if language.lower() == "python":
        import ast
        try:
            ast.parse(code)
        except SyntaxError as e:
            return (
                False,
                f"Syntax Error: {e}"
            )
        return (
            True,
            "Validation Passed"
        )

    # For other languages, we do basic sanity checking
    return (
        True,
        f"Validation Passed for {language}"
    )


def validate_python(code: str) -> tuple[bool, str]:
    """
    Check whether generated code is valid Python. Retained for backward compatibility.
    """
    return validate_code(code, "python")
