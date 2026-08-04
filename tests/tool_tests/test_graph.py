from app.graph.workflow import workflow


def run(query, file_path=""):

    print("=" * 70)
    print(query)
    print("=" * 70)

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

    print("\nPlan:")
    print(result["plan"])

    print("\nSelected Model:")
    print(result["selected_model"])

    print("\nExecution Success:")
    print(result["execution_success"])

    print("\nResult:\n")
    print(result["result"])


def main():

    run("Analyze this project")

    run(
        "Explain this code",
        "app/models/model_router.py"
    )


if __name__ == "__main__":
    main()