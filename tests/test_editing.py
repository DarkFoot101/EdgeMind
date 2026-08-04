from app.editing.editing_service import EditingService
from app.editing.models import EditRequest


def main():

    print("=" * 70)
    print("EDITING PIPELINE TEST")
    print("=" * 70)

    request = EditRequest(
        file_path="tests/sample_code.py",
        instruction="Add Python type hints wherever appropriate.",
        model="qwen2.5-coder:3b",
    )

    service = EditingService()

    response = service.prepare_edit(request)

    print("\nPreparation Success:")
    print(response.success)

    print("\nValidation:")
    print(response.validation_message)

    print("\nBackup:")
    print(response.backup_path)

    print("\nDiff:\n")
    print(response.diff)

    if response.error:
        print("\nError:")
        print(response.error)
        return

    print("\nApplying edit...")

    applied = service.apply_edit(
        response,
        request.file_path,
    )

    print("Applied:", applied)

    print("\nRolling back...")

    rolled_back = service.rollback(
        request.file_path
    )

    print("Rollback:", rolled_back)

    print("\nEditing pipeline test completed successfully.")


if __name__ == "__main__":
    main()