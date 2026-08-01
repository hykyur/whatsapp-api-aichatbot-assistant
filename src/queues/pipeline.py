from taskiq_pipelines import Pipeline
from src.queues.broker import broker
from src.queues.tasks import add_message, get_response, send_response
async def enqueue_message_pipe(name: str | None, phone: str, bsuid: str, wamid: str, body: str):
    pipe = (
        Pipeline(
            broker,
            add_message
        )
#        .call_next(check_escalation)
        .call_next(get_response)
        .call_next(send_response)
    )
    task = await pipe.kiq(name, phone, bsuid, wamid, body)
    return task