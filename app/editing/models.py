"""Data models used by the editing subsystem in EdgeMind V2.1."""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from app.editing.scope import EditScope, EditScopeType


class OperationType(str, Enum):
    """Supported file editing and transformation operations."""

    MODIFY = "modify"
    CREATE = "create"
    PATCH = "patch"

    @classmethod
    def from_str(cls, value: str) -> "OperationType":
        if isinstance(value, cls):
            return value
        val_clean = str(value or "").strip().lower()
        for member in cls:
            if member.value == val_clean:
                return member
        # Fallback to MODIFY if unknown
        return cls.MODIFY


@dataclass
class EditRequest:
    """
    Represent a request to prepare a source-code edit or file creation.
    Provides canonical path resolution, operation validation, and metadata management.
    """

    file_path: str
    instruction: str
    source_code: str = ""
    model: str = ""  # If left empty, dynamically resolved via router or fallback
    source_language: str = "python"
    target_language: str = "python"
    output_file: Optional[str] = None
    preserve_formatting: bool = True
    create_backup: bool = True
    validate_output: bool = True
    generate_diff: bool = True
    metadata: Optional[Dict[str, Any]] = None
    source_file: Optional[str] = None
    target_file: Optional[str] = None
    operation: OperationType | str = OperationType.MODIFY
    analysis_result: Optional[str] = None  # findings from prior analyze/search steps
    project_path: str = "."
    source_hash: Optional[str] = None  # SHA-256 pre-edit integrity hash
    scope: Optional[EditScope] = None
    scope_type: Optional[EditScopeType | str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    target_symbol: Optional[str] = None
    search_block: Optional[str] = None
    replace_block: Optional[str] = None
    candidates_count: int = 1

    def __post_init__(self):
        # 1. Normalize OperationType
        if not isinstance(self.operation, OperationType):
            self.operation = OperationType.from_str(str(self.operation))

        # 2. Scope initialization & synchronization
        if self.scope is None:
            st = EditScopeType.from_str(str(self.scope_type)) if self.scope_type else None
            if self.start_line is not None or self.end_line is not None:
                self.scope = EditScope(
                    scope_type=st or EditScopeType.LINE_RANGE,
                    start_line=self.start_line,
                    end_line=self.end_line,
                )
            elif self.target_symbol:
                self.scope = EditScope(
                    scope_type=st or EditScopeType.SYMBOL,
                    target_symbol=self.target_symbol,
                )
            elif self.search_block:
                self.scope = EditScope(
                    scope_type=st or EditScopeType.SEARCH_REPLACE,
                    search_block=self.search_block,
                    replace_block=self.replace_block,
                )
            else:
                self.scope = EditScope(scope_type=st or EditScopeType.FULL_FILE)
        else:
            if not isinstance(self.scope.scope_type, EditScopeType):
                self.scope.scope_type = EditScopeType.from_str(str(self.scope.scope_type))
            if self.scope_type is None:
                self.scope_type = self.scope.scope_type
            if self.start_line is None and self.scope.start_line is not None:
                self.start_line = self.scope.start_line
            if self.end_line is None and self.scope.end_line is not None:
                self.end_line = self.scope.end_line
            if self.target_symbol is None and self.scope.target_symbol is not None:
                self.target_symbol = self.scope.target_symbol
            if self.search_block is None and self.scope.search_block is not None:
                self.search_block = self.scope.search_block
            if self.replace_block is None and self.scope.replace_block is not None:
                self.replace_block = self.scope.replace_block

        # 2. Canonical path synchronization
        if not self.source_file and self.file_path:
            self.source_file = self.file_path
        elif self.source_file and not self.file_path:
            self.file_path = self.source_file

        if self.target_file and not self.output_file:
            self.output_file = self.target_file
        elif self.output_file and not self.target_file:
            self.target_file = self.output_file

        # 3. Dynamic default model resolution if omitted
        if not self.model:
            try:
                from app.models.model_router import select_model
                self.model = select_model("edit")
            except Exception:
                self.model = "qwen2.5-coder:3b"

        # 4. Normalize languages
        if self.source_language:
            self.source_language = self.source_language.strip().lower()
        if self.target_language:
            self.target_language = self.target_language.strip().lower()

        # 5. Metadata dictionary safety
        if self.metadata is None:
            self.metadata = {}

    @property
    def canonical_source_path(self) -> str:
        """Returns the definitive source file path."""
        return self.source_file or self.file_path

    @property
    def canonical_target_path(self) -> Optional[str]:
        """Returns the definitive target/destination file path."""
        return (
            self.target_file
            or self.output_file
            or (self.file_path if self.operation == OperationType.MODIFY else None)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize EditRequest to a serializable dictionary."""
        data = asdict(self)
        data["operation"] = (
            self.operation.value
            if isinstance(self.operation, OperationType)
            else str(self.operation)
        )
        if self.scope:
            data["scope"] = asdict(self.scope)
            data["scope"]["scope_type"] = (
                self.scope.scope_type.value
                if isinstance(self.scope.scope_type, EditScopeType)
                else str(self.scope.scope_type)
            )
        return data


@dataclass
class ExecutionMetrics:
    """Operational telemetry and resource metrics for code generation and editing."""

    inference_time_seconds: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    peak_memory_mb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CandidatePatch:
    """Represents a generated patch candidate with quality and syntax verification scores."""

    candidate_id: int
    content: str
    syntax_valid: bool = False
    validation_message: str = ""
    score: float = 0.0
    lines_added: int = 0
    lines_deleted: int = 0
    metrics: Optional[ExecutionMetrics] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.metrics:
            data["metrics"] = self.metrics.to_dict()
        return data


@dataclass
class EditResponse:
    """
    Represent the preview generated by an editing request.
    Maintains diff, validation status, backup path, and canonical paths.
    """

    success: bool
    file_path: str
    original_code: str
    modified_code: str
    diff: str
    validation_message: str
    backup_path: Optional[str]
    error: Optional[str]
    operation: OperationType | str = OperationType.MODIFY
    output_file: Optional[str] = None
    source_file: Optional[str] = None
    source_hash: Optional[str] = None  # SHA-256 hash of original code
    modified_hash: Optional[str] = None  # SHA-256 hash of generated code
    scope: Optional[EditScope] = None
    metrics: Optional[ExecutionMetrics] = None
    candidate_patches: Optional[List[CandidatePatch]] = None
    selected_candidate_id: Optional[int] = None

    def __post_init__(self):
        if not isinstance(self.operation, OperationType):
            self.operation = OperationType.from_str(str(self.operation))

        if not self.source_file and self.file_path:
            self.source_file = self.file_path

        if self.operation == OperationType.CREATE and not self.output_file and self.file_path:
            self.output_file = self.file_path

    @property
    def destination_path(self) -> str:
        """Returns the destination file path (output_file if created, else file_path)."""
        return self.output_file or self.file_path

    def to_dict(self) -> Dict[str, Any]:
        """Serialize EditResponse to a serializable dictionary."""
        data = asdict(self)
        data["operation"] = (
            self.operation.value
            if isinstance(self.operation, OperationType)
            else str(self.operation)
        )
        if self.scope:
            data["scope"] = asdict(self.scope)
            data["scope"]["scope_type"] = (
                self.scope.scope_type.value
                if isinstance(self.scope.scope_type, EditScopeType)
                else str(self.scope.scope_type)
            )
        if self.metrics:
            data["metrics"] = self.metrics.to_dict()
        if self.candidate_patches:
            data["candidate_patches"] = [c.to_dict() for c in self.candidate_patches]
        if self.selected_candidate_id is not None:
            data["selected_candidate_id"] = self.selected_candidate_id
        return data
