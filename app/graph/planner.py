"""
EdgeMind Hardened Planner V2

Uses a local LLM to convert natural-language user requests into
validated, structured multi-step execution plans conforming strictly to Plan/Task schemas.
"""

import json
import re
from typing import Any

from app.graph.planner_schema import Plan, Task
from app.models.model_router import select_model
from app.models.ollama_client import generate_response

PLANNER_SYSTEM_PROMPT = """You are the Lead Workflow Planner for EdgeMind V2, an intelligent local AI coding assistant.

Your ONLY responsibility is to analyze the user request and generate a strict, structured execution plan JSON object.

RULES:
1. Output ONLY valid JSON matching the exact Schema below.
2. NEVER output markdown explanation outside the JSON.
3. NEVER add comments inside the JSON.
4. NEVER invent tool names or operation names.
5. Set 'operation' to 'create' when converting code to a new file or generating a new target file.
6. Set 'operation' to 'modify' when updating an existing file in-place.
7. Set 'source_file' and 'target_file' whenever identified or inferred.
8. If target language differs from source language (e.g. Java -> Python), infer that 'create' operation with target_file is expected unless user explicitly asks to replace in-place.

AVAILABLE TOOLS:
- analyze     : Analyze project structure, metrics, or files (operations: inspect, analyze)
- search      : Discover files, functions, or relevant code (operations: search)
- edit        : Modify existing code or create new source files (operations: modify, create)
- debug       : Debug runtime errors, tracebacks, or failing code (operations: inspect, analyze, modify)
- explain     : Explain code structure, functions, or algorithms (operations: inspect, analyze)
- deployment  : Generate Dockerfile, requirements.txt, or compose files (operations: create)

SCHEMA:
{
  "tasks": [
    {
      "tool": "analyze" | "search" | "edit" | "debug" | "explain" | "deployment",
      "operation": "inspect" | "search" | "analyze" | "modify" | "create" | "test" | "verify",
      "instruction": "Detailed task instruction",
      "source_file": "path/to/source" | null,
      "target_file": "path/to/target" | null,
      "source_language": "python" | "java" | "cpp" | "javascript" | "typescript" | null,
      "target_language": "python" | "java" | "cpp" | "javascript" | "typescript" | null,
      "verification_requirements": "Requirements for testing or verifying result" | null
    }
  ]
}

EXAMPLES:

Example 1 (Bug Fix):
User: Fix the authentication bug in my project.
JSON:
{
  "tasks": [
    {
      "tool": "search",
      "operation": "search",
      "instruction": "Search for authentication logic and login functions across project",
      "source_file": null,
      "target_file": null,
      "source_language": null,
      "target_language": null,
      "verification_requirements": "Verify authentication bug is fixed"
    },
    {
      "tool": "edit",
      "operation": "modify",
      "instruction": "Fix the identified authentication bug",
      "source_file": null,
      "target_file": null,
      "source_language": "python",
      "target_language": "python",
      "verification_requirements": "Check syntax and functionality"
    }
  ]
}

Example 2 (Language Conversion):
User: Convert bad.java to Python.
JSON:
{
  "tasks": [
    {
      "tool": "analyze",
      "operation": "inspect",
      "instruction": "Inspect bad.java and understand algorithm structure",
      "source_file": "bad.java",
      "target_file": null,
      "source_language": "java",
      "target_language": "python",
      "verification_requirements": null
    },
    {
      "tool": "edit",
      "operation": "create",
      "instruction": "Convert Java implementation to clean idiomatic Python",
      "source_file": "bad.java",
      "target_file": "bad.py",
      "source_language": "java",
      "target_language": "python",
      "verification_requirements": "Verify valid Python AST"
    }
  ]
}

Example 3 (Optimize Algorithm):
User: Find the code responsible for Fibonacci and optimize it.
JSON:
{
  "tasks": [
    {
      "tool": "search",
      "operation": "search",
      "instruction": "Find Fibonacci implementation in project",
      "source_file": null,
      "target_file": null,
      "source_language": null,
      "target_language": null,
      "verification_requirements": null
    },
    {
      "tool": "edit",
      "operation": "modify",
      "instruction": "Optimize Fibonacci function using dynamic programming or iterative approach",
      "source_file": null,
      "target_file": null,
      "source_language": "python",
      "target_language": "python",
      "verification_requirements": "Check syntax and algorithm efficiency"
    }
  ]
}
"""


