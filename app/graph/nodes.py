from app.models.model_router import select_model
from app.tools.project_analyzer import analyze_project
from app.tools.code_explainer import explain_code
from app.tools.debug_assistant import debug_error

# classifier node functionality
def classify_task(state):
    query = state["user_query"].lower()

    if "debug" in query:
        task = "debug"
    elif "explain" in query:
        task = "explain"
    elif "docker" in query:
        task = "deployment"
    else:
        task = "analyze"

    state["task_type"] = task
    return state

# router node functionality
def route_model(state):
    task = state["task_type"]
    model = select_model(task)
    state["selected_model"] = model
    return state

# test node functionality
def execute_task(state):
    task = state["task_type"]

    if task == "analyze":
        report = analyze_project(".")
        state["result"] = report["analysis"]
        return state

    if task == "explain":
        file_path = state["file_path"]
        result = explain_code(file_path)
        state["result"] = result
        return state

    if task == "debug":
        file_path = state["file_path"]
        with open(file_path) as f:
            error_text = f.read()

        result = debug_error(error_text)
        state["result"] = result
        return state

    state["result"] = "Task not supported."

    return state