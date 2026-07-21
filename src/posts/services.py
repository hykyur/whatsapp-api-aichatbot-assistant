from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import openai
from openai import AsyncOpenAI

from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential, retry_if_exception_type,
)  # for exponential backoff

from src.config import config
from src.posts.utils import store_message, store_message_user_id, update_user_message_status, update_user_token, read_user_conversation
from src.models import MessageRole, MessageStatus, Message, User
from src.posts.exceptions import handle_openai_error, OpenAIAction
from src.posts.constants import LLM_MODEL
from datetime import datetime

#TODO: CHANGE THE MESSAGE STATUS BASED ON WHAT IS HAPPENING WITH THE MESSAGES

RETRYABLE_OPENAI_ERRORS = (
    openai.RateLimitError,
    openai.APITimeoutError,
    openai.InternalServerError,
    openai.ConflictError,
)

OPENAI_API_KEY = config.OPENAI_API_KEY
BUSINESS = config.BUSINESS

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

def get_text(response):
    try:
        for item in response.output:
            for content in item.content:
                if hasattr(content, "text"):
                    return content.text
    except Exception:
        pass
    return ""

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3), retry=retry_if_exception_type(RETRYABLE_OPENAI_ERRORS), reraise=True)
async def _call_responses(**kwargs) -> str:
    response = await client.with_options(timeout=100.0).responses.create(**kwargs)
    return get_text(response)

async def log_raise(session, e):
    decision = handle_openai_error(e)
    now = datetime.now().strftime('%a %d %b %Y, %I:%M%p')

    await store_message(session, "system", None, bsuid="system", role=MessageRole.system, status=MessageStatus.sent,
                        body=f"{decision.message}, TIME: {now}")

    if decision.action == OpenAIAction.CHECK_NETWORK:
        raise RuntimeError("OpenAI network error") from e

    if decision.action == OpenAIAction.FAIL_USER:
        raise ValueError("Invalid request sent to OpenAI") from e

    if decision.action == OpenAIAction.FAIL_FAST:
        raise RuntimeError("OpenAI credentials are invalid") from e

    if decision.action == OpenAIAction.FORBIDDEN:
        raise PermissionError("OpenAI access denied") from e

    if decision.action == OpenAIAction.RECREATE_RESOURCE:
        raise LookupError("OpenAI resource not found") from e

    raise

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3), retry=retry_if_exception_type(RETRYABLE_OPENAI_ERRORS), reraise=True)
async def create_conversation_token() -> str:
    conversation = await client.conversations.create()
    return conversation.id

async def get_conversation_token(session: AsyncSession, user_id: int) -> str | None:
    statement = await session.execute(select(User.openai_token).where(User.id == user_id))
    conversation = statement.scalar()
    if conversation is None:
        return None
    else:
        return conversation

async def ai_check_escalation_fallback(session: AsyncSession, user_id: int):
    new_conversation_id = await create_conversation_token()
    await update_user_token(session, user_id, new_conversation_id)
    conversation = await read_user_conversation(session, user_id)

    parsed = []
    for message in conversation:
        parsed.append({"role": message.role, "content": message.body})

    try:
        text = await _call_responses(
            model=LLM_MODEL,
            instructions="You evaluate whether the conversation needs escalation to a human. ...",
            temperature=0,
            input=parsed,
            conversation=new_conversation_id,
        )
        if text.strip().lower() == "needs escalation":
            await update_user_message_status(session, user_id, MessageStatus.escalated)
    except Exception as e:
        await log_raise(session, e)


async def ai_check_escalation_token(session: AsyncSession, user_id: int) -> bool | None:
    try:
        query = (select(Message)
                 .where(Message.user_id == user_id)
                 .where(Message.role == MessageRole.user)
                 .order_by(Message.created_at.desc()))
        last_user_message = (await session.scalars(query)).first()

        text = await _call_responses(
            model=LLM_MODEL,
            instructions="""
            You evaluate whether the conversation needs escalation to a human.
            You must answer ONLY with:
            - needs escalation
            - no escalation
            No punctuation. No explanation.
            The following input is the latest user message.
            """,
            temperature=0,
            input=last_user_message.body,
            conversation=await get_conversation_token(session, user_id),
        )
        if text.strip().lower() == "needs escalation":
            await update_user_message_status(session, user_id, MessageStatus.escalated)
            return True
        return False
    except Exception as e:
        await log_raise(session, e)

async def ai_reformulates(session: AsyncSession, user_id: int, sys_message: Message):
    try:
        text = await _call_responses(
            model=LLM_MODEL,
            instructions="""
            Rewrite the following message to be more formal and professional.
            Do not change its meaning.
            Only output the rewritten message.
            """,
            input=sys_message.body,
        )
        msg = Message(user_id=user_id, role=MessageRole.assistant,
                      status=MessageStatus.ai_handled, body=text)
        session.add(msg)
        await session.flush()
    except Exception as e:
        await log_raise(session, e)

async def ai_response(session: AsyncSession, user_id: int) -> Message | None:
    stmt = (
        select(Message, User.openai_token)
        .join(User, Message.user_id == User.id)
        .where(Message.user_id == user_id)
        .where(Message.role == MessageRole.user)
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.first()
    last_msg, conv_token = row if row else (None, None)
    try:
        text = await _call_responses(
            model=LLM_MODEL,
            instructions=f"""
            You are a professional customer support assistant for a {BUSINESS}.
            Answer clearly, politely, and concisely.
            Only output the reply to the client. Do not include explanations.
            """,
            temperature=0.3,
            input=last_msg.body if last_msg else '',
            conversation = conv_token
        )
        msg = Message(user_id=user_id, role=MessageRole.assistant, status=MessageStatus.ai_handled, body=text)
        session.add(msg)
        await session.flush()
        return msg
    except Exception as e:
        await log_raise(session, e)