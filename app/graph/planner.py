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
    Cleans raw LLM planner response text into strictly valid JSON.
    Handles markdown codeblocks, inline comments, unescaped quotes, single quotes, and trailing comma artifacts.
    """
    if not raw_text or not raw_text.strip():
        return '{"tasks": []}'

    text = raw_text.strip()

    # 1. Strip markdown codeblocks
    if "```" in text:
        match = re.search(r"```(?:json)?\s*(.*?)(?:```|$)", text, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()

    # 2. Extract root JSON object bounds
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        text = text[first_brace : last_brace + 1]

    # 3. Clean inline/block comments
    text = re.sub(r"//.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

    # 4. Fast path: try standard json.loads
    try:
        json.loads(text)
        return text.strip()
    except Exception:
        pass

    # 5. Try Python dict literal parsing (handles single quotes safely)
    try:
        import ast
        val = ast.literal_eval(text)
        if isinstance(val, (dict, list)):
            return json.dumps(val)
    except Exception:
        pass

    # 6. Fallback regex repairs
    text_fixed = re.sub(r"'+\s*\"", '"', text)
    text_fixed = re.sub(r"\"+\s*'", '"', text_fixed)
    text_fixed = re.sub(r"([{\s,])'([a-zA-Z0-9_]+)'\s*:", r'\1"\2":', text_fixed)
    text_fixed = re.sub(r":\s*'([^'\n]*?)'*(\s*[,}\]])", r': "\1"\2', text_fixed)
    text_fixed = re.sub(r",\s*([\}\]])", r"\1", text_fixed)

    if text_fixed.count('"') % 2 != 0:
        text_fixed += '"'

    open_braces = text_fixed.count("{") - text_fixed.count("}")
    open_brackets = text_fixed.count("[") - text_fixed.count("]")
    if open_brackets > 0:
        text_fixed += "]" * open_brackets
    if open_braces > 0:
        text_fixed += "}" * open_braces

    try:
        json.loads(text_fixed)
        return text_fixed.strip()
    except Exception:
        pass

    return text.strip()



# Qwen planner fix:
# Normalize tool/operation mismatches before strict plan validation.
# Keep tool semantics separate from executable operation semantics.
def normalize_planner_dict(raw_data: Any) -> dict[str, Any]:
    """
    Normalizes raw dict parsed from LLM planner output prior to Pydantic validation.
    Maps invalid tool/operation combinations (such as tool="explain", operation="explain")
    to valid operational modes while preserving tool semantics.
    """
    if isinstance(raw_data, list):
        raw_data = {"tasks": raw_data}

    if not isinstance(raw_data, dict):
        return {"tasks": []}

    tasks = raw_data.get("tasks")
    if not isinstance(tasks, list):
        return {"tasks": []}

    valid_ops = {"inspect", "search", "analyze", "modify", "create", "test", "verify"}
    valid_tools = {
        "analyze", "search", "edit", "debug", "explain", "deployment",
        "test", "verify", "translate", "create", "modify", "refactor",
        "optimize", "fix", "convert"
    }

    normalized_tasks = []
    for task in tasks:
        if not isinstance(task, dict):
            continue

        task_copy = dict(task)

        # 1. Clean quote artifacts from filenames
        if isinstance(task_copy.get("target_file"), str):
            task_copy["target_file"] = task_copy["target_file"].strip("'\" ")
        if isinstance(task_copy.get("source_file"), str):
            task_copy["source_file"] = task_copy["source_file"].strip("'\" ")

        # 2. Extract and sanitize tool
        tool = task_copy.get("tool")
        if isinstance(tool, str):
            tool_clean = tool.strip("'\" ").lower()
            if tool_clean in valid_tools:
                task_copy["tool"] = tool_clean

        # 3. Handle operation normalization and tool/operation mismatches
        op = task_copy.get("operation")
        op_str = str(op).strip("'\" ").lower() if op is not None else ""

        if op_str in valid_ops:
            task_copy["operation"] = op_str
        else:
            # LLM copied tool value into operation or generated an invalid operation name
            current_tool = task_copy.get("tool")
            if current_tool == "explain" or op_str == "explain":
                task_copy["operation"] = "inspect"
            elif current_tool == "search" or op_str == "search":
                task_copy["operation"] = "search"
            elif current_tool == "analyze" or op_str in {"analyze", "analysis"}:
                task_copy["operation"] = "analyze"
            elif current_tool == "debug" or op_str in {"debug", "debugging"}:
                task_copy["operation"] = "inspect"
            elif current_tool == "deployment" or op_str in {"deployment", "deploy"}:
                task_copy["operation"] = "create"
            elif current_tool in {"edit", "create", "modify", "refactor", "fix", "convert"} or op_str in {"edit", "update", "fix", "refactor"}:
                task_copy["operation"] = "create" if task_copy.get("target_file") else "modify"
            else:
                task_copy["operation"] = "inspect"

        normalized_tasks.append(task_copy)

    return {"tasks": normalized_tasks}


def parse_and_validate_plan(raw_text: str) -> Plan:
    """
    Cleans raw LLM response text, normalizes tool/operation dictionary artifacts,
    and validates against the Pydantic Plan schema.
    """
    cleaned = clean_planner_json(raw_text)
    data = json.loads(cleaned)
    normalized = normalize_planner_dict(data)
    return Plan.model_validate(normalized)


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

    valid_tools = {
        "analyze", "search", "edit", "debug", "explain", "deployment",
        "test", "verify", "translate", "create", "modify", "refactor",
        "optimize", "fix", "convert"
    }
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
        elif tool in {"translate", "create", "modify", "refactor", "optimize", "fix", "convert"}:
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

    is_create_intent = any(w in query_lower for w in ["create", "new file", "convert", "generate a new"])
    if is_create_intent:
        for task_dict in sanitized_tasks:
            if task_dict.get("tool") == "edit":
                task_dict["operation"] = "create"

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
    elif is_edit_query and not has_edit_task and not is_deployment_query:
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
        plan = parse_and_validate_plan(raw_response)
        return sanitize_plan_tasks(plan, user_query, active_file)
    except Exception as exc:
        print(f"\nPlanner V2 validation notice: First attempt required recovery retry ({exc}). Retrying...\n")

        correction_prompt = f"""
Original User Request: {user_query}
{context_str}

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
            plan_retry = parse_and_validate_plan(retry_raw)
            return sanitize_plan_tasks(plan_retry, user_query, active_file)
        except Exception as retry_exc:
            is_deploy_query = any(w in user_query.lower() for w in ["docker", "dockerfile", "compose", "requirements", "deploy", "container"])
            default_tool = "deployment" if is_deploy_query else ("edit" if any(w in user_query.lower() for w in ["fix", "modify", "update", "convert", "create"]) else "analyze")
            fallback_task = Task(
                tool=default_tool,
                operation="create" if "convert" in user_query.lower() or "create" in user_query.lower() else "modify",
                instruction=user_query,
                source_file=active_file or None,
            )
            return [fallback_task.model_dump()]