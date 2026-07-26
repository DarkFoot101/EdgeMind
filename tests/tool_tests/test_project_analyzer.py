import unittest
from unittest.mock import patch

from app.tools.project_analyzer import analyze_project


class ProjectAnalyzerTests(unittest.TestCase):
    def test_returns_complete_report(self) -> None:
        project_info = {
            "project_name": "demo",
            "language_detected": "Python",
            "python_files": 1,
            "total_files": 1,
            "requirements_exists": True,
            "dockerfile_exists": False,
            "readme_exists": True,
        }
        with patch("app.tools.project_analyzer.scan_project", return_value=project_info), patch(
            "app.tools.project_analyzer.get_system_resources",
            return_value={"cpu_percent": 1.0, "ram_available_gb": 8.0},
        ), patch(
            "app.tools.project_analyzer.generate_response", return_value="assessment"
        ) as generate:
            report = analyze_project(".", selected_model="test-model")

        self.assertEqual(report["analysis"], "assessment")
        self.assertEqual(report["selected_model"], "test-model")
        self.assertEqual(generate.call_args.kwargs["model"], "test-model")
