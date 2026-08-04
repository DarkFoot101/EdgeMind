from app.graph.workflow import workflow


def execute(query, file_path=""):

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

    print("\n" + "=" * 80)
    print(query)
    print("=" * 80)

    print("\nTask Plan:")
    print(result["plan"])

    print("\nResult:\n")
    print(result["result"])


def main():

    execute(
        "Analyze this project"
    )

    execute(
        "Explain this file",
        "app/models/model_router.py"
    )

    execute(
        "Debug this error",
        "tests/sample_error.txt"
    )

    execute(
        "Generate Dockerfile"
    )

    execute(
        "Generate requirements"
    )

    execute(
        "Generate docker compose"
    )

    execute(
        "Modify this code by adding type hints",
        "tests/sample_code.py"
    )


if __name__ == "__main__":
    main()