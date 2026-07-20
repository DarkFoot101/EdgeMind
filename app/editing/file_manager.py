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
import shutil


BACKUP_DIR = Path(".edgemind/backups")


def ensure_backup_directory():
    """
    Create the backup directory if it does not exist.
    """

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


def read_file(file_path: str) -> str:
    """
    Read the contents of a file.
    """

    file = Path(file_path)

    if not file.exists():
        raise FileNotFoundError(file)

    return file.read_text(
        encoding="utf-8"
    )


def backup_file(file_path: str) -> str:
    """
    Save a backup inside .edgemind/backups, preserving the full
    relative path structure to avoid filename collisions.
    """

    ensure_backup_directory()

    file = Path(file_path).resolve()

    # Recreate the full directory structure under BACKUP_DIR
    # e.g. src/utils.py -> .edgemind/backups/src/utils.py
    relative = Path(file_path)
    backup_path = BACKUP_DIR / relative

    backup_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    shutil.copy(
        file,
        backup_path
    )

    return str(backup_path)


def write_file(
    file_path: str,
    content: str
):
    """
    Overwrite a source file.
    """

    Path(file_path).write_text(
        content,
        encoding="utf-8"
    )


def restore_backup(file_path: str):
    """
    Restore a file from backup.
    """

    file = Path(file_path)

    # Mirror the same path structure used in backup_file
    backup = BACKUP_DIR / file

    if not backup.exists():
        raise FileNotFoundError(
            "Backup not found."
        )

    shutil.copy(
        backup,
        file
    )