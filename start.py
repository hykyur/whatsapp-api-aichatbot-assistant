import subprocess
from pathlib import Path

uvicorn_path = Path(".venv/bin/uvicorn")  # Linux/macOS
# venv_python = Path(".venv/Scripts/python.exe")  # Windows
taskiq_path = Path(".venv/bin/taskiq")

def parse_port_mapping(text: str) -> tuple[int, int] | None:
    parts = text.strip().split(":")
    if len(parts) != 2:
        return None

    host_str, container_str = parts

    if not (host_str.isdigit() and container_str.isdigit()):
        return None

    host_port = int(host_str)
    container_port = int(container_str)

    if not (1 <= host_port <= 65535 and 1 <= container_port <= 65535):
        return None

    return host_port, container_port

def parse_uvicorn_port(text: str) -> int | None:
    if len(text) != 1:
        return None

    if not text.isdigit():
        return None

    uvicorn_port = int(text)

    if not 1 <= uvicorn_port <= 65535:
        return None

    return uvicorn_port

user_input = input("Enter rabbitmq first port mapping (e.g. 5672:5672): ")
result = parse_port_mapping(user_input)

user_input_2 = input("Enter rabbitmq second port mapping (e.g. 15672:15672): ")
result_2 = parse_port_mapping(user_input_2)

if result is None or result_2 is None:
    if result is None:
        print(f"{result} is an invalid port mapping")
    if result_2 is None:
        print(f"{result_2} is an invalid port mapping")
else:
    host_port_, container_port_ = result
    host_port_2, container_port2 = result_2
    print("Valid:", host_port_, container_port_)
    print("Valid:", host_port_2, container_port2)
    try:
        subprocess.run(
            [
                "docker", "run", "--rm", "-d",
                "-p", f"{host_port_}:{container_port_}",
                "-p", f"{host_port_2}:{container_port2}",
                "--env", "RABBITMQ_DEFAULT_USER=guest",
                "--env", "RABBITMQ_DEFAULT_PASS=guest",
                "--env", "RABBITMQ_DEFAULT_VHOST=/",
                "rabbitmq:3.8.27-management-alpine",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print("Docker failed. Maybe try with different port mapping")
        print(e.stderr)

user_input_3 = input("Enter redis port mapping (e.g. 6379:6379): ")
result_3 = parse_port_mapping(user_input_3)

if result_3 is None:
    print(f"{result_3} is an invalid port mapping")
else:
    host_port_3, container_port_3 = result_3
    print("Valid:", host_port_3, container_port_3)
    try:
        subprocess.run(["docker", "run", "--rm", "-d", "-p", f"{host_port_3}:{container_port_3}", "redis"], check=True)
    except subprocess.CalledProcessError as e:
        print("Docker failed. Maybe try with different port mapping")
        print(e.stderr)

try:
    subprocess.run(
        [str(taskiq_path), "worker", "src.queues.broker:broker", "src.queues.tasks"],
        check=True, shell=True
    )
except subprocess.CalledProcessError as e:
    print("Something went wrong with taskiq worker start")
    print(e.stderr)

uvicorn_input = input("Enter uvicorn port (e.g. 5000)")
port = parse_uvicorn_port(uvicorn_input)

if port is None:
    print(f"{port} is an invalid port")
else:
    print("Valid: ", port)
    try:
        subprocess.run([str(uvicorn_path), "main:app", "--reload", "--port", f"{port}"], check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print("Something went wrong with uvicorn startup")
        print(e.stderr)