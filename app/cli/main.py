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


def _project_path(project_path: str) -> str:
    """Validate and normalize a project directory argument."""

    path = Path(project_path).expanduser()
    if not path.is_dir():
        raise typer.BadParameter("Project path must be an existing directory.")
    return str(path.resolve())


def _file_path(file_path: str) -> Path:
    """Validate and normalize a source or error-log file argument."""

    path = Path(file_path).expanduser()
    if not path.is_file():
        raise typer.BadParameter("File path must be an existing file.")
    return path.resolve()


@app.command()
def analyze(project_path: str = ".") -> None:
    """
    Analyze an entire project.
    """

    report = analyze_project(_project_path(project_path))

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
def explain(file_path: str) -> None:
    """
    Explain a source code file.
    """

    result = explain_code(str(_file_path(file_path)))

    print("\n========================")
    print("CODE EXPLANATION")
    print("========================\n")

    print(result)


@app.command()
def debug(error_file: str) -> None:
    """
    Analyze an error log or traceback.
    """

    error_text = _file_path(error_file).read_text(encoding="utf-8")

    result = debug_error(error_text)

    print("\n========================")
    print("DEBUG ANALYSIS")
    print("========================\n")

    print(result)


@app.command()
def generate_docker(project_path: str = ".") -> None:

    result = save_dockerfile(_project_path(project_path))
    print(result)


@app.command()
def generate_requirements(project_path: str = ".") -> None:

    packages = save_requirements(_project_path(project_path))

    print(
        f"Generated requirements.txt "
        f"with {len(packages)} packages."
    )


@app.command()
def generate_compose(project_path: str = ".") -> None:

    result = save_docker_compose(_project_path(project_path))
    print(result)


@app.command()
def interactive():
    """
    Launch EdgeMind interactive shell.
    """

    from app.cli.interactive import run

    run()

if __name__ == "__main__":
    app()
