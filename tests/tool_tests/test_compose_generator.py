from app.tools.docker_compose_generator import (
    generate_docker_compose,
    save_docker_compose
)

print(generate_docker_compose("."))

print(save_docker_compose("."))