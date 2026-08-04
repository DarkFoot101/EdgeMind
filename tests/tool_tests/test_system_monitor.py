from app.resources.system_monitor import get_system_resources


def main():

    print("=" * 60)
    print("SYSTEM RESOURCE TEST")
    print("=" * 60)

    resources = get_system_resources()

    print("\nCPU Usage:")
    print(resources["cpu_percent"], "%")

    print("\nAvailable RAM:")
    print(resources["ram_available_gb"], "GB")

    assert isinstance(resources, dict)
    assert "cpu_percent" in resources
    assert "ram_available_gb" in resources

    print("\nSystem monitor working successfully.")


if __name__ == "__main__":
    main()