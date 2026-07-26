import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

list_of_files = [
    "app/config.py",
    f"app/agents/coding_agent.py",
    f"app/models/model_router.py",
    f"app/models/ollama_client.py",
    f"app/resources/system_monitor.py",
    f"app/tools/file_reader.py",
    f"app/tools/code_scanner.py",
    f"app/tools/deployment_generator.py",
    f"app/memory/memory_manager.py",
    f"app/graph/workflow.py",
    f"app/cli/main.py",
    "tests/",
    "docs/",
    "tests/",
    "data/",
    "README.md",
    ".env"
]

def main() -> None:
    """Create the initial EdgeMind project structure when run directly."""

    logging.basicConfig(level=logging.INFO)
    for filepath in list_of_files:
        filepath = Path(filepath)
        filedir, filename = os.path.split(filepath)

        if filedir:
            os.makedirs(filedir, exist_ok=True)
            logger.info("Creating directory: %s for file %s", filedir, filename)

        if not filepath.exists() or filepath.stat().st_size == 0:
            filepath.touch(exist_ok=True)
            logger.info("Creating empty file: %s", filepath)
        else:
            logger.info("%s already exists", filename)


if __name__ == "__main__":
    main()
