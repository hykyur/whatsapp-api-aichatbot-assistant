from dotenv import load_dotenv
from fastapi import APIRouter, Request, Response, Depends
from dotenv import load_dotenv
import os
from sqlalchemy import select, true
from source.database.db import get_session
from source.models.message import MessageRole, MessageStatus, Message
from source.models.user import User
from source.crud.messages import store_message, read_user_messages
from source.services.ai import ai_reformulates, ai_check_escalation, ai_response

import requests

router = APIRouter()

load_dotenv()

Version = os.getenv("META_API_VERSION")
Phone_Number_ID = os.getenv("BUSINESS_PHONE_ID")
META_API_TOKEN = os.getenv("META_API_TOKEN")

# TODO: IMPLEMENT FASTAPI BACKGROUND TASKS TO MAKE THIS MUCH MORE EFFICIENT
# TODO: FIX QUERIES AND METHODS TO ACTUALLY RETRIEVE THE COMPONENTS
@router.post("/whatsapp/webhook")
async def read_message(request: Request, session = Depends(get_session)) -> Response:
    json = await request.json()
    name = json["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
    body = json["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
    phone = json["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]

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
    url = f"https://graph.facebook.com/{Version}/{Phone_Number_ID}/messages"
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_str,
        "type": "text",
        "text": {
            "preview_url": true,
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

# @router.get("/whatsapp/response")
# async def assistant_response(user_id: int, session = Depends(get_session)) -> Response:
# return response.json()

