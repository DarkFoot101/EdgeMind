# pyrefly: ignore [missing-import]
from langgraph.graph import StateGraph
# pyrefly: ignore [missing-import]
from langgraph.graph import END

from app.graph.state import EdgeMindState

from app.graph.nodes import (
    route_model,
    execute_task,
    get_current_task,
    advance_step,
    should_continue,
    should_continue_after_advance,
    planner_node,
    evaluate_task,
    memory_update,
    memory_lookup,
    retry_node
)

graph = StateGraph(EdgeMindState)

# creating the graph nodes
graph.add_node(
    "memory_lookup",
    memory_lookup
)
graph.add_node(
    "planner",
    planner_node
)
graph.add_node(
    "task",
    get_current_task
)
graph.add_node(
    "router",
    route_model
)
graph.add_node(
    "executor",
    execute_task
)
graph.add_node(
    'retry',
    retry_node
)
graph.add_node(
    "memory",
    memory_update
)

graph.add_node(
    "advance",
    advance_step
)
graph.add_node(
    "evaluator",
    evaluate_task
)

# set the entry point for the planner node
graph.set_entry_point("memory_lookup")

# adding the edges
graph.add_edge("memory_lookup", "planner")

graph.add_edge("planner", "task")

graph.add_edge("task", "router")

graph.add_edge("router", "executor")

graph.add_edge("executor", "evaluator")

graph.add_conditional_edges(
    "evaluator",
    should_continue,
    {
        "retry": "retry",
        "continue": "memory",
        "finish": END
    }
)

graph.add_edge("retry", "router")

graph.add_edge("memory", "advance")

graph.add_conditional_edges(
    "advance",
    should_continue_after_advance,
    {
        "continue": "task",
        "finish": END
    }
)

# compiling the graph 
workflow = graph.compile()
