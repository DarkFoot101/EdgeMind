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
Modify existing code or create a new file based on existing code.

Use this tool for:
- fixing bugs
- converting programming languages
- refactoring
- optimization
- improving readability
- creating a new file from existing code

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

Only output JSON matching the Schema.

Schema:

{
    "tasks":[
        {
            "tool":"analyze",
            "instruction":""
        },
        {
            "tool":"edit",
            "instruction":"Convert Java to optimized Python.",
            "target_file":"good.py",
            "operation":"create"
        }
    ]
}

If the user wants to create a new file (e.g. "create good.py", "save as optimized.py", etc.), set "operation" to "create" and "target_file" to the name/path of the file to create (e.g., "good.py").
Otherwise, set "operation" to "modify" and "target_file" to null or the name of the file being modified.

Good Example 1

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
            "instruction":"Convert the Java implementation into clean Python and optimize the dynamic programming algorithm.",
            "target_file":null,
            "operation":"modify"
        }
    ]
}

Good Example 2

User:
Convert bad.java to Python and create good.py

Output:

{
    "tasks":[
        {
            "tool":"analyze"
        },
        {
            "tool":"edit",
            "instruction":"Convert bad.java to Python.",
            "target_file":"good.py",
            "operation":"create"
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
) -> list[dict]:
    """
    Generate a validated execution plan.
    """

    prompt = f"""
        Memory Context:
        {memory}
        User Request:
        {user_query}
    """

    model = select_model("planner")
    response = generate_response(
        prompt=prompt,
        model=model,
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
        print("\nPlanner Validation Failed on first attempt, retrying with correction prompt...\n")
        print(exc)

        # Retry once with a correction prompt
        correction_prompt = f"""
        Your previous response was invalid.
        Error: {str(exc)}
        
        Previous Output:
        {response}
        
        Please correct the output. It must be valid JSON conforming to the schema:
        {{
            "tasks": [
                {{
                    "tool": "analyze" | "edit" | "debug" | "deployment" | "explain",
                    "instruction": "...",
                    "target_file": "..." | null,
                    "operation": "modify" | "create"
                }}
            ]
        }}
        Only output the JSON object. Do not include explanation.
        """

        try:
            retry_response = generate_response(
                prompt=correction_prompt,
                model=model,
                system_prompt=SYSTEM_PROMPT,
            )
            print("\n===== RAW PLANNER RETRY OUTPUT =====")
            print(retry_response)
            print("====================================\n")

            cleaned = clean_response(retry_response)
            plan = Plan.model_validate_json(cleaned)
            return [task.model_dump() for task in plan.tasks]
        except Exception as retry_exc:
            print("\nPlanner Validation Failed on retry.\n")
            print(retry_exc)
            raise RuntimeError(f"Planner failed to generate a valid execution plan. Validation error: {retry_exc}")