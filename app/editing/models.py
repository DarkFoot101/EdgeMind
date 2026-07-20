# we will arange the editing services such that it is neater and easier to debug\
# ensures that the modification of code by the edgemind is properly done

from dataclasses import dataclass 
from typing import Optional 

@dataclass 
class EditRequests:
    """Represents an editing request """
    file_path : str
    instruction : str 
    source_code: str = ""
    model : str = "qwen2.5-coder:3b" 
    language: str = "python"
    preserve_formatting : bool = True
    reate_backup: bool = True
    validate_output: bool = True
    generate_diff: bool = True
    metadata: Optional[dict] = None

@dataclass
class EditResponse:
    success : bool
    original_code : str 
    modified_code : str 
    diff : str 
    validation_message : str 
    backup_path : str | None 
    error : str | None 

