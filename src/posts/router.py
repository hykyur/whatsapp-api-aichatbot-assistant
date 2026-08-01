from fastapi import APIRouter, Request, Header, HTTPException
from pydantic import ValidationError

from src.config import config
from src.posts.schemas import Webhook
from src.queues.pipeline import enqueue_message_pipe

from datetime import datetime, timezone
import hashlib
import hmac
import logging
import os
from typing import Any, Optional

env = os.environ["ENVIRONMENT"]

META_API_TOKEN = config.META_API_TOKEN

logger = logging.getLogger(__name__)
router = APIRouter()

# TODO: TAKE ADVANTAGE OF THE FIELD FROM THE WEBHOOK TO MAKE DIFFERENT CHANGES ON THE DATABASE, E.G, phone_number_update (HANDLE MOST OF THE FIELDS TO ADAPT THE DATABASE)

# def verify_signature(payload: bytes, signature_header: Optional[str]) -> bool:
#     """Validate the X-Hub-Signature-256 header Meta sends with every POST."""
#     if not signature_header or not signature_header.startswith("sha256="):
#         return False
#     expected = hmac.new(META_API_TOKEN.encode(), payload, hashlib.sha256).hexdigest()
#     provided = signature_header.removeprefix("sha256=")
#     return hmac.compare_digest(expected, provided)

@router.post("/whatsapp/webhook", status_code=202)
async def read_message(request: Request,  x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256")):
    body = await request.body()
    # if not verify_signature(body, x_hub_signature_256):
    #     raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        parsed = Webhook.model_validate_json(body)
    except ValidationError as e:
        print(e)
        raise HTTPException(status_code=422, detail="Webhook couldn't be validated by JSON Parsing")

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
    wamid = message.id
    body_text = message.text.body
    task = await enqueue_message_pipe(name, phone, bsuid, wamid, body_text)
    return {
        "status" : "queued",
        "task_id": task.task_id,
        "enqueued_at": datetime.now(timezone.utc),
        "content": body_text,
        "user_phone": phone,
        "user_bsuid": bsuid
    }


