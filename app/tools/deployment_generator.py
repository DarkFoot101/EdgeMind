from pathlib import Path
from app.tools.code_scanner import scan_project
from app.models.model_router import select_model
from app.models.ollama_client import generate_response


def generate_dockerfile(
    project_path: str = ".",
    selected_model: str | None = None,
) -> str:

    project_info = scan_project(project_path)

    model = selected_model or select_model("deployment")

    prompt = f"""
        You are a Senior DevOps Engineer.

        Analyze the following project information and generate a Dockerfile.

        Project Information:
        {project_info}

        Rules:
        1. Assume this is a Python project.
        2. Use python:3.11-slim.
        3. Copy requirements.txt.
        4. Install dependencies.
        5. Copy project files.
        6. Return ONLY the Dockerfile.
        7. Do not explain anything.

        Output only Dockerfile content.
    """

    dockerfile_content = generate_response(
        prompt=prompt,
        model=model
    )

    return clean_llm_output(dockerfile_content)

def save_dockerfile(
    project_path: str = ".",
    selected_model: str | None = None,
) -> str:
    """Generate and save a non-empty Dockerfile for a project."""

    dockerfile_content = generate_dockerfile(project_path, selected_model)
    if not dockerfile_content.strip():
        raise ValueError("Model returned an empty Dockerfile.")

    output_path = Path(project_path) / "Dockerfile"
    output_path.write_text(dockerfile_content, encoding="utf-8")

    return "Dockerfile generated successfully."

def clean_llm_output(text: str) -> str:

    text = text.replace("```dockerfile", "")
    text = text.replace("```", "")

    return text.strip()
