from fastapi import APIRouter, Request, Depends
from celery import chain
from src.database import get_session


from src.posts.models import Webhook

from src.celery.tasks import add_message, check_escalation, reformulate_drafts, get_response, send_response

router = APIRouter()

# TODO: TAKE ADVANTAGE OF THE FIELD FROM THE WEBHOOK TO MAKE DIFFERENT CHANGES ON THE DATABASE, E.G, phone_number_update (HANDLE MOST OF THE FIELDS TO ADAPT THE DATABASE)

@router.post("/whatsapp/webhook")
async def read_message(request: Request, session = Depends(get_session)):
    json = await request.json()
    parsed = Webhook.model_validate(json)

    name = parsed.entry[0].changes[0].value.contacts[0].profile.name
    phone = parsed.entry[0].changes[0].value.contacts[0].wa_id
    body = parsed.entry[0].changes[0].value.messages[0].text.body # None pode ser um problema?

    chain(add_message.s(name, phone, body) | check_escalation.s() | reformulate_drafts.s() | get_response.s() | send_response.s())

    return {"status" : "ok"}


