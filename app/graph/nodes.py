from app.tools.docker_compose_generator import save_docker_compose
from app.models.model_router import select_model
from app.tools.project_analyzer import analyze_project
from app.tools.code_explainer import explain_code
from app.tools.debug_assistant import debug_error
from app.tools.deployment_generator import generate_dockerfile, save_dockerfile
from app.tools.requirements_generator import generate_requirements, save_requirements
from app.tools.docker_compose_generator import generate_compose, save_composee
from app.graph.evaluator import evaluate_execution
from app.graph.planner import create_plan


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

# getting the current task
def get_current_task(state):

    state["current_task"] = state["plan"][
        state["current_step"]
    ]

    return state

# router node functionality
def route_model(state):
    task = state["current_task"]
    model = select_model(task)
    state["selected_model"] = model
    return state

# test node functionality
def execute_task(state):
    task = state["current_task"]

    if task == "analyze":
        report = analyze_project(".")
        state["result"] = report["analysis"]
        return state

    # Execute the explanation using the model selected by the LangGraph routing stage.
    elif task == "explain":
        file_path = state["file_path"]
        result = explain_code(file_path , selected_model = state["selected_model"])
        state["result"] = result
        return state

    elif task == "debug":
        file_path = state["file_path"]
        with open(file_path) as f:
            error_text = f.read()

        result = debug_error(error_text)
        state["result"] = result
        return state    

    elif task == "deployment":
        query = state["user_query"].lower()

        if "docker" in query:
            result = save_dockerfile(".")
            state["result"] = result
            return state 
        elif "requirements" in query:
            packages = save_requirements(".")
            state["result"] = (
                f"Generated requirements.txt "
                f"with {len(packages)} packages."
            )
            return state

        elif "compose" in query:
            result = save_docker_compose(".")
            state["result"] = result
            return state
        
        # if no state has been called we can simply return the previous statements
        state["result"] = (
            "Deployment task detected but "
            "no deployment type specified."
        )

        return state


# planner node
def planner_node(state):
    plan = create_plan(
        state["user_query"]
    )
    state["plan"] = plan 
    state["current_step"] = 0
    state["current_task"] = plan[0]

    return state

# this makes the agent go iteratively 
def advance_step(state):
    state["current_step"] += 1
    if state["current_step"] < len(state["plan"]):
        state["current_task"] = state["plan"][
            state["current_step"]
        ]
        return state

# this makes the agent to take an advance step while planning goes on 
def should_continue(state):
    if not state["execution_success"]:
        return "finish"
    if state["current_step"] >= len(state["plan"]):
        return "finish"

    return "continue"

# evaluation of the agent to see if finished the task or not
def evaluate_task(state):
    success = evaluate_execution(
        state["result"]
    )
    state["execution_success"] = success
    return state

