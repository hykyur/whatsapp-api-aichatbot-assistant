from sqlalchemy import select, update, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, MessageRole, MessageStatus, Message
from src.posts.openai_client import create_conversation_token

async def store_message(session: AsyncSession, name: str, phone: str | None, bsuid: str | None, wamid: str | None,
                        role: MessageRole, status: MessageStatus, body: str) -> bool:
    """Store a message and return True only when it was newly inserted."""
    if wamid is not None:
        existing_message = await session.scalar(
            select(Message.id).where(Message.wamid == wamid)
        )
        if existing_message is not None:
            return False

    user_id = None
    identity_filter = None
    if bsuid is not None:
        identity_filter = User.bsuid == bsuid
    elif phone is not None:
        identity_filter = User.phone == phone

    if identity_filter is not None:
        user_id = await session.scalar(
            select(User.id).where(identity_filter)
        )

    if user_id is None:
        openai_token = None
        if role == MessageRole.user:
            openai_token = await create_conversation_token()

        user_stmt = (
            insert(User)
            .values(
                name=name,
                phone=phone,
                openai_token=openai_token,
                bsuid=bsuid,
            )
            .on_conflict_do_nothing()
            .returning(User.id)
        )

        user_id = await session.scalar(user_stmt)

        if user_id is None and identity_filter is not None:
            user_id = await session.scalar(
                select(User.id).where(identity_filter)
            )

        if user_id is None:
            raise RuntimeError("User insert conflicted but existing user was not found")

    message_stmt = (
        insert(Message)
        .values(
            user_id=user_id,
            wamid=wamid,
            role=role,
            status=status,
            body=body,
        )
        .on_conflict_do_nothing()
        .returning(Message.id)
    )
    message_id = await session.scalar(message_stmt)
    if message_id is None:
        return False

    await session.commit()
    return True

async def store_message_user_id(session: AsyncSession, user_id: int, wamid: str, role: MessageRole, status: MessageStatus, body: str):
    message = Message(user_id=user_id,wamid=wamid, role=role, status=status, body=body)
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message

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
    await session.execute(update(Message).where(Message.id == message_id).values(status=status))
    await session.commit()

async def update_user_message_status(session: AsyncSession, user_id: int, status: MessageStatus):
    await session.execute(update(Message)
                          .where(Message.user_id == user_id)
                          .where(Message.status == MessageStatus.pending)
                          .where(or_(Message.role == MessageRole.user, Message.role == MessageRole.assistant))
                          .values(status=status)
                          )
    await session.commit()

async def update_user_token(session: AsyncSession, user_id: int, token: str):
    await session.execute(update(User)
                          .where(User.id == user_id)
                          .values(openai_token=token)
                          )
    await session.commit()

async def update_user_bsuid(session: AsyncSession, user_id: int, bsuid:str):
    await session.execute(update(User).where(User.id == user_id).values(bsuid=bsuid))
    await session.commit()
