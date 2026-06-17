# pyrefly: ignore [missing-import]
from langgraph.graph import StateGraph
# pyrefly: ignore [missing-import]
from langgraph.graph import END

from app.graph.state import EdgeMindState

from app.graph.nodes import (
    classify_task,
    route_model,
    execute_task
)

graph = StateGraph(EdgeMindState)

# creating the graph nodes
graph.add_node(
    "classifier",
    classify_task
)
graph.add_node(
    "router",
    route_model
)
graph.add_node(
    "executor",
    execute_task
)

# connecting the graph nodes 
graph.set_entry_point("classifier")
graph.add_edge(
    "classifier",
    "router"
)
graph.add_edge(
    "router",
    "executor"
)
graph.add_edge(
    "executor",
    END
)

# compiling the graph 
workflow = graph.compile()
