from pathlib import Path 

IGNORE_DIRS = {
    "venv",
    "__pycache__",
    ".git",
    ".pytest_cache",
    "node_modules"
}

def scan_project(project_path : "."):
    project = Path(project_path) 

    python_files = []

    for file in project.rglob("*.py"):

        if any(
            part in IGNORE_DIRS
            for part in file.parts
        ):
            continue

        python_files.append(file)

    return {
        "project_name" : project.resolve().name,
        "language_detected" : "Python",
        "python_files": len(python_files),
        "total_files": len(
            [f for f in project.rglob("*") if f.is_file()]
        ),
        "requirements_exists":
            (project / "requirements.txt").exists(),

        "dockerfile_exists":
            (project / "Dockerfile").exists(),

        "readme_exists":
            (project / "README.md").exists()
    }