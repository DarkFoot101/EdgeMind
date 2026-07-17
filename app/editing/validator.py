# validates the edited code 
"""
EdgeMind Code Validator

Validates generated source code before
allowing it to overwrite existing files.
"""

import ast

def validate_python(code : str):
    """
    Check whether generated code is valid Python.

    Returns
    -------
    (bool, str)

    success

    message
    """

    if not code.strip():
        return (
            False, 
            "Generated code is empty"
        )
    
    try:
        ast.parse(str)
    except SyntaxError as e:
        return (
            False, 
            f"Syntax Error: {e}"
        )

    return (
        True,
        "Validation Passed"
    )