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

from app.tools import requirements_generator
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
)
from app.editing.validator import validate_python
from app.editing.diff_generator import generate_diff
from app.editing.code_modifier import modify_code


class EditingService:
    """
    Orchestrates EdgeMind's editing subsystem.
    """

    def prepare_edit(
        self,
        request: EditRequest
    ) -> EditResponse:
        """
        Generate an edit preview.

        No files are modified.
        """

        try:
            # ----------------------------
            # Read Original Source
            # ----------------------------
            original_code = read_file(
                request.file_path
            )
            # Store source inside request
            request.source_code = original_code

            # ----------------------------
            # Backup
            # ----------------------------
            backup_path = None
            if request.create_backup:

                backup_path = backup_file(
                    request.file_path
                )

            # ----------------------------
            # Generate Modified Code
            # ----------------------------
            modified_code = modify_code(
                request=request,
            )
            
            # ----------------------------
            # Validation
            # ----------------------------
            validation_message = "Validation Skipped"
            if request.validate_output:
                success, validation_message = validate_python(
                    modified_code
                )
                if not success:
                    return EditResponse(
                        success=False,
                        original_code=original_code,
                        modified_code=modified_code,
                        diff="",
                        validation_message=validation_message,
                        backup_path=backup_path,
                        error=validation_message,
                    )

            # ----------------------------
            # Diff
            # ----------------------------
            diff = ""
            if request.generate_diff:
                diff = generate_diff(
                    original=original_code,
                    modified=modified_code,
                    filename=Path(
                        request.file_path
                    ).name,
                )

            return EditResponse(
                success=True,
                original_code=original_code,
                modified_code=modified_code,
                diff=diff,
                validation_message=validation_message,
                backup_path=backup_path,
                error=None,
            )

        except Exception as e:
            return EditResponse(
                success=False,
                original_code="",
                modified_code="",
                diff="",
                validation_message="Preparation Failed",
                backup_path=None,
                error=str(e),
            )

    def apply_edit(
        self,
        response: EditResponse,
        file_path: str,
    ) -> bool:
        """
        Apply an approved edit.
        """
        if not response.success:
            return False
        write_file(
            file_path,
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
        except Exception:
            return False