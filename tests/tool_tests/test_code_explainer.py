from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.tools.code_explainer import explain_code


class CodeExplainerTests(unittest.TestCase):
    def test_passes_source_to_selected_model(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "example.py"
            source.write_text("value = 1\n", encoding="utf-8")
            with patch(
                "app.tools.code_explainer.generate_response", return_value="An explanation"
            ) as generate:
                result = explain_code(str(source), selected_model="test-model")

        self.assertEqual(result, "An explanation")
        self.assertEqual(generate.call_args.kwargs["model"], "test-model")
