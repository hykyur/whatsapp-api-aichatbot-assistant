import subprocess
from pathlib import Path

uvicorn_path = Path(".venv/bin/uvicorn")
taskiq_path = Path(".venv/bin/taskiq")

try:
    subprocess.run(
        [
            "docker", "run", "--rm", "-d",
            "-p", "5672:5672",
            "-p", "15672:15672",
            "--env", "RABBITMQ_DEFAULT_USER=guest",
            "--env", "RABBITMQ_DEFAULT_PASS=guest",
            "--env", "RABBITMQ_DEFAULT_VHOST=/",
            "rabbitmq:3.8.27-management-alpine",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
except subprocess.CalledProcessError as e:
    print("RabbitMQ failed to start.")
    print(e.stderr)

try:
    subprocess.run(
        ["docker", "run", "--rm", "-d", "-p", "6379:6379", "redis"],
        check=True,
        capture_output=True,
        text=True,
    )
except subprocess.CalledProcessError as e:
    print("Redis failed to start.")
    print(e.stderr)

try:
    taskiq_proc = subprocess.Popen(
        [str(taskiq_path), "worker", "src.queues.broker:broker", "src.queues.tasks"]
    )
except Exception as e:
    print("Something went wrong with taskiq worker start")
    print(e)

try:
    uvicorn_proc = subprocess.Popen(
        [str(uvicorn_path), "main:app", "--reload", "--port", "5000"]
    )
except Exception as e:
    print("Something went wrong with uvicorn startup")
    print(e)

try:
    uvicorn_proc.wait()
except KeyboardInterrupt:
    taskiq_proc.terminate()
    uvicorn_proc.terminate()