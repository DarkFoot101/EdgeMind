"""
EdgeMind V2.1 Intent Router

Classifies incoming user prompts into EXECUTION, FOLLOW_UP, or CONVERSATIONAL intents.
"""

import re
from enum import Enum
from typing import Optional, Tuple


class IntentType(str, Enum):
    EXECUTION = "execution"
    FOLLOW_UP = "follow_up"
    CONVERSATIONAL = "conversational"


# Keyword regex patterns for explicit intent routing
FOLLOW_UP_PATTERNS = [
    r"\bwhat\s+(did|have)\s+you\s+(change|do|modify|create|fix)\b",
    r"\bwhy\s+(did|have)\s+you\s+(change|do|modify|create|fix)\s+it\b",
    r"\bexplain\s+(that|the\s+change|those\s+changes|the\s+edit|your\s+edit)\b",
    r"\bwhat\s+happened\b",
    r"\bcan\s+you\s+undo\s+that\b",
    r"\bshow\s+diff\b",
    r"\bwhat\s+changed\b",
    r"\bfix\s+that\s+again\b",
    r"\bwhat\s+did\s+you\s+just\s+do\b",
    r"\breview\s+(the|those)\s+changes\b",
]

CONVERSATIONAL_PATTERNS = [
    r"\bwhat\s+do\s+you\s+think\s+about\b",
    r"\bdo\s+you\s+think\s+this\b",
    r"\btell\s+me\s+what\s+you\s+would\s+do\b",
    r"\bwhy\s+is\s+this\s+happening\b",
    r"\blet'?s\s+discuss\b",
    r"\bhaha\b",
    r"\bhello\b",
    r"\bhi\b",
    r"\bhey\b",
    r"\bwhat\s+is\s+your\s+opinion\b",
    r"\bhow\s+should\s+i\s+architect\b",
    r"\bis\s+this\s+approach\s+good\b",
]

EXECUTION_PATTERNS = [
    r"\b(fix|modify|update|edit|refactor|optimize|clean|correct|change|solve|rewrite)\b",
    r"\b(create|make|write|generate|add|build|convert|translate)\b",
    r"\b(analyze|inspect|scan|audit|debug)\b",
    r"\b(docker|dockerfile|compose|requirements|deploy|container)\b",
]


def detect_intent(query: str, has_previous_turn: bool = False) -> Tuple[IntentType, float]:
    """
    Analyzes user query text and context to return (IntentType, confidence).
    """
    q = (query or "").strip().lower()
    if not q:
        return (IntentType.CONVERSATIONAL, 1.0)

    # 1. Check Follow-Up patterns
    for pat in FOLLOW_UP_PATTERNS:
        if re.search(pat, q):
            # Follow-up questions require previous execution context
            if has_previous_turn or "what did you" in q or "explain" in q or "what changed" in q:
                return (IntentType.FOLLOW_UP, 0.95)

    # 2. Check explicit Execution imperatives
    has_exec_verb = any(re.search(pat, q) for pat in EXECUTION_PATTERNS)
    has_file_mention = bool(re.search(r"[\w./\\-]+\.[a-za-z0-9]+", q)) or "file" in q or "code" in q

    # If query specifically requests file creation, modification, code conversion, or debugging
    if has_exec_verb and (has_file_mention or any(w in q for w in ["fix", "create", "modify", "convert", "generate", "debug", "add"])):
        # Ensure it is not merely asking a conversational question about architecture or opinion
        if not any(re.search(pat, q) for pat in CONVERSATIONAL_PATTERNS):
            return (IntentType.EXECUTION, 0.95)

    # 3. Check Conversational patterns
    for pat in CONVERSATIONAL_PATTERNS:
        if re.search(pat, q):
            return (IntentType.CONVERSATIONAL, 0.9)

    # 4. Fallback intent logic
    if has_exec_verb:
        return (IntentType.EXECUTION, 0.8)

    if has_previous_turn and any(w in q for w in ["why", "what", "how", "explain", "undo"]):
        return (IntentType.FOLLOW_UP, 0.85)

    # General conversational fallback
    return (IntentType.CONVERSATIONAL, 0.75)
