"""
EdgeMind Edit Scoping Subsystem

Provides surgical, targeted code extraction and splicing:
- Full file scoping (default)
- Line range scoping (e.g. lines 15-35)
- AST and syntactic symbol scoping (e.g. function or class by name)
- Search-and-replace block scoping
"""

import ast
from dataclasses import dataclass
from enum import Enum
import re
from typing import Optional, Tuple


class EditScopeType(str, Enum):
    """Granularity of edit operations."""

    FULL_FILE = "full_file"
    LINE_RANGE = "line_range"
    SYMBOL = "symbol"
    SEARCH_REPLACE = "search_replace"

    @classmethod
    def from_str(cls, value: str) -> "EditScopeType":
        if isinstance(value, cls):
            return value
        val_clean = str(value or "").strip().lower()
        for member in cls:
            if member.value == val_clean:
                return member
        return cls.FULL_FILE


@dataclass
class EditScope:
    """Defines targeted edit boundaries within a source file."""

    scope_type: EditScopeType = EditScopeType.FULL_FILE
    start_line: Optional[int] = None  # 1-indexed inclusive
    end_line: Optional[int] = None    # 1-indexed inclusive
    target_symbol: Optional[str] = None  # Function, class, or method name
    search_block: Optional[str] = None
    replace_block: Optional[str] = None

    def __post_init__(self):
        if not isinstance(self.scope_type, EditScopeType):
            self.scope_type = EditScopeType.from_str(str(self.scope_type))


def extract_code_slice(code: str, start_line: int, end_line: int) -> str:
    """
    Extract a slice of lines (1-indexed, inclusive) from source code.
    Normalizes inverted line ranges and clamps bounds safely.
    """
    lines = code.splitlines()
    total_lines = len(lines)
    if total_lines == 0:
        return ""

    if start_line > end_line:
        start_line, end_line = end_line, start_line

    start_idx = max(1, start_line) - 1
    end_idx = min(total_lines, max(1, end_line))
    return "\n".join(lines[start_idx:end_idx])


def splice_code_slice(original_code: str, replacement_code: str, start_line: int, end_line: int) -> str:
    """
    Replace lines between start_line and end_line (1-indexed inclusive) with replacement_code.
    Preserves preceding and following lines intact. Normalizes inverted ranges.
    """
    lines = original_code.splitlines()
    total_lines = len(lines)

    if start_line > end_line:
        start_line, end_line = end_line, start_line

    start_idx = max(0, start_line - 1)
    end_idx = min(total_lines, max(0, end_line))

    pre_lines = lines[:start_idx]
    post_lines = lines[end_idx:]

    replacement_lines = replacement_code.splitlines() if replacement_code else []
    combined = pre_lines + replacement_lines + post_lines

    # Ensure trailing newline if original had one
    result = "\n".join(combined)
    if original_code.endswith("\n"):
        result += "\n"
    return result


def extract_symbol_range(code: str, symbol_name: str, language: str = "python") -> Optional[Tuple[int, int]]:
    """
    Locate start and end line numbers (1-indexed, inclusive) of a function or class.
    Uses AST for Python, and lexical brace matching for other languages.
    """
    if not code or not symbol_name:
        return None

    clean_symbol = symbol_name.strip("() \t\n")
    if "." in clean_symbol:
        clean_symbol = clean_symbol.split(".")[-1].strip("() \t\n")

    lang = language.lower()
    if lang == "python":
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name == clean_symbol:
                        end_ln = getattr(node, "end_lineno", node.lineno)
                        return (node.lineno, end_ln)
        except Exception:
            pass

    # Generic lexical / brace matching fallback (Java, C++, JS, TS, etc. or broken Python)
    lines = code.splitlines()
    target_pattern = rf"\b(?:def|function|class|interface|void|int|double|float|bool|string|[\w<>\[\]]+)\s+{re.escape(clean_symbol)}\b"
    symbol_line_idx = -1

    for idx, line in enumerate(lines):
        if re.search(target_pattern, line) or rf"\b{re.escape(clean_symbol)}\b\s*\(" in line:
            symbol_line_idx = idx
            break

    if symbol_line_idx == -1:
        return None

    # Check for brace-delimited block
    open_braces = 0
    found_first_brace = False
    end_idx = symbol_line_idx

    for idx in range(symbol_line_idx, len(lines)):
        line = lines[idx]
        for ch in line:
            if ch == "{":
                open_braces += 1
                found_first_brace = True
            elif ch == "}":
                open_braces -= 1

        if found_first_brace and open_braces <= 0:
            end_idx = idx
            break

    if found_first_brace:
        return (symbol_line_idx + 1, end_idx + 1)

    # Indentation-based block fallback (Python if AST failed)
    base_indent = len(lines[symbol_line_idx]) - len(lines[symbol_line_idx].lstrip())
    end_idx = symbol_line_idx
    for idx in range(symbol_line_idx + 1, len(lines)):
        line = lines[idx]
        if not line.strip():
            continue
        cur_indent = len(line) - len(line.lstrip())
        if cur_indent <= base_indent:
            break
        end_idx = idx

    return (symbol_line_idx + 1, end_idx + 1)


def apply_search_and_replace(original_code: str, search_block: str, replace_block: str) -> Tuple[bool, str]:
    """
    Search for search_block in original_code and substitute with replace_block.
    Falls back to whitespace-normalized comparison if exact match fails.
    """
    if search_block in original_code:
        return True, original_code.replace(search_block, replace_block, 1)

    # Try stripped line comparison
    norm_search = "\n".join(l.rstrip() for l in search_block.strip().splitlines())
    orig_lines = original_code.splitlines()
    search_lines = norm_search.splitlines()

    for i in range(len(orig_lines) - len(search_lines) + 1):
        window = "\n".join(orig_lines[i : i + len(search_lines)])
        window_norm = "\n".join(l.rstrip() for l in orig_lines[i : i + len(search_lines)])
        if window_norm == norm_search:
            result_lines = orig_lines[:i] + replace_block.splitlines() + orig_lines[i + len(search_lines):]
            res = "\n".join(result_lines)
            if original_code.endswith("\n"):
                res += "\n"
            return True, res

    return False, original_code
