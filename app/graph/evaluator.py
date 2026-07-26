"""Execution-result evaluation for the graph."""


def evaluate_execution(result: object) -> bool:
    """Return whether a task produced a non-empty, non-error result."""

    if result is None:
        return False

    if not result:
        return False

    if isinstance(result, str):
        normalized = result.strip().lower()
        if not normalized:
            return False
        if normalized.startswith(("error:", "exception:", "traceback")):
            return False

    return True
