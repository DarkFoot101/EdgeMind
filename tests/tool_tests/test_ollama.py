import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

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

    def test_detailed_telemetry_returned(self) -> None:
        from app.models.ollama_client import generate_response_detailed
        with patch(
            "app.models.ollama_client.ollama.chat",
            return_value={
                "message": {"content": "detailed response"},
                "prompt_eval_count": 42,
                "eval_count": 18,
            },
        ):
            meta = generate_response_detailed("test prompt", "test-model")

        self.assertEqual(meta.content, "detailed response")
        self.assertEqual(meta.prompt_tokens, 42)
        self.assertEqual(meta.completion_tokens, 18)
        self.assertEqual(meta.total_tokens, 60)
        self.assertGreaterEqual(meta.inference_time_seconds, 0.0)

