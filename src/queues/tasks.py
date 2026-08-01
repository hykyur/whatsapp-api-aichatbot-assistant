from typing import Annotated, TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import TaskiqDepends

from src.posts.exceptions import handle_httpx_exception
from src.posts.services import ai_response
from src.posts.utils import store_message, update_message_status
from src.queues.broker import broker
from src.database import get_session
from src.models import Message, User, MessageRole, MessageStatus
from src.config import config
import httpx

# .env variables
META_API_VERSION = config.META_API_VERSION
BUSINESS_PHONE_ID = config.BUSINESS_PHONE_ID
META_API_TOKEN = config.META_API_TOKEN


class MessageContext(TypedDict, total=False):
    """
    Carried through the whole pipeline instead of positional tuples,
    so every task reads named fields instead of guessing tuple order.
    Plain dict (not a dataclass) so it stays trivially serializable
    regardless of which result backend/serializer taskiq is using.
    """
    bsuid: str
    flag_success: bool
    user_id: int
    message_id: int



@broker.task
async def add_message(
    name: str,
    phone: str,
    bsuid: str,
    wamid: str,
    body: str,
    session: Annotated[AsyncSession, TaskiqDepends(get_session)],
) -> MessageContext:
    flag_successs = await store_message(
        session=session,
        name=name,
        phone=phone,
        bsuid=bsuid,
        wamid=wamid,
        role=MessageRole.user,
        status=MessageStatus.pending,
        body=body,
    )
    return {"bsuid": bsuid, "flag_success": flag_successs}


@broker.task
async def get_response(
    ctx: MessageContext,
    session: Annotated[AsyncSession, TaskiqDepends(get_session)],
) -> MessageContext:
    if not ctx["flag_success"]:
        # Nothing to do — don't burn an AI call regenerating a response
        # for a message we've already answered.
        print(f"Duplicate webhook for bsuid={ctx['bsuid']}, skipping AI response")
        return ctx

    result = await session.execute(select(User.id).where(User.bsuid == ctx["bsuid"]))
    user_id = result.scalar()

    if user_id is None:
        print(f"No user found for bsuid={ctx['bsuid']}, skipping")
        # Treat "nothing we can do" the same as duplicate: downstream steps no-op.
        return {**ctx, "flag_success": False}

    msg = await ai_response(session, user_id)
    await session.commit()

    return {**ctx, "user_id": user_id, "message_id": msg.id}


@broker.task
async def send_response(
    ctx: MessageContext,
    session: Annotated[AsyncSession, TaskiqDepends(get_session)],
) -> None:
    if not ctx["flag_success"]:
        print(f"Duplicate webhook for bsuid={ctx['bsuid']}, skipping send")
        return

    message_id = ctx["message_id"]

    stmt = (
        select(Message.body, User.phone, User.bsuid)
        .join(User, Message.user_id == User.id)
        .where(Message.id == message_id)
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        print(f"No message/user found for message_id={message_id}")
        return

    reply, phone, bsuid = row

    url = f"https://graph.facebook.com/{META_API_VERSION}/{BUSINESS_PHONE_ID}/messages"
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone,
        "recipient": bsuid,
        "type": "text",
        "text": {"body": reply},
    }
    headers = {
        "Authorization": f"Bearer {META_API_TOKEN}",
        "Content-Type": "application/json",
    }
    # https://www.python-httpx.org/async/#explicit-transport-instances
    transport = httpx.AsyncHTTPTransport(retries=1)
    try:
        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.post(url, json=data, headers=headers)
            print(response.status_code, response.text)
            response.raise_for_status()
        await update_message_status(session, message_id, MessageStatus.sent)
    except Exception as e:
        handle_httpx_exception(e, context="POST /whatsapp/webhook")