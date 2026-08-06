"""
EdgeMind Planner V2

Uses a local LLM to convert a natural-language request
into a validated execution plan.
"""

import re

from app.graph.planner_schema import Plan
from app.models.ollama_client import generate_response
from app.models.model_router import select_model


SYSTEM_PROMPT = """
You are the workflow planner for EdgeMind.

Your ONLY responsibility is to decide which tools should execute.

You NEVER execute tools.
You NEVER explain code.
You NEVER generate code.
You NEVER answer the user's request.

----------------------------------------
AVAILABLE TOOLS
----------------------------------------

analyze
Purpose:
Analyze an entire project or a source file.

edit
Purpose:
Modify existing code.

Use this tool for:
- fixing bugs
- converting programming languages
- refactoring
- optimization
- improving readability

debug
Purpose:
Debug runtime errors or tracebacks.

explain
Purpose:
Explain existing code.

deployment
Purpose:
Generate:
- Dockerfile
- requirements.txt
- docker-compose.yml

Only use deployment if the user explicitly requests deployment-related artifacts.

----------------------------------------
RULES
----------------------------------------

Never invent tool names.

Never invent fields.

Only output JSON.

Schema:

{
    "tasks":[
        {
            "tool":"analyze",
            "instruction":""
        },
        {
            "tool":"edit",
            "instruction":"Convert Java to optimized Python."
        }
    ]
}

Good Example

User:
Fix bad_dp.java, convert it to Python and optimize it.

Output:

{
    "tasks":[
        {
            "tool":"analyze"
        },
        {
            "tool":"edit",
            "instruction":"Convert the Java implementation into clean Python and optimize the dynamic programming algorithm."
        }
    ]
}
"""


def clean_response(response: str) -> str:
    """
    Remove markdown fences and extract JSON.
    """
    response = response.strip()
    response = response.replace("```json", "")
    response = response.replace("```", "")
    match = re.search(r"\{.*\}", response, re.DOTALL)

    if not match:
        raise ValueError("Planner returned no JSON.")

    return match.group()


def create_plan(
    user_query: str,
    memory: str = "",
):
    """
    Generate a validated execution plan.
    """

    prompt = f"""
        Memory Context
        {memory}
        User Request
        {user_query}
    """

    response = generate_response(
        prompt=prompt,
        model=select_model("planner"),
        system_prompt=SYSTEM_PROMPT,
    )

    print("\n===== RAW PLANNER OUTPUT =====")
    print(response)
    print("==============================\n")

    try:
        cleaned = clean_response(response)
        plan = Plan.model_validate_json(cleaned)
        return [task.model_dump() for task in plan.tasks]

    except Exception as exc:
        print("\nPlanner Validation Failed\n")
        print(exc)

        return [
            {
                "tool": "analyze",
                "instruction": "",
            }
        ]