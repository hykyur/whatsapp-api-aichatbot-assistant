from sqlmodel import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from source.models.message import MessageRole, MessageStatus, Message
from source.models.user import User

from typing import cast

async def store_message(session: AsyncSession, name: str, phone: str | None, role: MessageRole, status: MessageStatus,
                        body: str):
    result = await session.execute(select(User).where(phone == User.phone))
    user = result.scalars().first()
    if user is None:
        user = User(name=name, phone=phone)
        session.add(user)
        await session.flush()

    message = Message(user_id=user.id, role=role, status=status, body=body)
    session.add(message)



async def read_user_messages(session: AsyncSession, user_id: int) -> list[Message]:
    result = await session.execute(select(Message).where(user_id == Message.user_id).order_by(Message.created_at))
    return cast(list[Message], result.scalars().all())


async def update_message_status(session: AsyncSession, message_id: int, status: MessageStatus):
    await session.execute(update(Message).where(Message.id == message_id).values(status=status))


async def update_user_message_status(session: AsyncSession, user_id: int, status: MessageStatus):
    await session.execute(update(Message).where(Message.user_id == user_id).values(status=status))
