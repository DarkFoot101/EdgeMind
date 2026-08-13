"""
EdgeMind File Manager V2

Handles all secure filesystem operations within the active project directory:
1. Read files safely
2. Create automatic backups
3. Restore backups
4. Write modified files atomically
5. Create new target files safely

No AI logic should exist in this module.
"""

from pathlib import Path
import os
import shutil
import tempfile


BACKUP_DIR = Path(".edgemind/backups")


def get_project_root(project_path: str = ".") -> Path:
    """Return normalized absolute Path of project root."""
    return Path(project_path).expanduser().resolve()


def validate_project_path(file_path: str, project_path: str = ".") -> Path:
    """
    Ensure a file path is safely contained inside the current project root.
    Prevents directory traversal attacks (e.g., ../ outside project).
    """
    project_root = get_project_root(project_path)
    file = Path(file_path).expanduser().resolve()

    try:
        file.relative_to(project_root)
    except ValueError as exc:
        raise ValueError(f"Security error: Path '{file}' is outside project root '{project_root}'.") from exc

    # Reject operations in forbidden internal system directories unless explicit
    forbidden_parts = {".git", ".edgemind/backups", "node_modules", "venv", ".venv"}
    rel_parts = set(file.relative_to(project_root).parts)
    if forbidden_parts.intersection(rel_parts) and not str(file).startswith(str(project_root / BACKUP_DIR)):
        raise ValueError(f"Security error: Modifications to internal directory '{file}' are disallowed.")

    return file


def _resolve_project_file(file_path: str, project_path: str = ".") -> Path:
    """Resolve an existing file and ensure it belongs to this project."""
    file = validate_project_path(file_path, project_path)
    if not file.exists():
        raise FileNotFoundError(f"File not found: {file}")
    if not file.is_file():
        raise IsADirectoryError(f"Path is a directory: {file}")
    return file


def ensure_backup_directory(project_path: str = ".") -> Path:
    """Create the backup directory inside project root if it does not exist."""
    project_root = get_project_root(project_path)
    backup_root = (project_root / BACKUP_DIR).resolve()
    backup_root.mkdir(parents=True, exist_ok=True)
    return backup_root


def read_file(file_path: str, project_path: str = ".") -> str:
    """Read the contents of an existing project file."""
    file = _resolve_project_file(file_path, project_path)
    return file.read_text(encoding="utf-8")


def backup_file(file_path: str, project_path: str = ".") -> str:
    """
    Save a backup inside .edgemind/backups, preserving the relative path structure.
    """
    project_root = get_project_root(project_path)
    backup_root = ensure_backup_directory(project_path)
    file = _resolve_project_file(file_path, project_path)

    relative = file.relative_to(project_root)
    backup_path = backup_root / relative

    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file, backup_path)

    return str(backup_path)


def write_file(file_path: str, content: str, project_path: str = ".") -> None:
    """
    Overwrite an existing source file atomically using a temporary file.
    """
    file = _resolve_project_file(file_path, project_path)
    original_mode = file.stat().st_mode if file.exists() else 0o644

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=file.parent,
            delete=False,
        ) as temporary_file:
            temporary_file.write(content)
            temporary_path = Path(temporary_file.name)
        os.chmod(temporary_path, original_mode)
        temporary_path.replace(file)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def restore_backup(file_path: str, project_path: str = ".") -> None:
    """Restore a file from backup."""
    project_root = get_project_root(project_path)
    file = _resolve_project_file(file_path, project_path)
    backup = (project_root / BACKUP_DIR / file.relative_to(project_root)).resolve()

    if not backup.exists():
        raise FileNotFoundError(f"Backup not found for: {file_path}")

    write_file(str(file), backup.read_text(encoding="utf-8"), project_path=project_path)


def create_file(file_path: str, content: str, project_path: str = ".", overwrite: bool = False) -> None:
    """
    Create a new file safely inside the project root.
    """
    file = validate_project_path(file_path, project_path)

    if file.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {file}")

    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")