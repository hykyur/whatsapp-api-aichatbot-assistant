from src.celery.app import app

from sqlalchemy import select
from src.database import async_session

from src.posts.services import ai_check_escalation, ai_reformulates, ai_response

from src.posts.utils import store_message, read_user_messages
from src.models import Message, User, MessageRole, MessageStatus

from src.config import META_API_VERSION, META_API_TOKEN, BUSINESS_PHONE_ID

import requests

from asgiref.sync import async_to_sync

@app.task
def add_message(name: str, phone: str, body: str) -> str:
    # open async session
    def _run():
        async def _inner():
            async with async_session() as session:
                await store_message(session, name, phone,
                                    MessageRole.user, MessageStatus.pending, body)
        return async_to_sync(_inner)()

    _run()
    return phone

@app.task
def check_escalation(phone: str) -> int | None:
    def _run():
        async def _inner():
            async with async_session() as session:
                result = await session.execute(select(User.id).where(User.phone == phone))
                user_id: int | None = result.scalar()

                if user_id is None:
                    print("user id not found") # placeholder, write an exception later
                    return None

                conversation = await read_user_messages(session, user_id)
                await ai_check_escalation(session, user_id, conversation)
                return user_id

        return async_to_sync(_inner)()

    return _run()

@app.task
def reformulate_drafts(user_id: int) -> int | None:
    def _run():
        async def _inner():
            async with async_session() as session:
                conversation = await read_user_messages(session, user_id)
                for message in conversation:
                    if message.status == MessageStatus.drafting:
                        await ai_reformulates(session, message)
                return user_id

        return async_to_sync(_inner)()

    return _run()
    '''TODO: 
    TRY TO DITCH THE FOR LOOP FOR EFFICIENCY 
    -> REWRITING THE MESSAGE ON THE MOMENT OF WORKER INPUT
    -> NEEDS THE LOGIC FOR THAT BEFOREHAND '''


@app.task
def get_response(user_id: int) -> tuple[int, int]:
    def _run():
        async def _inner():
            async with async_session() as session:
                conversation = await read_user_messages(session, user_id)
                msg = await ai_response(session, user_id, conversation)
                # assuming ai_response stores the message and returns a Message with .id
                return msg.id, user_id

        return async_to_sync(_inner)()

    return _run()

@app.task
def send_response(message_id: int, user_id: int):
    def _run():
        async def _inner():
            async with async_session() as session:
                reply_res = await session.execute(
                    select(Message.body).where(Message.id == message_id)
                )
                reply = reply_res.scalar()

                phone_res = await session.execute(
                    select(User.phone).where(User.id == user_id)
                )
                phone = phone_res.scalar()

            # outside async with: session closed, we just use reply/phone
            url = f"https://graph.facebook.com/{META_API_VERSION}/{BUSINESS_PHONE_ID}/messages"

            data = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": phone,
                "type": "text",
                "text": {"body": reply},
            }

            headers = {
                "Authorization": f"Bearer {META_API_TOKEN}",
                "Content-Type": "application/json",
            }

            requests.post(url, json=data, headers=headers)

        return async_to_sync(_inner)()

    _run()

