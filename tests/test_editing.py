from pathlib import Path

from app.editing.editing_service import EditingService
from app.editing.models import EditRequest


def main():

    print("=" * 60)
    print("EDITING PIPELINE TEST")
    print("=" * 60)

    sample_file = "tests/sample_code.py"

    request = EditRequest(
        file_path=sample_file,
        instruction="Add proper Python type hints and improve the comments.",
        model="qwen2.5-coder:3b"
    )

    service = EditingService()

    response = service.prepare_edit(request)

    print("\nSuccess:")
    print(response.success)

    print("\nMessage:")
    print(response.message)

    print("\nGenerated Diff:\n")
    print(response.diff)

    if response.error:
        print("\nError:")
        print(response.error)


if __name__ == "__main__":
    main()