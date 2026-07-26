from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.tools.docker_compose_generator import save_docker_compose


class ComposeGeneratorTests(unittest.TestCase):
    def test_saves_model_output(self) -> None:
        with TemporaryDirectory() as directory:
            project = Path(directory)
            with patch(
                "app.tools.docker_compose_generator.generate_docker_compose",
                return_value="services:\n  edgemind:\n    build: .\n",
            ):
                result = save_docker_compose(str(project))

            self.assertEqual(result, "docker-compose.yml generated successfully.")
            self.assertTrue((project / "docker-compose.yml").is_file())

    def test_rejects_an_empty_model_output(self) -> None:
        with patch("app.tools.docker_compose_generator.generate_docker_compose", return_value=""):
            with self.assertRaises(ValueError):
                save_docker_compose(".")
