# pyrefly: ignore [missing-import]
from app.graph.nodes import evaluate_task
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
    planner_node
)

graph = StateGraph(EdgeMindState)

# creating the graph nodes
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
    "advance",
    advance_step
)
graph.add_node(
    "evaluator",
    evaluate_task
)

# set the entry point for the planner node
graph.set_entry_point("planner")

# adding the edges
graph.add_edge("planner", "task")

graph.add_edge("task", "router")

graph.add_edge("router", "executor")

graph.add_edge("executor", "evaluator")

graph.add_edge("evaluator", "advance")

# now we are adding the conditional edge, that acts with the advanced step 
graph.add_conditional_edges(
    'advance',
    should_continue,
    {
        "continue": "task",
        "finish": END
    }
)

# compiling the graph 
workflow = graph.compile()
