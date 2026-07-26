"""
EdgeMind File Manager

Responsible for all filesystem operations.

Responsibilities
----------------
1. Read files
2. Create automatic backups
3. Restore backups
4. Write modified files

No AI logic should exist in this module.
"""

from pathlib import Path
import os
import shutil
import tempfile


BACKUP_DIR = Path(".edgemind/backups")


def _resolve_project_file(file_path: str) -> Path:
    """Resolve an existing file and ensure it belongs to this project."""

    project_root = Path.cwd().resolve()
    file = Path(file_path).expanduser().resolve()
    try:
        file.relative_to(project_root)
    except ValueError as exc:
        raise ValueError("File path must be inside the current project.") from exc

    if not file.exists():
        raise FileNotFoundError(file)
    if not file.is_file():
        raise IsADirectoryError(file)
    return file


def ensure_backup_directory() -> Path:
    """
    Create the backup directory if it does not exist.
    """

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )
    return BACKUP_DIR.resolve()


def read_file(file_path: str) -> str:
    """
    Read the contents of a file.
    """

    file = _resolve_project_file(file_path)
    return file.read_text(
        encoding="utf-8"
    )


def backup_file(file_path: str) -> str:
    """
    Save a backup inside .edgemind/backups, preserving the full
    relative path structure to avoid filename collisions.
    """

    backup_root = ensure_backup_directory()
    file = _resolve_project_file(file_path)
    relative = file.relative_to(Path.cwd().resolve())
    backup_path = backup_root / relative

    backup_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    shutil.copy2(
        file,
        backup_path
    )

    return str(backup_path)


def write_file(
    file_path: str,
    content: str
) -> None:
    """
    Overwrite a source file.
    """

    file = _resolve_project_file(file_path)
    original_mode = file.stat().st_mode
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


def restore_backup(file_path: str) -> None:
    """
    Restore a file from backup.
    """

    file = _resolve_project_file(file_path)
    backup = BACKUP_DIR.resolve() / file.relative_to(Path.cwd().resolve())

    if not backup.exists():
        raise FileNotFoundError(
            "Backup not found."
        )

    write_file(str(file), backup.read_text(encoding="utf-8"))
