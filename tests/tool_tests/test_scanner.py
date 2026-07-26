from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.tools.code_scanner import scan_project


class ScannerTests(unittest.TestCase):
    def test_scans_python_files_and_ignores_virtual_environments(self) -> None:
        with TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "app.py").write_text("pass\n", encoding="utf-8")
            (project / "venv").mkdir()
            (project / "venv" / "ignored.py").write_text("pass\n", encoding="utf-8")

            result = scan_project(str(project))

        self.assertEqual(result["python_files"], 1)
        self.assertEqual(result["total_files"], 1)
