import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.editing.editing_service import EditingService
from app.editing.models import EditRequest
from app.editing.validator import validate_python


class EditingTests(unittest.TestCase):
    def test_validator_rejects_invalid_python(self) -> None:
        self.assertEqual(validate_python("value = 1"), (True, "Validation Passed"))
        self.assertFalse(validate_python("def invalid(")[0])

    def test_preview_keeps_original_until_approval(self) -> None:
        with TemporaryDirectory() as directory:
            project = Path(directory).resolve()
            target = project / "module.py"
            target.write_text("value = 1\n", encoding="utf-8")
            previous_directory = Path.cwd()
            try:
                os.chdir(project)
                request = EditRequest("module.py", "Set value to two")
                with patch(
                    "app.editing.editing_service.modify_code", return_value="value = 2\n"
                ):
                    response = EditingService().prepare_edit(request)
                self.assertTrue(response.success)
                self.assertEqual(target.read_text(encoding="utf-8"), "value = 1\n")
                self.assertTrue(Path(response.backup_path).exists())
                self.assertTrue(EditingService().apply_edit(response, "module.py"))
            finally:
                os.chdir(previous_directory)

            self.assertEqual(target.read_text(encoding="utf-8"), "value = 2\n")
