from app.graph.workflow import workflow

graph = workflow.get_graph()

print(graph.draw_mermaid())