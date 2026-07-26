from pathlib import Path

from app.models.model_router import select_model
from app.tools.project_analyzer import analyze_project
from app.tools.code_explainer import explain_code
from app.tools.debug_assistant import debug_error
from app.tools.deployment_generator import save_dockerfile
from app.tools.requirements_generator import save_requirements
from app.tools.docker_compose_generator import save_docker_compose
from app.graph.evaluator import evaluate_execution
from app.graph.planner import create_plan
from app.memory.memory_manager import save_execution, search_memory


# # classifier node functionality
# def classify_task(state):
#     query = state["user_query"].lower()

#     if "debug" in query:
#         task = "debug"
#     elif "explain" in query:
#         task = "explain"
#     elif (
#         "docker" in query
#         or "deploy" in query
#         or "requirements" in query
#         or "compose" in query
#     ):
#         task = "deployment"
#     else:
#         task = "analyze"

#     state["task_type"] = task
#     return state

def get_current_task(state):
    """Load the execution-plan item selected by ``current_step``."""

    state["current_task"] = state["plan"][
        state["current_step"]
    ]

    return state

def route_model(state):
    """Select the local model for the active task."""

    task = state["current_task"]
    model = select_model(task)
    state["selected_model"] = model
    return state

def execute_task(state):
    """Execute one planned task and record its textual result."""

    task = state["current_task"]
    project_path = state.get("project_path", ".")

    try:
        if task == "Use memory context":
            state["result"] = "Used memory context."
            return state

        if task == "analyze":
            report = analyze_project(project_path, state["selected_model"])
            state["result"] = report["analysis"]
            return state

        if task == "explain":
            result = explain_code(
                state["file_path"],
                selected_model=state["selected_model"],
            )
            state["result"] = result
            return state

        if task == "debug":
            error_text = Path(state["file_path"]).read_text(encoding="utf-8")
            state["result"] = debug_error(error_text, state["selected_model"])
            return state

        if task == "deployment":
            query = state["user_query"].lower()
            if "compose" in query:
                state["result"] = save_docker_compose(project_path, state["selected_model"])
            elif "requirements" in query:
                packages = save_requirements(project_path)
                state["result"] = f"Generated requirements.txt with {len(packages)} packages."
            elif "docker" in query:
                state["result"] = save_dockerfile(project_path, state["selected_model"])
            else:
                state["result"] = "Deployment task detected but no deployment type specified."
            return state

        state["result"] = f"Error: unsupported task '{task}'."
        return state
    except Exception as exc:
        state["result"] = f"Error: {type(exc).__name__}: {exc}"
        return state


def planner_node(state):
    """Create the ordered execution plan for the current request."""

    plan = create_plan(
        user_query = state["user_query"],
        memory = state["memory_context"]
    )
    state["plan"] = plan 
    state["current_step"] = 0
    state["current_task"] = plan[0]

    return state

# this makes the agent go iteratively 
def advance_step(state):
    """
    Move to the next task in the execution plan.
    """
    state["current_step"] += 1
    if state["current_step"] < len(state["plan"]):
        state["current_task"] = state["plan"][state["current_step"]]

    return state

def should_continue(state):
    """Route to the next plan item only after a successful task."""

    if not state["execution_success"]:
        return "finish"
    if state["current_step"] >= len(state["plan"]):
        return "finish"

    return "continue"

def evaluate_task(state):
    """Evaluate the result produced by the active task."""

    success = evaluate_execution(
        state["result"]
    )
    state["execution_success"] = success
    return state

def memory_update(state):
    """Persist the completed task as project memory."""

    if state["current_task"] != "Use memory context":
        save_execution(state)
    return state 

def memory_lookup(state):
    """Load bounded project memory before planning."""
    rows = search_memory(
        state.get("project_path", ".")
    )
    if not rows:
        state["memory_context"] = ""
        return state 
    
    context_parts = []
    for query, task, result, success in rows:
        context_parts.append(
            "\n".join(
                (
                    f"Previous Query: {query}",
                    f"Task: {task}",
                    f"Succeeded: {bool(success)}",
                    f"Result: {result[:4000]}",
                )
            )
        )
    state["memory_context"] = "\n\n".join(context_parts)
    return state 
