from pathlib import Path
from app.tools.code_scanner import scan_project
from app.models.model_router import select_model
from app.models.ollama_client import generate_response


def clean_llm_output(text: str) -> str:

    text = text.replace("```yaml", "")
    text = text.replace("```yml", "")
    text = text.replace("```", "")

    return text.strip()


def generate_docker_compose(
    project_path: str = ".",
    selected_model: str | None = None,
) -> str:

    project_info = scan_project(project_path)

    model = selected_model or select_model("deployment")

    prompt = f"""
        You are a Senior DevOps Engineer.

        Generate a docker-compose.yml file.

        Project Information:

        {project_info}

        Rules:
        1. Assume Dockerfile already exists.
        2. Create one service called edgemind.
        3. Build from current directory.
        4. Do not configure a restart policy; EdgeMind is a command-line app.
        5. Return ONLY YAML.
        6. No explanation.

        Output only docker-compose.yml content.
        
    """

    response = generate_response(
        prompt=prompt,
        model=model
    )

    return clean_llm_output(response)


def save_docker_compose(
    project_path: str = ".",
    selected_model: str | None = None,
) -> str:
    """Generate and save a non-empty Compose file for a project."""

    compose_content = generate_docker_compose(
        project_path,
        selected_model,
    )
    if not compose_content.strip():
        raise ValueError("Model returned an empty docker-compose.yml file.")

    output_path = Path(project_path) / "docker-compose.yml"
    output_path.write_text(compose_content, encoding="utf-8")

    return "docker-compose.yml generated successfully."
