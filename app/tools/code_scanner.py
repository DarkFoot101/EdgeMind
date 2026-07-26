from pathlib import Path

IGNORE_DIRS = {
    "venv",
    "__pycache__",
    ".git",
    ".pytest_cache",
    "node_modules"
}

def scan_project(project_path: str = ".") -> dict[str, str | int | bool]:
    """Return lightweight metadata for a Python project directory."""

    project = Path(project_path).resolve()
    if not project.is_dir():
        raise NotADirectoryError(project)

    python_files = []
    total_files = 0

    for file in project.rglob("*"):
        if any(
            part in IGNORE_DIRS
            for part in file.parts
        ):
            continue

        if not file.is_file():
            continue

        total_files += 1
        if file.suffix != ".py":
            continue

        python_files.append(file)

    return {
        "project_name" : project.resolve().name,
        "language_detected" : "Python",
        "python_files": len(python_files),
        "total_files": total_files,
        "requirements_exists":
            (project / "requirements.txt").exists(),

        "dockerfile_exists":
            (project / "Dockerfile").exists(),

        "readme_exists":
            (project / "README.md").exists()
    }
