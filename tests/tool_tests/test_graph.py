import unittest

from app.graph.evaluator import evaluate_execution
from app.graph.planner import create_plan


class GraphUnitTests(unittest.TestCase):
    def test_planner_builds_a_deployment_plan(self) -> None:
        self.assertEqual(create_plan("Generate Docker Compose"), ["deployment"])

    def test_evaluator_accepts_successful_error_related_language(self) -> None:
        self.assertTrue(evaluate_execution("No errors were found."))
        self.assertFalse(evaluate_execution("Error: source file is missing"))
