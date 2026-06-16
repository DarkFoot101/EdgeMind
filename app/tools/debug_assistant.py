from app.models.model_router import select_model
from app.models.ollama_client import generate_response


def debug_error(error_text: str):

    model = select_model("debug")

    prompt = f"""
        You are an expert Python debugging assistant.

        Analyze the following error.

        Provide:

        1. Root Cause
        2. Explanation
        3. Suggested Fix

        Error:

        {error_text}
    """

    response = generate_response(
        prompt=prompt,
        model=model
    )

    return response