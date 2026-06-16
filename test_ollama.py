from app.models.ollama_client import generate_response
from app.models.model_router import select_model

model = select_model("simple")

print(model)

response = generate_response(
    "What is Python?",
    model
)

print(response)