# this manages the memory inside the database 

from app.memory.database import get_connection, get_project_path 

# this is the code to write into the database 
def save_execution(state):
    conn = get_connection()
    cursor = conn.cursor() 

    cursor.execute(
        """
        INSERT INTO task_history
        (   
            project_path,
            user_query,
            task,
            file_path,
            selected_model,
            result,
            success
        )

        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            get_project_path(),
            state["user_query"],
            state["current_task"],
            state["file_path"],
            state["selected_model"],
            state["result"],
            state["execution_success"]
        )
    )
    
    conn.commit()
    conn.close()

# this is the retireval code
def get_recent_history(limit = 5):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 
            user_query,
            task,
            result, 
            success
        FROM task_history 
        ORDER BY id DESC

        LIMIT ?
        """,
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows 

def search_memory(user_query : str):
    """Retrieve the previously executed task """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 
            user_query,
            task,
            result,
            success
        FROM task_history 
        WHERE project_path = ? 
        ORDER BY timestamp DESC
        LIMIT 5
        """,
        (get_project_path(),)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows