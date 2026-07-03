from taskiq_aio_pika import AioPikaBroker
from taskiq_redis import RedisAsyncResultBackend
from taskiq_pipelines import PipelineMiddleware
from src.config import BROKER_URL

broker = AioPikaBroker(BROKER_URL).with_result_backend(RedisAsyncResultBackend("redis://localhost"))
broker.add_middlewares(PipelineMiddleware())


