from app.tools.code_scanner import scan_project
from app.resources.system_monitor import get_system_resources
from app.models.model_router import select_model
from app.models.ollama_client import generate_response


def analyze_project(
    project_path: str = ".",
    selected_model: str | None = None,
) -> dict:
    """Analyze project metadata with the selected local model."""

    # Step 1
    project_info = scan_project(project_path)

    # Step 2
    resources = get_system_resources()

    # Step 3
    model = selected_model or select_model("analyze")

    # Step 4
    prompt = f"""
        You are a senior software engineer.

        Analyze the following project information and provide a short project assessment.

        Project Name:
        {project_info['project_name']}

        Language:
        {project_info['language_detected']}

        Python Files:
        {project_info['python_files']}

        Total Files:
        {project_info['total_files']}

        Requirements.txt Present:
        {project_info['requirements_exists']}

        Dockerfile Present:
        {project_info['dockerfile_exists']}

        README Present:
        {project_info['readme_exists']}

        Available RAM:
        {resources['ram_available_gb']} GB

        Provide:

        1. Project Summary
        2. Missing Components
        3. Recommendations
    """

    # Step 5
    ai_analysis = generate_response(
        prompt=prompt,
        model=model
    )

    # Step 6
    report = {
        "project_info": project_info,
        "resources": resources,
        "selected_model": model,
        "analysis": ai_analysis
    }

    return report
