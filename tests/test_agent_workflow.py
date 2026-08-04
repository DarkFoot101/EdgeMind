"""
EdgeMind End-to-End Workflow Test

Simulates a user interacting with EdgeMind
through multiple software engineering tasks.
"""

from app.graph.workflow import workflow


def execute(query: str, file_path: str = ""):

    print("\n")
    print("=" * 80)
    print(f"USER REQUEST: {query}")
    print("=" * 80)

    state = {
        "user_query": query,
        "project_path": ".",
        "file_path": file_path,

        "plan": [],
        "current_step": 0,
        "current_task": "",

        "selected_model": "",

        "result": "",
        "execution_success": False,

        "retry_count": 0,
        "max_retry": 2,

        "memory_context": "",

        "edit_response": None,
    }

    result = workflow.invoke(state)

    print("\nExecution Plan")
    print("-" * 50)
    print(result["plan"])

    print("\nSelected Model")
    print("-" * 50)
    print(result["selected_model"])

    print("\nExecution Success")
    print("-" * 50)
    print(result["execution_success"])

    print("\nResult")
    print("-" * 50)
    print(result["result"])


def main():

    print("\n")
    print("=" * 80)
    print("EDGE MIND END-TO-END SYSTEM TEST")
    print("=" * 80)

    # --------------------------------------------------
    # Project Analysis
    # --------------------------------------------------

    execute(
        "Analyze this project"
    )

    # --------------------------------------------------
    # Code Explanation
    # --------------------------------------------------

    execute(
        "Explain this file",
        "app/models/model_router.py"
    )

    # --------------------------------------------------
    # Debugging
    # --------------------------------------------------

    execute(
        "Debug this error",
        "tests/sample_error.txt"
    )

    # --------------------------------------------------
    # Dockerfile
    # --------------------------------------------------

    execute(
        "Generate Dockerfile"
    )

    # --------------------------------------------------
    # Requirements
    # --------------------------------------------------

    execute(
        "Generate requirements"
    )

    # --------------------------------------------------
    # Docker Compose
    # --------------------------------------------------

    execute(
        "Generate docker compose"
    )

    # --------------------------------------------------
    # Editing Pipeline
    # --------------------------------------------------

    execute(
        "Modify this file by adding type hints",
        "tests/sample_code.py"
    )

    print("\n")
    print("=" * 80)
    print("ALL EDGE MIND TESTS COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()