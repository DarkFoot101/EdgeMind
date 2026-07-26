from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.tools.requirements_generator import extract_imports, save_requirements


class RequirementsGeneratorTests(unittest.TestCase):
    def test_excludes_stdlib_and_local_packages(self) -> None:
        with TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "local_package").mkdir()
            (project / "local_package" / "__init__.py").write_text("", encoding="utf-8")
            (project / "main.py").write_text(
                "import pathlib\nimport ollama\nfrom local_package import value\n",
                encoding="utf-8",
            )

            self.assertEqual(extract_imports(str(project)), ["ollama"])
            self.assertEqual(save_requirements(str(project)), ["ollama"])
            self.assertEqual(
                (project / "requirements.txt").read_text(encoding="utf-8"),
                "ollama\n",
            )
