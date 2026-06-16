from app.tools.code_scanner import scan_project
from app.models.model_router import select_model
from app.models.ollama_client import generate_response


def clean_llm_output(text):

    text = text.replace("```yaml", "")
    text = text.replace("```yml", "")
    text = text.replace("```", "")

    return text.strip()


def generate_docker_compose(project_path="."):

    project_info = scan_project(project_path)

    model = select_model("deployment")

    prompt = f"""
        You are a Senior DevOps Engineer.

        Generate a docker-compose.yml file.

        Project Information:

        {project_info}

        Rules:
        1. Assume Dockerfile already exists.
        2. Create one service called edgemind.
        3. Build from current directory.
        4. Use restart unless-stopped.
        5. Return ONLY YAML.
        6. No explanation.

        Output only docker-compose.yml content.
        
    """

    response = generate_response(
        prompt=prompt,
        model=model
    )

    return clean_llm_output(response)


def save_docker_compose(project_path="."):

    compose_content = generate_docker_compose(
        project_path
    )

    with open("docker-compose.yml", "w") as f:
        f.write(compose_content)

    return "docker-compose.yml generated successfully."