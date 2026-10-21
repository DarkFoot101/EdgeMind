"""
EdgeMind Candidate Ranker & Best-of-N AST Verification.

Evaluates and ranks generated patch candidates based on:
1. AST syntax validity (ast.parse for Python, balanced delimiters and structure for other languages).
2. Target symbol preservation (if scoped to a specific function or class).
3. Non-destructive edit fidelity (penalizes empty code or disproportionate deletions).
4. Delimiter and bracket balance.
"""

import ast
import re
from typing import List, Optional, Tuple

from app.editing.diff_generator import compute_diff_stats, generate_diff
from app.editing.models import CandidatePatch, EditRequest, EditScopeType
from app.editing.validator import check_balanced_delimiters, validate_code


def evaluate_candidate(
    candidate_id: int,
    content: str,
    request: EditRequest,
    original_code: str,
) -> CandidatePatch:
    """Evaluate a single candidate patch and assign a quality/AST verification score."""
    if not content or not content.strip():
        return CandidatePatch(
            candidate_id=candidate_id,
            content="",
            syntax_valid=False,
            validation_message="Candidate code is empty",
            score=0.0,
            lines_added=0,
            lines_deleted=0,
        )

    # 1. AST / Language Syntax Validation (Weight: 100 points)
    syntax_valid, validation_msg = validate_code(content, request.target_language)
    score = 100.0 if syntax_valid else 0.0

    # 2. Structural & Delimiter Balance (Weight: 15 points)
    balanced, balance_msg = check_balanced_delimiters(content)
    if balanced:
        score += 15.0
    else:
        score = max(0.0, score - 10.0)

    # 3. Target Symbol Preservation (Weight: 25 points)
    target_sym = request.target_symbol or (
        request.scope.target_symbol if getattr(request, "scope", None) else None
    )
    if target_sym:
        clean_sym = target_sym.strip("() '\"")
        if request.target_language.lower() == "python":
            try:
                tree = ast.parse(content)
                found = any(
                    isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                    and n.name == clean_sym
                    for n in ast.walk(tree)
                )
                if found:
                    score += 25.0
                elif re.search(rf"\b{re.escape(clean_sym)}\b", content):
                    score += 10.0
            except SyntaxError:
                if re.search(rf"\b{re.escape(clean_sym)}\b", content):
                    score += 5.0
        else:
            if re.search(rf"\b{re.escape(clean_sym)}\b", content):
                score += 25.0

    # 4. Non-destructive Edit Fidelity / Minimal Diff Distance (Weight: up to 20 points)
    diff = ""
    lines_added = 0
    lines_deleted = 0
    if original_code:
        diff = generate_diff(original=original_code, modified=content, filename="patch")
        lines_added, lines_deleted = compute_diff_stats(diff)

        orig_lines = max(1, len(original_code.splitlines()))
        # If modifying and deleted > 90% of file without instruction to clear:
        if str(request.operation).lower() not in {"create"} and lines_deleted > orig_lines * 0.9 and orig_lines > 5:
            score = max(0.0, score - 20.0)
        else:
            preservation_ratio = max(0.0, 1.0 - (lines_deleted / (orig_lines * 2.0)))
            score += round(preservation_ratio * 20.0, 2)

    return CandidatePatch(
        candidate_id=candidate_id,
        content=content,
        syntax_valid=syntax_valid,
        validation_message=validation_msg,
        score=round(score, 2),
        lines_added=lines_added,
        lines_deleted=lines_deleted,
    )


def rank_candidates(
    candidates: List[str],
    request: EditRequest,
    original_code: str,
) -> Tuple[CandidatePatch, List[CandidatePatch]]:
    """
    Ranks multiple candidates and returns (best_candidate, all_evaluated_candidates).
    Sorts primarily by syntax validity, then composite score, then minimal lines deleted.
    """
    if not candidates:
        empty = evaluate_candidate(1, "", request, original_code)
        return empty, [empty]

    evaluated: List[CandidatePatch] = []
    for idx, content in enumerate(candidates, start=1):
        evaluated.append(evaluate_candidate(idx, content, request, original_code))

    sorted_candidates = sorted(
        evaluated,
        key=lambda c: (c.syntax_valid, c.score, -c.lines_deleted),
        reverse=True,
    )

    best_candidate = sorted_candidates[0]
    return best_candidate, evaluated
