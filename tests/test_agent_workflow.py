from app.graph.workflow import workflow


def run_test(title, state):

    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    result = workflow.invoke(state)

    print("\nCurrent Plan:")
    print(result.get("plan"))

    print("\nExecuted Task:")
    print(result.get("current_task"))

    print("\nSelected Model:")
    print(result.get("selected_model"))

    print("\nExecution Success:")
    print(result.get("execution_success"))

    print("\nResult:\n")
    print(result.get("result"))

    print()


# ----------------------------------------

run_test(
    "PROJECT ANALYSIS",
    {
        "user_query": "Analyze this project",
        "file_path": ""
    }
)

# ----------------------------------------

run_test(
    "CODE EXPLANATION",
    {
        "user_query": "Explain this file",
        "file_path": "tests/sample_code.py"
    }
)

# ----------------------------------------

run_test(
    "DEBUGGING",
    {
        "user_query": "Debug this error",
        "file_path": "tests/sample_error.txt"
    }
)

# ----------------------------------------

run_test(
    "DOCKERFILE",
    {
        "user_query": "Generate Dockerfile",
        "file_path": ""
    }
)

# ----------------------------------------

run_test(
    "REQUIREMENTS",
    {
        "user_query": "Generate requirements",
        "file_path": ""
    }
)

# ----------------------------------------

run_test(
    "DOCKER COMPOSE",
    {
        "user_query": "Generate compose",
        "file_path": ""
    }
)

print("\nALL TESTS FINISHED\n")