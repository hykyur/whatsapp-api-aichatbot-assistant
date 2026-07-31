from taskiq_aio_pika import AioPikaBroker
from taskiq_redis import RedisAsyncResultBackend
from taskiq_pipelines import PipelineMiddleware
from taskiq import InMemoryBroker
import taskiq_fastapi
from src.config import config
import os
AMQP_URL = str(config.AMQP_URL)
REDIS_URL = str(config.REDIS_URL)

env = os.environ.get("ENVIRONMENT")
if env and env == "pytest":
    broker = InMemoryBroker(await_inplace=True)
else:
    broker = AioPikaBroker(AMQP_URL).with_result_backend(RedisAsyncResultBackend(REDIS_URL))
    broker.add_middlewares(PipelineMiddleware())
    taskiq_fastapi.init(broker, "main:app")

