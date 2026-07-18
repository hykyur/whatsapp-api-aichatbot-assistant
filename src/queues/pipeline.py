from taskiq_pipelines import Pipeline
from src.queues.broker import broker
from src.queues.tasks import add_message, check_escalation, get_response, send_response
async def enqueue_message_pipe(name: str | None, phone: str, bsuid:str, body: str):
    await broker.startup()
    pipe = (
        Pipeline(
            broker,
            add_message
        )
        .call_next(check_escalation)
        .call_next(get_response)
        .call_next(send_response)
    )
    task = await pipe.kiq(name, phone, bsuid, body)
    await broker.shutdown()
    return task