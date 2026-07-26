import ast
import sys
from pathlib import Path

STDLIB = set(sys.stdlib_module_names)


def _local_module_names(project: Path) -> set[str]:
    """Return import roots provided by the project itself."""

    return {
        path.stem
        for path in project.iterdir()
        if path.suffix == ".py"
    } | {
        path.name
        for path in project.iterdir()
        if path.is_dir() and (path / "__init__.py").exists()
    }


def extract_imports(project_path: str = ".") -> list[str]:
    """Extract third-party import roots from Python files in a project."""

    imports = set()
    project = Path(project_path).resolve()
    if not project.is_dir():
        raise NotADirectoryError(project)

    local_modules = _local_module_names(project)

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

        except (OSError, SyntaxError, UnicodeDecodeError):
            continue

    filtered_imports = [
        pkg
        for pkg in imports
        if pkg not in STDLIB and pkg not in local_modules
    ]

    return sorted(filtered_imports)

def save_requirements(project_path: str = ".") -> list[str]:
    """Write discovered third-party imports to ``requirements.txt``."""

    imports = extract_imports(
        project_path
    )

    output_path = Path(project_path) / "requirements.txt"
    with output_path.open("w", encoding="utf-8") as file:

        for package in imports:
            file.write(f"{package}\n")

    return imports
