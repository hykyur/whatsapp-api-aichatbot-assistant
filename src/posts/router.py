from fastapi import APIRouter, Request

from src.posts.schemas import Webhook

from src.queues.pipeline import enqueue_message_pipe

router = APIRouter()

# TODO: TAKE ADVANTAGE OF THE FIELD FROM THE WEBHOOK TO MAKE DIFFERENT CHANGES ON THE DATABASE, E.G, phone_number_update (HANDLE MOST OF THE FIELDS TO ADAPT THE DATABASE)

@router.post("/whatsapp/webhook")
async def read_message(request: Request):
    body = await request.body()
    parsed = Webhook.model_validate_json(body)

    value = parsed.entry[0].changes[0].value
    if not value.messages or not value.contacts:
        return {"status": "ignored"}

    message = value.messages[0]
    if message.type != "text" or not message.text:
        return {"status": "ignored"}

    if value.contacts[0].profile is None:
        name = None
    else:
        name = value.contacts[0].profile.name
    phone = value.contacts[0].wa_id
    bsuid = value.contacts[0].user_id
    body = message.text.body
    await enqueue_message_pipe(name, phone, bsuid, body)

    return {"status" : "queued"}