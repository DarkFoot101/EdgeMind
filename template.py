import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)

project_name="EdgeMind"

list_of_files = [
    f"app/config.py"
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

for filepath in list_of_files:
    filepath = Path(filepath)
    filedir, filename = os.path.split(filepath)

    if filedir != "":
        os.makedirs(filedir, exist_ok=True)
        logging.info(f"Creating directory:{filedir} for the file {filename}")

    
    if (not os.path.exists(filepath)) or (os.path.getsize(filepath) == 0):
        with open(filepath,'w') as f:
            pass
            logging.info(f"Creating empty file: {filepath}")


    
    else:
        logging.info(f"{filename} is already exists")