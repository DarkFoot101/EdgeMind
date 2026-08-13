"""
EdgeMind LangGraph V2 Workflow Orchestration

Assembles and compiles the full agentic execution graph:
memory_lookup -> planner -> file_discovery -> plan_refinement -> task -> router -> executor -> reviewer -> evaluator -> memory -> advance -> finish
"""

from langgraph.graph import StateGraph, END
from app.graph.state import EdgeMindState
from app.graph.nodes import (
    memory_lookup_node,
    planner_node,
    file_discovery_node,
    plan_refinement_node,
    get_current_task_node,
    route_model_node,
    execute_task_node,
    reviewer_node,
    evaluate_task_node,
    retry_node,
    memory_update_node,
    advance_step_node,
    should_continue,
    should_continue_after_advance,
)

graph = StateGraph(EdgeMindState)

# 1. Add operational graph nodes
graph.add_node("memory_lookup", memory_lookup_node)
graph.add_node("planner", planner_node)
graph.add_node("file_discovery", file_discovery_node)
graph.add_node("plan_refinement", plan_refinement_node)
graph.add_node("task", get_current_task_node)
graph.add_node("router", route_model_node)
graph.add_node("executor", execute_task_node)
graph.add_node("reviewer", reviewer_node)
graph.add_node("evaluator", evaluate_task_node)
graph.add_node("retry", retry_node)
graph.add_node("memory", memory_update_node)
graph.add_node("advance", advance_step_node)

# 2. Set entry point
graph.set_entry_point("memory_lookup")

# 3. Add deterministic edges
graph.add_edge("memory_lookup", "planner")
graph.add_edge("planner", "file_discovery")
graph.add_edge("file_discovery", "plan_refinement")
graph.add_edge("plan_refinement", "task")
graph.add_edge("task", "router")
graph.add_edge("router", "executor")
graph.add_edge("executor", "reviewer")
graph.add_edge("reviewer", "evaluator")

# 4. Add conditional retry/memory edges
graph.add_conditional_edges(
    "evaluator",
    should_continue,
    {
        "retry": "retry",
        "continue": "memory",
        "finish": END,
    },
)

graph.add_edge("retry", "router")
graph.add_edge("memory", "advance")

graph.add_conditional_edges(
    "advance",
    should_continue_after_advance,
    {
        "continue": "task",
        "finish": END,
    },
)

# 5. Compile workflow graph
workflow = graph.compile()
