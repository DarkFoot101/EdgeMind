"""
EdgeMind Safe Project File Reader Tool
"""

from pathlib import Path
from app.editing.file_manager import read_file


def safe_read_file(file_path: str, project_path: str = ".", max_bytes: int = 200_000) -> str:
    """
    Read contents of a project file safely up to max_bytes.
    """
    content = read_file(file_path, project_path)
    if len(content) > max_bytes:
        return content[:max_bytes] + f"\n...[Truncated: File exceeded {max_bytes} bytes]"
    return content
