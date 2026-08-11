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

from pathlib import Path
from app.editing.models import (
    EditRequest,
    EditResponse,
)
from app.editing.file_manager import (
    read_file,
    backup_file,
    write_file,
    restore_backup,
    create_file,
)
from app.editing.validator import validate_code
from app.editing.diff_generator import generate_diff
from app.editing.code_modifier import modify_code


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
        """

        try:
            source_path = Path(
                request.file_path
            ).resolve()

            if not source_path.exists():
                raise FileNotFoundError(
                    f"Source file not found: {source_path}"
                )

            source_content = read_file(
                str(source_path)
            )

            request.source_code = source_content

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
                        str(target_path)
                    )

            modified_code = modify_code(
                request=request,
            )

            validation_message = "Validation Skipped"

            if request.validate_output:
                success, validation_message = validate_code(
                    modified_code,
                    request.target_language,
                )

                if not success:
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
                    )

            diff = ""

            if request.generate_diff:
                diff = generate_diff(
                    original=original_code,
                    modified=modified_code,
                    filename=target_path.name,
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
            )

        except Exception as exc:
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
            )

    def apply_edit(
        self,
        response: EditResponse,
        file_path: str,
    ) -> bool:
        """
        Apply an approved edit or create a new file.
        """

        if not response.success:
            return False

        target = Path(file_path).resolve()

        if response.operation == "create":
            create_file(
                str(target),
                response.modified_code,
            )
            return True

        if target != Path(response.file_path).resolve():
            raise ValueError(
                "An edit may only be applied to the file it previewed."
            )

        write_file(
            str(target),
            response.modified_code,
        )

        return True

    def rollback(
        self,
        file_path: str,
    ) -> bool:
        """
        Restore the previous backup.
        """
        try:
            restore_backup(
                file_path
            )
            return True
        except (FileNotFoundError, OSError, ValueError):
            return False

    def create_file(
        self,
        response: EditResponse,
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
        )

        return True
