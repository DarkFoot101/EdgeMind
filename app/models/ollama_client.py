import time
import ollama

def generate_response(prompt, model="qwen2.5-coder:3b"):

    start = time.time()

    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    end = time.time()

    print(
        f"Inference Time: {end-start:.2f}s"
    )

    return response["message"]["content"]