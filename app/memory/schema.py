"""
SQLite schema definition and migration for EdgeMind V2.1 project memory.
"""

from contextlib import closing
from app.memory.database import get_connection


def initialize_database() -> None:
    """Create or migrate the task_history project-memory table."""
    with closing(get_connection()) as connection, connection:
        connection.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            project_path TEXT,
            user_query TEXT,
            task TEXT,
            intent TEXT,
            file_path TEXT,
            source_file TEXT,
            target_file TEXT,
            operation TEXT,
            selected_model TEXT,
            plan_json TEXT,
            result TEXT,
            diff_text TEXT,
            success BOOLEAN
        );
        """)

        # Safely migrate existing tables if columns are missing
        cursor = connection.cursor()
        cursor.execute("PRAGMA table_info(task_history)")
        columns = {row[1] for row in cursor.fetchall()}

        new_cols = [
            ("intent", "TEXT"),
            ("source_file", "TEXT"),
            ("target_file", "TEXT"),
            ("operation", "TEXT"),
            ("plan_json", "TEXT"),
            ("diff_text", "TEXT"),
        ]

        for col_name, col_type in new_cols:
            if col_name not in columns:
                try:
                    connection.execute(f"ALTER TABLE task_history ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass
