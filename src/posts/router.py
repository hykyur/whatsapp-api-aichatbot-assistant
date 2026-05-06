from fastapi import APIRouter, Request, Response, Depends
from sqlalchemy import select

from src.database import get_session
from src.config import META_API_VERSION, META_API_TOKEN, BUSINESS_PHONE_ID
from src.models import User, MessageRole, MessageStatus

from src.posts.utils import store_message, read_user_messages
from src.posts.services import ai_reformulates, ai_check_escalation, ai_response
from src.posts.models import Webhook

import requests

router = APIRouter()

# TODO: IMPLEMENT FASTAPI BACKGROUND TASKS TO MAKE THIS MUCH MORE EFFICIENT

# TODO: TAKE ADVANTAGE OF THE FIELD FROM THE WEBHOOK TO MAKE DIFFERENT CHANGES ON THE DATABASE, E.G, phone_number_update

@router.post("/whatsapp/webhook")
async def read_message(request: Request, session = Depends(get_session)) -> Response:
    json = await request.json()
    parsed = Webhook.model_validate(json)

    name = parsed.entry[0].changes[0].value.contacts[0].profile.name
    phone = parsed.entry[0].changes[0].value.contacts[0].wa_id
    body = parsed.entry[0].changes[0].value.messages[0].text.body

    await store_message(session, name, phone, MessageRole.user, MessageStatus.pending, body)


    statement = await session.execute(select(User.id).where(User.phone == phone))
    user_id = statement.scalar()
    conversation = await read_user_messages(session, user_id)

    phone_str = phone

    await ai_check_escalation(session, user_id, conversation)

    for message in conversation: #TODO: REWRITE THIS FOR EFFICIENCY
        if message.role == MessageStatus.drafting: #TODO: AGAIN, IMPLEMENT WORKER LOGIC INPUT TO ACTUALLY HAVE MESSAGES WITH DRAFTING STATUS
            await ai_reformulates(session, message)
            await session.flush()

    reply = await ai_response(session, user_id, conversation)
    await session.commit()

    # META API REQUEST CONSTRUCTOR
    url = f"https://graph.facebook.com/{META_API_VERSION}/{BUSINESS_PHONE_ID}/messages"
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_str,
        "type": "text",
        "text": {
            "body": reply.body
        }
    }
    headers = {
        "Authorization": f"Bearer {META_API_TOKEN}",
        "Content-Type": "application/json"
    }


    response = requests.request("POST", url, json=data, headers=headers)

    return response.json()


'''TODO: 
TRY TO DITCH THE FOR LOOP FOR EFFICIENCY 
-> REWRITING THE MESSAGE ON THE MOMENT OF WORKER INPUT
-> NEEDS THE LOGIC FOR THAT BEFOREHAND '''

