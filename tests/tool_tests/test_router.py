from app.models.model_router import select_model


def main():

    print("=" * 60)
    print("MODEL ROUTER TEST")
    print("=" * 60)

    tasks = [
        "analyze",
        "debug",
        "deployment",
        "explain",
    ]

    for task in tasks:

        model = select_model(task)

        print(f"{task:15} -> {model}")

    print("\nModel routing test completed.")


if __name__ == "__main__":
    main()