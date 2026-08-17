"""
EdgeMind V2.1 Autonomous File Discovery Tool

Searches, ranks, and resolves project files based on query, context, and intent.
Strictly respects project root security boundaries and excludes backup/internal directories.
"""

from pathlib import Path
import re
from typing import Optional

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
    ".bak",
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

        # Check ignored directories & backup filenames
        if any(ignored in path.parts for ignored in IGNORED_DIRS) or path.name.endswith(".bak"):
            continue

        # Check ignored extensions
        if path.suffix.lower() in IGNORED_EXTENSIONS:
            continue

        score = 0
        rel_path_str = str(path.relative_to(project_root)).replace("\\", "/")
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
    Prioritizes pronoun/continuation references and active_file before blind filesystem search.
    Guarantees backups (.bak, .edgemind/backups) are NEVER returned.
    """
    project_root = Path(project_path).resolve()
    query_lower = (query or "").lower()

    # 1. Pronoun and continuation resolution from active context
    words = set(re.findall(r"\b\w+\b", query_lower))
    pronouns = {"it", "that", "file", "code", "optimize", "fix", "again", "changed", "what", "undo", "explain"}
    has_pronouns = not words.isdisjoint(pronouns)
    file_tokens = re.findall(r"[\w./\\-]+\.[A-Za-z0-9]+", query)

    # If query uses pronouns without specifying a brand new filename, return active_file if valid
    if has_pronouns and not file_tokens and active_file:
        active_path = Path(active_file)
        if not active_path.is_absolute():
            active_path = (project_root / active_path).resolve()
        if active_path.exists() and active_path.is_file():
            if not any(ignored in active_path.parts for ignored in IGNORED_DIRS) and not active_path.name.endswith(".bak"):
                return str(active_path)

    # 2. Direct filename match in query
    if file_tokens:
        for token in file_tokens:
            token_clean = token.strip("'\" ")
            candidate = project_root / token_clean
            if candidate.exists() and candidate.is_file():
                if not any(ignored in candidate.parts for ignored in IGNORED_DIRS) and not candidate.name.endswith(".bak"):
                    return str(candidate.resolve())

            # Check rglob match for basename
            search_name = Path(token_clean).name
            for match in project_root.rglob(search_name):
                if match.is_file() and not any(ignored in match.parts for ignored in IGNORED_DIRS) and not match.name.endswith(".bak"):
                    return str(match.resolve())

    # 3. Search candidates in project
    candidates = search_project_files(query, project_path, limit=5)
    if candidates:
        cand_path = (project_root / candidates[0]).resolve()
        if cand_path.exists() and not cand_path.name.endswith(".bak"):
            return str(cand_path)

    # 4. Fallback to active file if available
    if active_file:
        act_p = Path(active_file)
        if not act_p.is_absolute():
            act_p = (project_root / act_p).resolve()
        if act_p.exists() and not act_p.name.endswith(".bak") and not any(ignored in act_p.parts for ignored in IGNORED_DIRS):
            return str(act_p)

    # 5. Fallback: find primary source code file in project root
    source_exts = {".py", ".java", ".js", ".ts", ".cpp", ".c", ".go", ".rs"}
    all_source_files = []
    for path in project_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in source_exts:
            if not any(ignored in path.parts for ignored in IGNORED_DIRS) and not path.name.endswith(".bak"):
                is_test = "test" in path.name.lower() or "tests" in path.parts
                all_source_files.append((0 if not is_test else 1, path))

    if all_source_files:
        all_source_files.sort(key=lambda x: (x[0], x[1].as_posix()))
        return str(all_source_files[0][1].resolve())

    return None
