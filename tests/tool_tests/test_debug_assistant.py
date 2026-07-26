import unittest
from unittest.mock import patch

from app.tools.debug_assistant import debug_error


class DebugAssistantTests(unittest.TestCase):
    def test_uses_explicit_model_when_provided(self) -> None:
        with patch(
            "app.tools.debug_assistant.generate_response", return_value="Fix the import"
        ) as generate:
            result = debug_error("ModuleNotFoundError", selected_model="test-model")

        self.assertEqual(result, "Fix the import")
        self.assertEqual(generate.call_args.kwargs["model"], "test-model")
