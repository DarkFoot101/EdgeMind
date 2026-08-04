from app.memory.memory_manager import (
    save_execution,
    search_memory,
)
from datetime import datetime

def main():

    print("=" * 60)
    print("MEMORY TEST")
    print("=" * 60)

    sample_state = {
        "user_query": f"Analyze project at {datetime.now()}",
        "project_path": ".",
        "current_task": "analyze",
        "result": "Project analyzed successfully.",
        "execution_success": True,
    }

    print("\nSaving execution...")

    save_execution(sample_state)

    print("Saved successfully.\n")

    print("Retrieving memory...\n")

    rows = search_memory(".")

    for index, row in enumerate(rows, start=1):

        print(f"Memory #{index}")

        print("Query :", row[0])

        print("Task  :", row[1])

        print("Result:", row[2])

        print("Success:", bool(row[3]))

        print("-" * 40)

    print("\nMemory test completed.")


if __name__ == "__main__":
    main()