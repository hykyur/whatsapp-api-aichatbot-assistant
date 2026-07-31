from fastapi import APIRouter, Request, HTTPException

from src.posts.schemas import Webhook

from src.queues.pipeline import enqueue_message_pipe
from datetime import datetime, timezone

router = APIRouter()

# TODO: TAKE ADVANTAGE OF THE FIELD FROM THE WEBHOOK TO MAKE DIFFERENT CHANGES ON THE DATABASE, E.G, phone_number_update (HANDLE MOST OF THE FIELDS TO ADAPT THE DATABASE)

@router.post("/whatsapp/webhook", status_code=202)
async def read_message(request: Request):
    body = await request.body()
    parsed = Webhook.model_validate_json(body)

    value = parsed.entry[0].changes[0].value
    if not value.messages or not value.contacts:
        raise HTTPException(status_code=400, detail="Webhook missing messages or contacts field")

    message = value.messages[0]
    if message.type != "text" or not message.text:
        raise HTTPException(status_code=400, detail="Webhook isn't a text message, ignored.")

    if value.contacts[0].profile is None:
        name = None
    else:
        name = value.contacts[0].profile.name
    phone = value.contacts[0].wa_id
    bsuid = value.contacts[0].user_id
    body_text = message.text.body
    task = await enqueue_message_pipe(name, phone, bsuid, body_text)
    return {
        "status" : "queued",
        "task_id": task.task_id,
        "enqueued_at": datetime.now(timezone.utc),
        "content": body_text,
        "user_phone": phone,
        "user_bsuid": bsuid
    }