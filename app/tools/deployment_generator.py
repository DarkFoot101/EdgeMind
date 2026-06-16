from app.tools.code_scanner import scan_project
from app.models.model_router import select_model
from app.models.ollama_client import generate_response


def generate_dockerfile(project_path="."):

    project_info = scan_project(project_path)

    model = select_model("deployment")

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

def save_dockerfile(project_path="."):

    dockerfile_content = generate_dockerfile(project_path)

    with open("Dockerfile", "w") as f:
        f.write(dockerfile_content)

    return "Dockerfile generated successfully."

def clean_llm_output(text):

    text = text.replace("```dockerfile", "")
    text = text.replace("```", "")

    return text.strip()