import unittest
from unittest.mock import patch

from app.models.ollama_client import generate_response


class OllamaClientTests(unittest.TestCase):
    def test_sends_a_system_prompt_when_supplied(self) -> None:
        with patch(
            "app.models.ollama_client.ollama.chat",
            return_value={"message": {"content": "response"}},
        ) as chat:
            result = generate_response("request", "test-model", "system")

        self.assertEqual(result, "response")
        self.assertEqual(chat.call_args.kwargs["model"], "test-model")
        self.assertEqual(chat.call_args.kwargs["messages"][0]["role"], "system")
