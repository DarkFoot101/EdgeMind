from app.tools.deployment_generator import (
    generate_dockerfile,
    save_dockerfile
)

print("\nGENERATED DOCKERFILE:\n")

dockerfile = generate_dockerfile(".")

print(dockerfile)

print("\nSaving Dockerfile...\n")

print(save_dockerfile("."))