from fastapi import APIRouter, Request

from src.posts.models import Webhook

from src.queues.pipeline import enqueue_message_pipe

router = APIRouter()

# TODO: TAKE ADVANTAGE OF THE FIELD FROM THE WEBHOOK TO MAKE DIFFERENT CHANGES ON THE DATABASE, E.G, phone_number_update (HANDLE MOST OF THE FIELDS TO ADAPT THE DATABASE)

@router.post("/whatsapp/webhook")
async def read_message(request: Request):
    json = await request.json()
    parsed = Webhook.model_validate(json)

    value = parsed.entry[0].changes[0].value
    if not value.messages or not value.contacts:
        return {"status": "ignored"}

    message = value.messages[0]
    if message.type != "text" or not message.text:
        return {"status": "ignored"}

    name = value.contacts[0].profile.name
    phone = value.contacts[0].wa_id
    body = message.text.body
    await enqueue_message_pipe(name, phone, body)

    return {"status" : "queued"}