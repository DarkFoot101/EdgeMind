#The Editing Service orchestrates all editing operations, but it does not contain the implementation of those operations.
# It simply coordinates them.

"""
EdgeMind Editing Service
Coordinates the complete editing pipeline.
Responsibilities
----------------
1. Read source file
2. Create backup
3. Generate modified code
4. Validate generated code
5. Generate diff preview
6. Return EditResponse
The service NEVER asks for user input.
The service NEVER writes the modified file during
prepare_edit().
File modifications only occur after explicit approval.
"""

import os
from pathlib import Path
import time
import psutil

from app.editing.diff_generator import compute_diff_stats, generate_diff
from app.editing.file_manager import (
    read_file,
    backup_file,
    write_file,
    restore_backup,
    create_file,
    compute_sha256,
    get_file_sha256,
)
from app.editing.models import (
    CandidatePatch,
    EditRequest,
    EditResponse,
    ExecutionMetrics,
)
from app.editing.validator import validate_code
from app.editing.code_modifier import modify_code, generate_candidate_patches
from app.editing.candidate_ranker import rank_candidates


class EditingService:
    """
    Orchestrates EdgeMind's editing subsystem.
    """

    def prepare_edit(
        self,
        request: EditRequest,
    ) -> EditResponse:
        """
        Generate an edit preview without modifying files.
        Includes execution latency, memory footprint, and patch delta telemetry.
        Supports Best-of-N AST verification and candidate ranking.
        """
        t_start = time.perf_counter()

        try:
            source_path = Path(
                request.file_path
            ).resolve()

            if not source_path.exists():
                raise FileNotFoundError(
                    f"Source file not found: {source_path}"
                )

            source_content = read_file(
                str(source_path),
                project_path=request.project_path,
            )
            source_hash = compute_sha256(source_content)

            request.source_code = source_content
            request.source_hash = source_hash

            if request.operation == "create":
                if not request.target_file:
                    raise ValueError(
                        "target_file is required for create operation."
                    )

                target_path = Path(
                    request.target_file
                ).resolve()

                if target_path.exists():
                    raise FileExistsError(
                        f"Target file already exists: {target_path}"
                    )

                original_code = ""

                backup_path = None

            else:
                target_path = source_path

                original_code = source_content

                backup_path = None

                if request.create_backup:
                    backup_path = backup_file(
                        str(target_path),
                        project_path=request.project_path,
                    )

            # 1. Candidate Generation & Sampling
            raw_candidates = []
            if request.metadata and isinstance(request.metadata.get("candidates"), list):
                raw_candidates = [str(c) for c in request.metadata["candidates"]]
            elif request.candidates_count > 1:
                try:
                    raw_candidates = generate_candidate_patches(
                        request=request,
                        count=request.candidates_count,
                    )
                except Exception:
                    raw_candidates = [modify_code(request=request)]
            else:
                raw_candidates = [modify_code(request=request)]

            # 2. Candidate Evaluation & Best-of-N AST Ranking
            best_candidate, evaluated_candidates = rank_candidates(
                candidates=raw_candidates,
                request=request,
                original_code=original_code,
            )

            modified_code = best_candidate.content
            modified_hash = compute_sha256(modified_code) if modified_code else None
            validation_message = best_candidate.validation_message or "Validation Skipped"

            diff = ""
            if request.generate_diff:
                diff = generate_diff(
                    original=original_code,
                    modified=modified_code,
                    filename=target_path.name,
                )

            lines_added, lines_deleted = compute_diff_stats(diff) if diff else (0, 0)
            elapsed_sec = round(time.perf_counter() - t_start, 3)
            current_mem = round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)

            prompt_tok = getattr(request, "_prompt_tokens", 0) or max(1, int(len(request.instruction.split()) * 1.3))
            comp_tok = getattr(request, "_completion_tokens", 0) or max(1, int(len((modified_code or "").split()) * 1.3))

            metrics = ExecutionMetrics(
                inference_time_seconds=elapsed_sec,
                prompt_tokens=prompt_tok,
                completion_tokens=comp_tok,
                total_tokens=prompt_tok + comp_tok,
                lines_added=lines_added,
                lines_deleted=lines_deleted,
                peak_memory_mb=current_mem,
            )
            best_candidate.metrics = metrics

            if request.validate_output and not best_candidate.syntax_valid:
                return EditResponse(
                    success=False,
                    file_path=str(source_path),
                    original_code=source_content,
                    modified_code=modified_code,
                    diff="",
                    validation_message=validation_message,
                    backup_path=backup_path,
                    error=validation_message,
                    operation=request.operation,
                    output_file=(
                        str(target_path)
                        if request.operation == "create"
                        else None
                    ),
                    source_hash=source_hash,
                    modified_hash=modified_hash,
                    scope=request.scope,
                    metrics=metrics,
                    candidate_patches=evaluated_candidates,
                    selected_candidate_id=best_candidate.candidate_id,
                )

            return EditResponse(
                success=True,
                file_path=str(source_path),
                original_code=source_content,
                modified_code=modified_code,
                diff=diff,
                validation_message=validation_message,
                backup_path=backup_path,
                error=None,
                operation=request.operation,
                output_file=(
                    str(target_path)
                    if request.operation == "create"
                    else None
                ),
                source_hash=source_hash,
                modified_hash=modified_hash,
                scope=request.scope,
                metrics=metrics,
                candidate_patches=evaluated_candidates,
                selected_candidate_id=best_candidate.candidate_id,
            )

        except Exception as exc:
            elapsed_sec = round(time.perf_counter() - t_start, 3)
            current_mem = round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)
            metrics = ExecutionMetrics(
                inference_time_seconds=elapsed_sec,
                peak_memory_mb=current_mem,
            )
            return EditResponse(
                success=False,
                file_path=request.file_path,
                original_code="",
                modified_code="",
                diff="",
                validation_message="Preparation Failed",
                backup_path=None,
                error=f"{type(exc).__name__}: {exc}",
                operation=request.operation,
                output_file=request.target_file,
                source_hash=getattr(request, "source_hash", None),
                modified_hash=None,
                scope=getattr(request, "scope", None),
                metrics=metrics,
            )

    def apply_edit(
        self,
        response: EditResponse,
        file_path: str,
        project_path: str = ".",
        force: bool = False,
    ) -> bool:
        """
        Apply an approved edit or create a new file with optimistic concurrency validation.
        """

        if not response.success:
            return False

        target = Path(file_path).resolve()

        if response.operation == "create":
            create_file(
                str(target),
                response.modified_code,
                project_path=project_path,
            )
            return True

        if target != Path(response.file_path).resolve():
            raise ValueError(
                "An edit may only be applied to the file it previewed."
            )

        # Optimistic concurrency check: verify target file was not modified on disk since preview
        if not force and response.source_hash:
            current_hash = get_file_sha256(str(target), project_path=project_path)
            if current_hash != response.source_hash:
                raise ValueError(
                    f"Concurrency conflict: Target file '{target.name}' was modified on disk after preview was generated. "
                    f"Expected hash {response.source_hash[:8]}, but found {current_hash[:8]}."
                )

        write_file(
            str(target),
            response.modified_code,
            project_path=project_path,
        )

        return True

    def rollback(
        self,
        file_path: str,
        project_path: str = ".",
    ) -> bool:
        """
        Restore the previous backup.
        """
        try:
            restore_backup(
                file_path,
                project_path=project_path,
            )
            return True
        except (FileNotFoundError, OSError, ValueError):
            return False

    def create_file(
        self,
        response: EditResponse,
        project_path: str = ".",
    ) -> bool:
        """
        Create a new file from generated code.
        """

        if not response.success:
            return False

        if not response.output_file:
            raise ValueError(
                "Output file is required for create operation."
            )

        create_file(
            response.output_file,
            response.modified_code,
            project_path=project_path,
        )

        return True
