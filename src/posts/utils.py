from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, MessageRole, MessageStatus, Message
from src.config import config
from openai import AsyncOpenAI

OPENAI_API_KEY = config.OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def store_message(session: AsyncSession, name: str, phone: str | None, bsuid:str | None, role: MessageRole, status: MessageStatus, body: str):
    stmt = select(User).where(User.bsuid == bsuid)
    user = (await session.scalars(stmt)).first()
    if user is None:
        openai_token = None
        if role == MessageRole.user:
            conv = await client.conversations.create()
            openai_token = conv.id

        user = User(name=name, phone=phone, openai_token=openai_token, bsuid=bsuid)
        session.add(user)
        await session.commit()

    message = Message(user_id=user.id, role=role, status=status, body=body)
    session.add(message)
    await session.commit()

async def store_message_user_id(session: AsyncSession, user_id: int, role: MessageRole, status: MessageStatus, body: str):
    message = Message(user_id = user_id, role=role, status=status, body=body)
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
        .where(Message.status == MessageStatus.drafting)
    )

    return (await session.scalars(stmt)).all()

async def update_message_status(session: AsyncSession, message_id: int, status: MessageStatus):
    await session.execute(update(Message).where(Message.id == message_id).where(Message.status == MessageStatus.sent).values(status=status))

async def update_user_message_status(session: AsyncSession, user_id: int, status: MessageStatus):
    await session.execute(update(Message).where(Message.user_id == user_id).where(Message.status == MessageStatus.sent).values(status=status))

async def update_user_token(session: AsyncSession, user_id: int, token: str):
    await session.execute(update(User).where(User.id == user_id).values(openai_token=token))
async def update_user_bsuid(session: AsyncSession, user_id: int, bsuid:str):
    await session.execute(update(User).where(User.id == user_id).values(bsuid=bsuid))