def clean_planner_json(raw_text: str) -> str:
    """
    Strips markdown code fences, trailing comments, trailing commas, and repairs unclosed JSON structures in LLM JSON output.
    """
    text = raw_text.strip()

    # 1. Remove markdown code block wrappers
    if "```" in text:
        match = re.search(r"```(?:json)?\s*(.*?)(?:```|$)", text, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()

    # 2. Locate starting '{'
    first_brace = text.find("{")
    if first_brace != -1:
        text = text[first_brace:]

    # 3. Extract complete root JSON object if end brace exists
    last_brace = text.rfind("}")
    if last_brace != -1 and last_brace > first_brace:
        text = text[: last_brace + 1]

    # 4. Remove inline JS comments (// ...) and block comments (/* ... */)
    text = re.sub(r"//.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

    # 5. Clean trailing single/double quote artifacts before double quotes (e.g. "path.py'" -> "path.py")
    text = re.sub(r"'+\s*\"", '"', text)

    # 6. Remove trailing commas in objects and arrays before closing brace/bracket
    text = re.sub(r",\s*([\}\]])", r"\1", text)

    # 7. Auto-repair unclosed arrays/objects if truncated
    text = text.rstrip(" \t\n\r,:")
    open_braces = text.count("{") - text.count("}")
    open_brackets = text.count("[") - text.count("]")
    if open_brackets > 0:
        text += "]" * open_brackets
    if open_braces > 0:
        text += "}" * open_braces

    # 8. Attempt ast.literal_eval if standard json parse fails due to single quotes
    try:
        json.loads(text)
        return text.strip()
    except Exception:
        import ast
        try:
            val = ast.literal_eval(text)
            if isinstance(val, dict):
                return json.dumps(val)
        except Exception:
            pass

    return text.strip()



def sanitize_plan_tasks(plan: Plan, user_query: str, active_file: str = "") -> list[dict[str, Any]]:
    """
    Validates and sanitizes plan tasks to ensure:
    - No null or unknown tools
    - No unrequested deployment tasks for non-deployment queries
    - Clean filename strings without trailing quote artifacts
    """
    query_lower = user_query.lower()
    is_deployment_query = any(
        kw in query_lower for kw in ["docker", "dockerfile", "compose", "requirements", "deploy", "container"]
    )

    valid_tools = {"analyze", "search", "edit", "debug", "explain", "deployment", "test", "verify", "translate"}
    valid_ops = {"inspect", "search", "analyze", "modify", "create", "test", "verify"}

    sanitized_tasks = []
    for task in plan.tasks:
        task_dict = task.model_dump()

        # Clean string quote artifacts from filenames
        if task_dict.get("target_file") and isinstance(task_dict["target_file"], str):
            task_dict["target_file"] = task_dict["target_file"].strip("'\" ")
        if task_dict.get("source_file") and isinstance(task_dict["source_file"], str):
            task_dict["source_file"] = task_dict["source_file"].strip("'\" ")

        # Fix null or unknown tool
        tool = task_dict.get("tool")
        if tool in {"test", "verify"}:
            tool = "debug" if tool == "test" else "analyze"
            task_dict["tool"] = tool
        elif tool == "translate":
            tool = "edit"
            task_dict["tool"] = tool

        if not tool or tool not in valid_tools:
            task_dict["tool"] = "edit" if any(w in query_lower for w in ["fix", "modify", "create", "convert"]) else "analyze"

        # Suppress unrequested deployment task
        if task_dict["tool"] == "deployment" and not is_deployment_query:
            task_dict["tool"] = "edit" if any(w in query_lower for w in ["fix", "modify", "create", "convert"]) else "analyze"

        # Fix null or unknown operation
        op = task_dict.get("operation")
        if not op or op not in valid_ops:
            task_dict["operation"] = "create" if task_dict.get("target_file") else "modify"

        if not task_dict.get("instruction"):
            task_dict["instruction"] = user_query

        sanitized_tasks.append(task_dict)

    is_edit_query = any(w in query_lower for w in ["fix", "modify", "update", "convert", "create", "optimize", "clean", "correct", "change", "refactor", "solve", "problem", "bug"])
    has_edit_task = any(t.get("tool") == "edit" for t in sanitized_tasks)

    if not sanitized_tasks:
        default_tool = "edit" if is_edit_query else "analyze"
        sanitized_tasks.append({
            "tool": default_tool,
            "operation": "create" if "convert" in query_lower or "create" in query_lower else "modify",
            "instruction": user_query,
            "source_file": active_file or None,
            "target_file": None,
            "source_language": None,
            "target_language": None,
            "verification_requirements": None,
        })
    elif is_edit_query and not has_edit_task:
        sanitized_tasks.append({
            "tool": "edit",
            "operation": "create" if "convert" in query_lower or "create" in query_lower else "modify",
            "instruction": user_query,
            "source_file": active_file or None,
            "target_file": None,
            "source_language": None,
            "target_language": None,
            "verification_requirements": None,
        })

    return sanitized_tasks


def create_plan(
    user_query: str,
    memory: str = "",
    active_file: str = "",
) -> list[dict[str, Any]]:
    """
    Generate and validate a structured execution plan from local LLM output.
    Uses model routing and automatic recovery retry logic.
    """
    context_str = f"Active File Context: {active_file}\n" if active_file else ""
    if memory:
        context_str += f"Project Memory:\n{memory}\n"

    prompt = f"{context_str}User Request:\n{user_query}"
    model = select_model("planner")

    raw_response = generate_response(
        prompt=prompt,
        model=model,
        system_prompt=PLANNER_SYSTEM_PROMPT,
    )

    try:
        cleaned = clean_planner_json(raw_response)
        plan = Plan.model_validate_json(cleaned)
        return sanitize_plan_tasks(plan, user_query, active_file)
    except Exception as exc:
        print(f"\nPlanner V2 validation notice: First attempt required recovery retry ({exc}). Retrying...\n")

        correction_prompt = f"""
Your previous response could not be parsed as valid JSON conforming to the schema.
Validation error: {exc}

Previous Output:
{raw_response}

Please correct your output. Return ONLY a valid JSON object matching:
{{
  "tasks": [
    {{
      "tool": "analyze" | "search" | "edit" | "debug" | "explain" | "deployment",
      "operation": "inspect" | "search" | "analyze" | "modify" | "create" | "test" | "verify",
      "instruction": "...",
      "source_file": null,
      "target_file": null,
      "source_language": null,
      "target_language": null,
      "verification_requirements": null
    }}
  ]
}}
"""
        retry_raw = generate_response(
            prompt=correction_prompt,
            model=model,
            system_prompt=PLANNER_SYSTEM_PROMPT,
        )

        try:
            cleaned_retry = clean_planner_json(retry_raw)
            plan = Plan.model_validate_json(cleaned_retry)
            return sanitize_plan_tasks(plan, user_query, active_file)
        except Exception as retry_exc:
            print(f"\nPlanner V2 fallback applied: {retry_exc}")
            default_tool = "edit" if any(w in user_query.lower() for w in ["fix", "modify", "update", "convert", "create"]) else "analyze"
            fallback_task = Task(
                tool=default_tool,
                operation="create" if "convert" in user_query.lower() or "create" in user_query.lower() else "modify",
                instruction=user_query,
                source_file=active_file or None,
            )
            return [fallback_task.model_dump()]