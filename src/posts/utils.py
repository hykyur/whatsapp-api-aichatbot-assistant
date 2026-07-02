from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User, MessageRole, MessageStatus, Message
from src.config import OPEN_AI_API_KEY
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key= OPEN_AI_API_KEY)

async def store_message(session: AsyncSession, name: str, phone: str | None, role: MessageRole, status: MessageStatus,
                        body: str):
    result = await session.execute(select(User).where(User.phone == phone))
    user = result.scalars().first()
    if user is None:
        if role == MessageRole.user:
            openai_token = (await client.conversations.create()).id
            user = User(name=name, phone=phone, openai_token = openai_token)
            session.add(user)
            await session.flush()
        else:
            user = User(name=name, phone=phone, openai_token = None)
            session.add(user)
            await session.flush()

    message = Message(user_id=user.id, role=role, status=status, body=body)
    session.add(message)


async def read_user_conversation(session: AsyncSession, user_id: int) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.user_id == user_id)
        .where(or_(Message.role == MessageRole.user, Message.role == MessageRole.assistant))
        .order_by(Message.created_at)
    )

    return (await session.scalars(stmt)).all()

async def read_user_drafts(session: AsyncSession, user_id:int) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.user_id == user_id)
        .where(Message.status == "drafting")
    )

    return (await session.scalars(stmt)).all()

async def update_message_status(session: AsyncSession, message_id: int, status: MessageStatus):
    await session.execute(update(Message).where(Message.id == message_id).values(status=status))

async def update_user_message_status(session: AsyncSession, user_id: int, status: MessageStatus):
    await session.execute(update(Message).where(Message.user_id == user_id).values(status=status))

async def update_user_token(session: AsyncSession, user_id: int, token: str):
    await session.execute(update(User).where(User.id == user_id).values(openai_token=token))