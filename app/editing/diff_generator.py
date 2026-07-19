# shows differences """
"""EdgeMind Diff Generator

Generates human-readable diffs between
two versions of source code.

No AI logic.
"""

from difflib import unified_diff


def generate_diff(
    original: str,
    modified: str,
    filename: str = "file.py",
) -> str:
    """
    Generate a unified diff.

    Parameters
    ----------
    original : str
        Original source.

    modified : str
        Modified source.

    filename : str
        Display filename.

    Returns
    -------
    str
        Unified diff output.
    """

    diff = unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile=f"{filename} (original)",
        tofile=f"{filename} (modified)",
        lineterm="",
    )

    return "\n".join(diff)