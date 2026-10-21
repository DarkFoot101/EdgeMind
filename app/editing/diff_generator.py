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


def compute_diff_stats(diff_text: str) -> tuple[int, int]:
    """
    Calculate the number of added and deleted lines from unified diff text.
    Returns (lines_added, lines_deleted).
    """
    if not diff_text:
        return 0, 0

    added = 0
    deleted = 0
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            deleted += 1

    return added, deleted


def colorize_diff(diff_text: str, use_color: bool = True) -> str:
    """
    Renders unified diff text with vibrant ANSI terminal color codes:
    - Red for deletions (-)
    - Green for additions (+)
    - Cyan for chunk headers (@@)
    - Bold yellow/white for file metadata (---, +++)
    """
    if not diff_text or not use_color:
        return diff_text

    RED = "\033[91m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    BOLD_YELLOW = "\033[1;33m"
    RESET = "\033[0m"

    colored_lines = []
    for line in diff_text.splitlines():
        if line.startswith("---") or line.startswith("+++"):
            colored_lines.append(f"{BOLD_YELLOW}{line}{RESET}")
        elif line.startswith("@@"):
            colored_lines.append(f"{CYAN}{line}{RESET}")
        elif line.startswith("-"):
            colored_lines.append(f"{RED}{line}{RESET}")
        elif line.startswith("+"):
            colored_lines.append(f"{GREEN}{line}{RESET}")
        else:
            colored_lines.append(line)

    return "\n".join(colored_lines)