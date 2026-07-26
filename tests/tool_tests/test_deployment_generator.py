from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.tools.deployment_generator import save_dockerfile


class DockerfileGeneratorTests(unittest.TestCase):
    def test_saves_cleaned_model_output(self) -> None:
        with TemporaryDirectory() as directory:
            project = Path(directory)
            with patch(
                "app.tools.deployment_generator.generate_dockerfile",
                return_value="FROM python:3.11-slim\n",
            ):
                result = save_dockerfile(str(project))

            self.assertEqual(result, "Dockerfile generated successfully.")
            self.assertEqual(
                (project / "Dockerfile").read_text(encoding="utf-8"),
                "FROM python:3.11-slim\n",
            )

    def test_rejects_an_empty_model_output(self) -> None:
        with patch("app.tools.deployment_generator.generate_dockerfile", return_value=""):
            with self.assertRaises(ValueError):
                save_dockerfile(".")
