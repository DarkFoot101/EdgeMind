# this is where the memory input and the reference will take place. 
# this file creates the sql database 

import sqlite3
from pathlib import Path
DB_DIR = Path.home() / ".edgemind"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "edgemind.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_project_path(project_path="."):
    return str(Path(project_path).resolve())