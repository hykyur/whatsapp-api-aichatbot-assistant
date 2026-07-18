from sqlalchemy import select, inspect
from sqlalchemy.orm import Mapped
from src.queues.broker import broker
from src.database import async_session
from src.posts.services import ai_check_escalation_token, ai_response
from src.posts.utils import store_message
from src.models import Message, User, MessageRole, MessageStatus
from src.config import config
import httpx

# .env variables
META_API_VERSION = config.META_API_VERSION
BUSINESS_PHONE_ID = config.BUSINESS_PHONE_ID
META_API_TOKEN = config.META_API_TOKEN

#TODO: IN CASE THAT THE DB DOESN'T HAVE THE TABLES, CREATE THEM AGAIN AT HAND.
@broker.task
async def add_message(name: str, phone: str, bsuid:str, body: str) -> str:
    async with async_session() as session:
        await store_message(session, name, phone, bsuid,
                            MessageRole.user, MessageStatus.pending, body)
        await session.commit()
    return bsuid

@broker.task
async def check_escalation(bsuid: str) -> int:
    async with async_session() as session:
        result = await session.execute(select(User.id).where(User.bsuid == bsuid))
        user_id: int = result.scalar()
        await ai_check_escalation_token(session, user_id)
        return user_id




'''@broker.task
def reformulate_drafts(user_id: int) -> int:
    async with async_session() as session:
        conversation = await read_user_drafts(session, user_id)
        for message in conversation:
            await ai_reformulates(session, user_id, message)
            await update_message_status(session, message.id, MessageStatus.ai_handled)
        return user_id
'''


@broker.task
async def get_response(user_id: int) -> tuple[Mapped[int], int]:
    async with async_session() as session:
        msg = await ai_response(session, user_id)
        # assuming ai_response stores the message and returns a Message with .id
        return msg.id, user_id

@broker.task
async def send_response(payload: tuple[int, int]):
    message_id, user_id = payload
    async with async_session() as session:
        reply_res = await session.execute(
            select(Message.body).where(Message.id == message_id)
        )
        reply = reply_res.scalar()

        info_res = await session.execute(
            select(User.phone, User.bsuid).where(User.id == user_id)
        )
        info = info_res.first()
        if info is None:
            print("No user found for user_id=%s", user_id)
            return

        phone = info[0]
        bsuid = info[1]

    # outside async with: session closed, we just use reply/phone/bsuid
    url = f"https://graph.facebook.com/{META_API_VERSION}/{BUSINESS_PHONE_ID}/messages"

    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone,
        #"recipient": bsuid,
        "type": "text",
        "text": {"body": reply},
    }

    headers = {
        "Authorization": f"Bearer {META_API_TOKEN}",
        "Content-Type": "application/json",
    }
    transport = httpx.AsyncHTTPTransport(retries=1) # https://www.python-httpx.org/async/#explicit-transport-instances
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.post(url, json=data, headers=headers)
        print(response.status_code, response.text)