from taskiq_aio_pika import AioPikaBroker
from taskiq_redis import RedisAsyncResultBackend
from taskiq_pipelines import PipelineMiddleware
from src.config import config

AMQP_URL = str(config.AMQP_URL)
REDIS_URL = str(config.REDIS_URL)
broker = AioPikaBroker(AMQP_URL).with_result_backend(RedisAsyncResultBackend(REDIS_URL))
broker.add_middlewares(PipelineMiddleware())
