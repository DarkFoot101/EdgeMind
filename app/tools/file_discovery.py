"""
EdgeMind Autonomous File Discovery Tool

Searches and ranks project files based on user query, intent,
keywords, symbols, or relative file patterns.
Strictly respects project root security boundaries.
"""

from pathlib import Path
import re

IGNORED_DIRS = {
    ".git",
    ".edgemind",
    "backups",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".pytest_cache",
    "edgemind.egg-info",
    "build",
    "dist",
}

IGNORED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".zip",
    ".tar",
    ".gz",
}


def search_project_files(
    query: str,
    project_path: str = ".",
    limit: int = 5,
) -> list[str]:
    """
    Find and rank candidate files within the project root matching the query.
    Returns relative path strings.
    """
    project_root = Path(project_path).resolve()
    if not project_root.is_dir():
        return []

    # 1. Clean query terms (extract potential filenames, keywords, identifiers)
    raw_tokens = re.findall(r"[A-Za-z0-9_\-\./\\]+", query)
    search_terms = set(t.lower() for t in raw_tokens if len(t) > 2)

    # Specific check for potential filename tokens in query (e.g. bad.py, fib.java)
    file_tokens = re.findall(r"[\w./\\-]+\.[A-Za-z0-9]+", query)
    file_names = set(Path(f).name.lower() for f in file_tokens)

    candidates: list[tuple[int, Path]] = []

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue

        # Check ignored directories
        if any(ignored in path.parts for ignored in IGNORED_DIRS):
            continue

        # Check ignored extensions
        if path.suffix.lower() in IGNORED_EXTENSIONS:
            continue

        score = 0
        rel_path_str = str(path.relative_to(project_root)).replace("\\", "/")
        file_stem = path.stem.lower()
        file_name = path.name.lower()

        # Score matching exact file token
        if file_name in file_names or rel_path_str.lower() in [f.lower() for f in file_tokens]:
            score += 100

        # Score path name matching search terms
        for term in search_terms:
            if term in file_name:
                score += 40
            elif term in rel_path_str.lower():
                score += 20

        # Content keyword search for source/text files (< 500 KB)
        if path.stat().st_size < 500_000:
            try:
                content = path.read_text(encoding="utf-8", errors="ignore").lower()
                for term in search_terms:
                    # Skip generic python keywords
                    if term in {"def", "class", "return", "import", "from", "the", "and", "for", "with", "this"}:
                        continue
                    if term in content:
                        score += content.count(term) * 5
            except Exception:
                pass

        if score > 0:
            candidates.append((score, path))

    # Sort descending by score, then alphabetically
    candidates.sort(key=lambda item: (-item[0], item[1].as_posix()))

    results = []
    seen = set()
    for _, path in candidates:
        rel_str = str(path.relative_to(project_root))
        if rel_str not in seen:
            seen.add(rel_str)
            results.append(rel_str)
            if len(results) >= limit:
                break

    return results


def resolve_best_file(
    query: str,
    project_path: str = ".",
    active_file: str | None = None,
) -> str | None:
    """
    Determine the single best file candidate for a query.
    If query uses pronoun/continuation without new file specification, returns active_file.
    """
    project_root = Path(project_path).resolve()

    # Direct filename check in query
    file_tokens = re.findall(r"[\w./\\-]+\.[A-Za-z0-9]+", query)
    if file_tokens:
        for token in file_tokens:
            token_clean = token.strip("'\" ")
            candidate = project_root / token_clean
            if candidate.exists() and candidate.is_file():
                if not any(ignored in candidate.parts for ignored in IGNORED_DIRS):
                    return str(candidate.resolve())

            # Check rglob match for basename
            search_name = Path(token_clean).name
            for match in project_root.rglob(search_name):
                if match.is_file() and not any(ignored in match.parts for ignored in IGNORED_DIRS):
                    return str(match.resolve())

    # Check search candidates
    candidates = search_project_files(query, project_path, limit=5)
    if candidates:
        return str((project_root / candidates[0]).resolve())

    # Fallback to active file if available
    if active_file and Path(active_file).exists():
        return str(Path(active_file).resolve())

    # Fallback: find any primary source code file in project root
    source_exts = {".py", ".java", ".js", ".ts", ".cpp", ".c", ".go", ".rs"}
    all_source_files = []
    for path in project_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in source_exts:
            if not any(ignored in path.parts for ignored in IGNORED_DIRS):
                is_test = "test" in path.name.lower() or "tests" in path.parts
                all_source_files.append((0 if not is_test else 1, path))

    if all_source_files:
        all_source_files.sort(key=lambda x: (x[0], x[1].as_posix()))
        return str(all_source_files[0][1].resolve())

    return None
