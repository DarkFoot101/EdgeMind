"""
EdgeMind Setup Wizard
"""

import ollama

from app.setup.checks import (
    check_ram,
    check_disk,
    check_sqlite,
    check_ollama,
    start_ollama,
    missing_models,
)


def run_setup():

    print()

    print("=" * 60)

    print("EdgeMind First Time Setup")

    print("=" * 60)

    print()

    print("Checking RAM...")

    print("✓ OK" if check_ram() else "✗ Low RAM")

    print("Checking Disk...")

    print("✓ OK" if check_disk() else "✗ Low Disk Space")

    print("Checking SQLite...")

    print("✓ OK" if check_sqlite() else "✗ SQLite Error")

    print()

    print("Checking Ollama...")

    if check_ollama():

        print("✓ Running")

    else:

        print("✗ Not Running")

        answer = input(

            "Start Ollama now? (Y/N): "

        ).lower()

        if answer == "y":

            if start_ollama():

                print("✓ Ollama Started")

            else:

                print("Could not start Ollama.")

                print("Run: ollama serve")

                return

        else:

            return

    print()

    missing = missing_models()

    if not missing:

        print("✓ All models installed")

    else:

        print("Missing Models:\n")

        for model in missing:

            print(model)

        print()

        answer = input(

            "Download them now? (Y/N): "

        ).lower()

        if answer == "y":

            for model in missing:

                print(f"Downloading {model}...")

                ollama.pull(model)

                print("✓ Done")

    print()

    print("=" * 60)

    print("Setup Complete!")

    print()

    print("Run")

    print()

    print("edgemind")

    print()

    print("=" * 60)