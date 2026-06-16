import typer
from pathlib import Path

from app.tools.project_analyzer import analyze_project
from app.tools.code_explainer import explain_code
from app.tools.debug_assistant import debug_error
from app.tools.deployment_generator import save_dockerfile
from app.tools.requirements_generator import save_requirements
from app.tools.docker_compose_generator import save_docker_compose

app = typer.Typer(
    name="EdgeMind",
    help="Resource-Aware Agentic Coding Assistant"
)


@app.command()
def analyze(project_path: str = "."):
    """
    Analyze an entire project.
    """

    report = analyze_project(project_path)

    print("\n========================")
    print("PROJECT ANALYSIS REPORT")
    print("========================\n")

    print("Project Info:")
    print(report["project_info"])

    print("\nResources:")
    print(report["resources"])

    print("\nSelected Model:")
    print(report["selected_model"])

    print("\nAI Analysis:\n")
    print(report["analysis"])


@app.command()
def explain(file_path: str):
    """
    Explain a source code file.
    """

    result = explain_code(file_path)

    print("\n========================")
    print("CODE EXPLANATION")
    print("========================\n")

    print(result)


@app.command()
def debug(error_file: str):
    """
    Analyze an error log or traceback.
    """

    error_text = Path(error_file).read_text()

    result = debug_error(error_text)

    print("\n========================")
    print("DEBUG ANALYSIS")
    print("========================\n")

    print(result)


@app.command()
def generate_docker():

    result = save_dockerfile(".")
    print(result)


@app.command()
def generate_requirements():

    packages = save_requirements(".")

    print(
        f"Generated requirements.txt "
        f"with {len(packages)} packages."
    )


@app.command()
def generate_compose():

    result = save_docker_compose(".")
    print(result)


if __name__ == "__main__":
    app()