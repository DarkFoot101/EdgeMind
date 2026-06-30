# test_graph.py

from app.graph.workflow import workflow

# result = workflow.invoke(
#     {
#         "user_query":
#             "explain this file",

#         "file_path":
#             "app/models/model_router.py"
#     }
# )
result = workflow.invoke(
    {
        "user_query":
            "analyze project",

        "file_path":
            ""
    }
)
print(result["result"])