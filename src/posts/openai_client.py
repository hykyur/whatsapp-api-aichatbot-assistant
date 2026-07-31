import openai
from openai import AsyncOpenAI
from src.config import config

from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential, retry_if_exception_type,
)  # for exponential backoff

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User

OPENAI_API_KEY = config.OPENAI_API_KEY
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

RETRYABLE_OPENAI_ERRORS = (
    openai.RateLimitError,
    openai.APITimeoutError,
    openai.InternalServerError,
    openai.ConflictError,
)

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3), retry=retry_if_exception_type(RETRYABLE_OPENAI_ERRORS), reraise=True)
async def _call_responses(**kwargs) -> str:
    response = await client.with_options(timeout=100.0).responses.create(**kwargs)
    return get_text(response)

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
