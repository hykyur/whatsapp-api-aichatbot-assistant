from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from source.models.message import MessageRole, MessageStatus, Message
from source.models.user import User


async def store_message(session: AsyncSession, name: str, phone: str, role: MessageRole, body: str, status: MessageStatus):
    user = session.exec(select(User).where(User.phone == phone)).first()

    if user is None:
        user = User(name=name, phone=phone)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    message = Message(
        user_id=user.id,
        role=role,
        body=body,
        status=status
    )

    session.add(message)
    await session.commit()
    await session.refresh(message)
    
async def read_user_messages(session: AsyncSession, phone: str) -> list[Message]:
    user = session.exec(select(User).where(User.phone == phone)).first()

    if user is None:
        return []

    results = session.exec(select(Message).where(Message.user_id == user.user_id))
    return results.all()


async def update_message_status(session: AsyncSession, message_id: int, status: MessageStatus):
    result = session.exec(select(Message).where(Message.id == message_id))
    message = result.first()

    if message is None:
        raise ValueError(f"Message {message_id} not found")

    message.status = status
    session.add(message)
    await session.commit()
    await session.refresh(message)
    