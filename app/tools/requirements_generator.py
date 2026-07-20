import ast
from pathlib import Path

STDLIB = {
    "os",
    "sys",
    "json",
    "time",
    "pathlib",
    "typing",
    "ast",
    "re",
    "collections",
    "datetime"
}

def extract_imports(project_path="."):

    imports = set()
    
    project = Path(project_path)

    for py_file in project.rglob("*.py"):

        # ignore venv/cache/git
        if any(
            ignored in py_file.parts
            for ignored in {
                "venv",
                ".venv",
                "__pycache__",
                ".git"
            }
        ):
            continue

        try:

            source = py_file.read_text(
                encoding="utf-8"
            )

            tree = ast.parse(source)

            for node in ast.walk(tree):

                if isinstance(node, ast.Import):

                    for alias in node.names:
                        imports.add(
                            alias.name.split(".")[0]
                        )

                elif isinstance(
                    node,
                    ast.ImportFrom
                ):

                    if node.module:

                        imports.add(
                            node.module.split(".")[0]
                        )

        except Exception:
            continue

    filtered_imports = [
        pkg
        for pkg in imports
        if pkg not in STDLIB
    ]

    return sorted(filtered_imports)

def save_requirements(project_path="."):

    imports = extract_imports(
        project_path
    )

    output_path = Path(project_path) / "requirements.txt"
    with open(output_path, "w") as f:

        for package in imports:
            f.write(f"{package}\n")

    return imports