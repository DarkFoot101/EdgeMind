# this is the phase 1 planner 
# basically V1 - plans the flow of execution using simple single step task
# for V2 - planning is based on complex tasks that come up, there we will use the LLM


def create_plan(user_query : str):
    query = user_query.lower()
    plan = []

    if "analyze" in query:
        plan.append("analyze")
        
    if "explain" in query:
        plan.append("explain")

    if "debug" in query:
        plan.append("debug")

    if (
        "docker" in query
        or "deployment" in query
        or "deploy" in query
        or "requirements" in query
        or "compose" in query
    ):
        plan.append("deployment")

    if not plan:
        plan.append("analyze")

    return plan