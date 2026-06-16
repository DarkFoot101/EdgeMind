import typer

from app.tools.project_analyzer import analyze_project

app = typer.Typer()


@app.command()
def analyze(project_path: str = "."):

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


if __name__ == "__main__":
    app()