from pathlib import Path

from app.models.model_router import select_model
from app.models.ollama_client import generate_response


def explain_code(file_path: str , selected_model: str):

    file = Path(file_path)

    if not file.exists():
        return "File not found."

    code = file.read_text()

    # to prevent ollama from crying lol
    if len(code) > 100000:
        code = code[:100000]

    # the tool should select the model required to execute the task
    # model = select_model("explain")
    # model_execution = select_model("explain", model)

    prompt = f"""
        You are a senior software engineer.

        Explain the following code.

        Provide:

        1. Purpose
        2. Main Functions
        3. Workflow
        4. Important Notes

        Code:

        {code}
    """

    explanation = generate_response(
        prompt=prompt,
        model=selected_model
    )

    return explanation