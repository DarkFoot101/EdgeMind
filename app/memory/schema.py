# The memory will contain the following set of schema
# id
# timestamp
# project_path - > this is to give better contextual understanding for the agent 
# task
# file_path
# plan
# result
# selected_model 
# success

# this creates the schema of the database
from app.memory.database import get_connection 

def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
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
    conn.connect()
    conn.close()