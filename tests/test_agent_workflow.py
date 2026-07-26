import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.graph.workflow import workflow
from app.editing.models import EditResponse
from app.memory.memory_manager import save_execution, search_memory


class WorkflowTests(unittest.TestCase):
    def test_analyze_uses_requested_project_and_saves_result(self) -> None:
        with TemporaryDirectory() as directory:
            project = Path(directory).resolve()
            previous_directory = Path.cwd()
            try:
                os.chdir(project)
                with patch(
                    "app.graph.nodes.analyze_project",
                    return_value={"analysis": "analysis complete"},
                ) as analyze:
                    result = workflow.invoke(
                        {
                            "user_query": "Analyze this project",
                            "project_path": str(project),
                            "file_path": "",
                        }
                    )
            finally:
                os.chdir(previous_directory)

        self.assertTrue(result["execution_success"])
        self.assertEqual(result["result"], "analysis complete")
        analyze.assert_called_once_with(str(project), "phi3:mini")

    def test_compose_request_does_not_generate_a_dockerfile(self) -> None:
        with TemporaryDirectory() as directory:
            project = Path(directory).resolve()
            previous_directory = Path.cwd()
            try:
                os.chdir(project)
                with patch(
                    "app.graph.nodes.save_docker_compose", return_value="compose complete"
                ) as compose, patch("app.graph.nodes.save_dockerfile") as dockerfile:
                    result = workflow.invoke(
                        {
                            "user_query": "Generate Docker Compose",
                            "project_path": str(project),
                            "file_path": "",
                        }
                    )
            finally:
                os.chdir(previous_directory)

        self.assertTrue(result["execution_success"])
        compose.assert_called_once_with(str(project), "phi3:mini")
        dockerfile.assert_not_called()

    def test_memory_context_step_is_not_persisted(self) -> None:
        with TemporaryDirectory() as directory:
            project = Path(directory).resolve()
            previous_directory = Path.cwd()
            try:
                os.chdir(project)
                save_execution(
                    {
                        "project_path": str(project),
                        "user_query": "Earlier analysis",
                        "current_task": "analyze",
                        "file_path": "",
                        "selected_model": "phi3:mini",
                        "result": "Earlier result",
                        "execution_success": True,
                    }
                )
                with patch(
                    "app.graph.nodes.analyze_project",
                    return_value={"analysis": "New result"},
                ):
                    workflow.invoke(
                        {
                            "user_query": "Analyze this project",
                            "project_path": str(project),
                            "file_path": "",
                        }
                    )
                tasks = [row[1] for row in search_memory(str(project))]
            finally:
                os.chdir(previous_directory)

        self.assertNotIn("Use memory context", tasks)
        self.assertEqual(tasks.count("analyze"), 2)

    def test_edit_prepares_a_preview_without_applying_it(self) -> None:
        response = EditResponse(
            success=True,
            file_path="module.py",
            original_code="value = 1\n",
            modified_code="value = 2\n",
            diff="--- module.py (original)\n+++ module.py (modified)\n",
            validation_message="Validation Passed",
            backup_path=".edgemind/backups/module.py",
            error=None,
        )
        with TemporaryDirectory() as directory:
            project = Path(directory).resolve()
            target = project / "module.py"
            target.write_text(response.original_code, encoding="utf-8")
            previous_directory = Path.cwd()
            try:
                os.chdir(project)
                with patch("app.graph.nodes.EditingService") as service:
                    service.return_value.prepare_edit.return_value = response
                    result = workflow.invoke(
                        {
                            "user_query": "Edit this file to set value to two",
                            "project_path": str(project),
                            "file_path": "module.py",
                        }
                    )
            finally:
                os.chdir(previous_directory)

            self.assertTrue(result["execution_success"])
            self.assertIs(result["edit_response"], response)
            self.assertIn("+++ module.py", result["result"])
            self.assertEqual(target.read_text(encoding="utf-8"), response.original_code)
