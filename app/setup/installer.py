"""
EdgeMind V2.1 Setup Wizard
"""

import shutil
import time
import ollama

from app.models.model_manager import ModelManager
from app.setup.checks import (
    check_ram,
    check_disk,
    check_sqlite,
    check_ollama,
    start_ollama,
    missing_models,
)


def run_setup():
    print("\n" + "=" * 60)
    print("EdgeMind V2.1 Setup Wizard")
    print("=" * 60 + "\n")

    print("Checking Python environment...")
    print("✓ Python detected")

    print("Checking RAM...")
    print("✓ Available RAM >= 4GB" if check_ram() else "✗ Low RAM (requires >= 4GB)")

    print("Checking Disk...")
    print("✓ Free Disk Space >= 5GB" if check_disk() else "✗ Low Disk Space (requires >= 5GB)")

    print("Checking SQLite...")
    print("✓ SQLite operational" if check_sqlite() else "✗ SQLite Error")

    print("\nChecking Ollama...")
    if not shutil.which("ollama"):
        print("✗ Ollama binary not found. Please install Ollama from https://ollama.com")
        return

    print("✓ Ollama detected")

    if check_ollama():
        print("✓ Ollama running")
    else:
        print("✗ Ollama not running")
        answer = input("Start Ollama now? (Y/N): ").strip().lower()
        if answer in {"y", "yes"}:
            if start_ollama():
                print("Starting Ollama", end="", flush=True)
                for _ in range(10):
                    time.sleep(1)
                    print(".", end="", flush=True)
                    if check_ollama():
                        print(" ✓ Running!")
                        break
                else:
                    print("\nOllama taking long to start. Please run 'ollama serve' in terminal.")
                    return
            else:
                print("Unable to start Ollama automatically. Run: ollama serve")
                return
        else:
            return

    print()
    installed = ModelManager.list_installed_models()
    if installed:
        print("Detected local Ollama models:")
        for m in installed:
            print(f"  ✓ {m}")
        rec_model = ModelManager.select_best_model("edit")
        print(f"\nSelected active coding model: {rec_model}")
        print("No additional model download required.")
    else:
        rec_model, size_est = ModelManager.recommend_default_model()
        print("No compatible coding model found.")
        print("Recommended model:")
        print(f"  {rec_model}")
        print(f"Model size: {size_est}")

        answer = input("\nDownload model? [Y/n]: ").strip().lower()
        if answer in {"", "y", "yes"}:
            print(f"Downloading {rec_model}...")
            try:
                ollama.pull(rec_model)
                print(f"✓ Successfully installed {rec_model}")
            except Exception as exc:
                print(f"✗ Failed to download {rec_model}: {exc}")
                return
        else:
            print("Model setup cancelled.")
            return

    print("\n" + "=" * 60)
    print("Setup Complete! You can now start EdgeMind:")
    print("  edgemind")
    print("=" * 60 + "\n")