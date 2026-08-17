"""
EdgeMind V2.1 Conversation & Follow-Up Handler

Processes follow-up questions and conversational companion queries using previous
session context and SQLite execution history without triggering file modification workflows.
"""

from typing import Dict, Any, Optional
from app.events.activity_stream import ActivityStream, EventType
from app.models.ollama_client import generate_response
from app.models.model_router import select_model


FOLLOW_UP_SYSTEM_PROMPT = """You are EdgeMind, an expert local AI software engineering companion.
The user is asking a follow-up question about a previous code edit or execution turn.
Use the provided execution context, plan, modified files, diff, and query history to answer their question directly, clearly, and concisely.
Do NOT attempt to make new code edits or generate tool commands.
If asked "what did you change?", summarize the exact changes cleanly in bullet points.
If asked "why did you change it?", explain the rationale behind the technical choices.
If asked "explain that", explain the implementation details clearly.
Keep your response helpful, technical, and natural."""

CONVERSATIONAL_SYSTEM_PROMPT = """You are EdgeMind, an expert local AI software engineering companion pair-programming with the user.
The user is having a technical discussion, asking for architectural advice, or sharing feedback.
Respond conversationally, thoughtfully, and concisely as an experienced tech lead companion.
Use the active project context if relevant. Do NOT generate code diffs or command execution payloads unless explicitly asked."""


def handle_follow_up(
    query: str,
    session_state: Any,
    memory_context: str = "",
) -> Dict[str, Any]:
    """
    Handles follow-up questions using session memory and SQLite context.
    Strictly read-only: does NOT modify any files on disk.
    """
    ActivityStream.emit("Understanding request...", EventType.PROGRESS, stage="follow_up")
    ActivityStream.emit("This is a follow-up question about the previous edit.", EventType.INFO, stage="follow_up")
    ActivityStream.emit("Loading previous execution context...", EventType.PROGRESS, stage="follow_up")

    last_query = getattr(session_state, "last_query", "") or "Previous request"
    last_edited = getattr(session_state, "last_edited_file", None) or getattr(session_state, "active_file", None) or "target file"
    last_result = getattr(session_state, "last_result", "") or ""
    last_plan = getattr(session_state, "last_plan", []) or []

    ActivityStream.emit(f"Previous target: {last_edited}", EventType.INFO, stage="follow_up")
    ActivityStream.emit("Reviewing the changes made...", EventType.PROGRESS, stage="follow_up")

    # Extract key change insights from previous result
    changes_count = 1
    if "diff" in last_result.lower() or "---" in last_result:
        changes_count = max(len([line for line in last_result.splitlines() if line.startswith("+") and not line.startswith("+++")]), 1)
    
    ActivityStream.emit(f"Found {changes_count} significant change{'s' if changes_count != 1 else ''}.", EventType.SUCCESS, stage="follow_up")

    context_prompt = f"""
Previous Execution Context:
- Original Request: {last_query}
- Active / Modified File: {last_edited}
- Plan Tasks Executed: {last_plan}
- Previous Result & Diff Output:
{last_result[:2500]}

{memory_context}

User Follow-Up Question: {query}
"""

    model = select_model("conversational")
    response_text = generate_response(
        prompt=context_prompt,
        model=model,
        system_prompt=FOLLOW_UP_SYSTEM_PROMPT,
    )

    formatted_answer = f"EdgeMind:\n{response_text.strip()}\nNo additional files were modified."

    return {
        "user_query": query,
        "result": formatted_answer,
        "execution_success": True,
        "intent": "follow_up",
        "modified_file": None,
        "source_file": last_edited,
        "selected_model": model,
    }


def handle_conversational(
    query: str,
    session_state: Any,
    memory_context: str = "",
) -> Dict[str, Any]:
    """
    Handles general conversational queries, architecture discussions, and chit-chat.
    Strictly read-only: does NOT modify any files on disk.
    """
    ActivityStream.emit("Understanding request...", EventType.PROGRESS, stage="conversational")
    ActivityStream.emit("Conversational inquiry detected...", EventType.INFO, stage="conversational")

    active_file = getattr(session_state, "active_file", None) or ""
    project_path = getattr(session_state, "project_path", ".") or "."

    context_prompt = f"""
Active Working Context:
- Project Path: {project_path}
- Active File: {active_file}

{memory_context}

User Prompt: {query}
"""

    model = select_model("conversational")
    response_text = generate_response(
        prompt=context_prompt,
        model=model,
        system_prompt=CONVERSATIONAL_SYSTEM_PROMPT,
    )

    return {
        "user_query": query,
        "result": f"EdgeMind:\n{response_text.strip()}",
        "execution_success": True,
        "intent": "conversational",
        "modified_file": None,
        "source_file": active_file or None,
        "selected_model": model,
    }
