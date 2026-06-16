from app.tools.debug_assistant import debug_error

error = """
ModuleNotFoundError:
No module named 'langgraph'
"""

result = debug_error(error)

print(result)