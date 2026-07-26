"""SQLite schema for project execution memory."""

from contextlib import closing

from app.memory.database import get_connection


def initialize_database() -> None:
    """Create the project-memory table when it does not exist."""

    with closing(get_connection()) as connection, connection:
        connection.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            project_path TEXT,
            user_query TEXT,
            task TEXT,
            file_path TEXT,
            selected_model TEXT,
            result TEXT,
            success BOOLEAN
        );
        """)
