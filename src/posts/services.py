from openai.types.responses.responses_client_event_param import Conversation
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import openai
from openai import AsyncOpenAI

from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)  # for exponential backoff

from src.config import BUSINESS, OPEN_AI_API_KEY
from src.posts.utils import store_message, update_user_message_status, update_user_token, read_user_conversation
from src.models import MessageRole, MessageStatus, Message, User

from datetime import datetime

client = AsyncOpenAI(api_key=OPEN_AI_API_KEY)

def handle_openai_error(e: Exception) -> str:
    if isinstance(e, openai.RateLimitError):
        return "retry"
    if isinstance(e, openai.InternalServerError):
        return "retry"
    if isinstance(e, openai.APITimeoutError):
        return "retry"
    if isinstance(e, openai.APIConnectionError):
        return "check_network"
    if isinstance(e, openai.BadRequestError):
        return "fail_user"
    if isinstance(e, openai.AuthenticationError):
        return "fail_fast"
    if isinstance(e, openai.NotFoundError):
        return "fallback"
    raise e

def get_text(response):
    try:
        for item in response.output:
            for content in item.content:
                if hasattr(content, "text"):
                    return content.text
    except Exception:
        pass
    return ""

#TODO: IMPLEMENT EXCEPTION HANDELING LOGIC -> https://developers.openai.com/api/docs/guides/error-codes
#TODO: MAYBE DELEGATE THE LAST MESSAGE TO THE AI_RESPONSE SOMEHOW

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
async def ai_gen_token() -> Conversation:
    return await client.conversations.create()
# NOT SURE ABOUT THE TYPES HERE, DOCUMENTATION ISN'T CLEAR (IT'S TREATED AS A STR FOR THE CONVERSATION ARGUMENT ON THE CREATE RESPONSE BUT IT RETURNS "CONVERSATION" type.;

async def ai_conversation_token(session: AsyncSession, user_id: int) -> str | None:
    statement = await session.execute(select(User.openai_token).where(User.id == user_id))
    token = statement.scalar()
    return token

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
async def ai_check_escalation_fallback(session: AsyncSession, user_id: int):
    new_conversation_id = await ai_gen_token()
    await update_user_token(session, user_id, new_conversation_id)
    conversation = await read_user_conversation(session, user_id)

    parsed = []
    for message in conversation:
        parsed.append({"role": message.role, "content": message.body})

    try:
        response = await client.with_options(timeout = 100.0).responses.create(
            model="gpt-5.4-nano-2026-03-17",
            instructions="""
                    You evaluate whether the conversation needs escalation to a human.
                    You must answer ONLY with:
                    - needs escalation
                    - no escalation
                    No punctuation. No explanation.
                    This is the history of the conversation, since the conversation ID of your API expired, this conversation will replace it.
                    """,
            temperature=0,
            input=parsed,
            conversation = new_conversation_id
        )
        text = get_text(response).strip().lower()
        if text == "needs escalation":
            await update_user_message_status(session, user_id, MessageStatus.escalated)
        else:
            pass
    except Exception as e:
        action = handle_openai_error(e)
        if action == "retry":
            pass
        if action == "check_network":
            now = str(datetime.now())
            await store_message(session, "system", None, MessageRole.system, MessageStatus.sent, "Network error when trying to fallback check escalation in the OpenAI API, TIME:" + now)
            print("Issue connecting to OpenAI servers, check network configuration")
        if action == "fail_user":
            now = str(datetime.now())
            await store_message(session, "system", None, MessageRole.system, MessageStatus.sent, "Bad request when trying to fallback check escalation in the OpenAI API, TIME:" + now)
            print("Bad written request, try again.")
        if action == "fail_fast":
            now = str(datetime.now())
            await store_message(session, "system", None, MessageRole.system, MessageStatus.sent, "API Key invalid for the OpenAI API when tryign to fallback check escalation, TIME:" + now)
            print("Api key invalid, try configuring enviroment variables")



@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
async def ai_check_escalation_token(session: AsyncSession, user_id:int) -> bool:
    try:
        query = select(Message).where(Message.user_id == user_id).order_by(Message.created_at.desc())
        last_user_message: Message = session.scalars(query).first()
        response = await client.with_options(timeout = 100.0).responses.create(
            model="gpt-5.4-nano-2026-03-17",
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
            conversation = await ai_conversation_token(session, user_id)
        )
        text = get_text(response).strip().lower()
        if text == "needs escalation":
            await update_user_message_status(session, user_id, MessageStatus.escalated)
            return True
        else:
            return False

    except Exception as e:

        action = handle_openai_error(e)

        if action == "retry":
            pass

        if action == "check_network":
            now = str(datetime.now())

            await store_message(session, "system", None, MessageRole.system, MessageStatus.sent,
                                "Network error when trying to check escalation in the OpenAI API, TIME:" + now)

            print("Issue connecting to OpenAI servers, check network configuration")

        if action == "fail_user":
            now = str(datetime.now())

            await store_message(session, "system", None, MessageRole.system, MessageStatus.sent,
                                "Bad request when trying to check escalation in the OpenAI API, TIME:" + now)

            print("Bad written request, try again.")

        if action == "fail_fast":
            now = str(datetime.now())

            await store_message(session, "system", None, MessageRole.system, MessageStatus.sent,
                                "API Key invalid for the OpenAI API when trying to check escalation, TIME:" + now)

            print("Api key invalid, try configuring enviroment variables")


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
async def ai_reformulates(session: AsyncSession, user_id: int, sys_message: Message):
    phone = session.scalars(select(User.phone).where(User.id == user_id)).first()
    try:
        response = await client.with_options(timeout = 100.0).responses.create(
            model="gpt-5.4-nano-2026-03-17",
            instructions="""
            Rewrite the following message to be more formal and professional.
            Do not change its meaning.
            Only output the rewritten message.
            """,
            input=sys_message.body
        )
        text = get_text(response)
        await store_message(session, "LLM", phone, MessageRole.system, MessageStatus.ai_handled, text)

    except Exception as e:
        action = handle_openai_error(e)

        if action == "retry":
            pass

        if action == "check_network":
            now = str(datetime.now())
            await store_message(session, "system", None, MessageRole.system, MessageStatus.sent, "Network connection error when trying reformulation OpenAI API, TIME: " + now)
            print("Issue connecting to OpenAI servers, check network configuration")

        if action == "fail_user":
            now = str(datetime.now())
            await store_message(session, "system", None, MessageRole.system, MessageStatus.sent, "Bad request when trying reformulation OpenAI API, TIME: " + now)
            print("Bad written request, try again.")

        if action == "fail_fast":
            now = str(datetime.now())
            await store_message(session, "system", None, MessageRole.system, MessageStatus.sent, "API Key invalid, OpenAI API, TIME: " + now)
            print("Api key invalid, try configuring enviroment variables")

        if action == "fallback":
            await ai_check_escalation_fallback(session, user_id)
            pass


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
async def ai_response(session: AsyncSession, user_id: int) -> Message:
    phone = session.scalars(select(User.phone).where(User.id == user_id)).first()
    try:
        response = await client.with_options(timeout = 100.0).responses.create(
            model="gpt-5.4-nano-2026-03-17",
            instructions=f"""
            You are a professional customer support assistant for a {BUSINESS}.
            Answer clearly, politely, and concisely.
            Only output the reply to the client. Do not include explanations.
            """,
            temperature=0.3,
            input='',
            conversation = await ai_conversation_token(session, user_id)
        )
        text = get_text(response)
        await store_message(session, "LLM", phone, MessageRole.assistant, MessageStatus.ai_handled, text)
        return Message(user_id= user_id, role= MessageRole.assistant, status= MessageStatus.ai_handled, body= text)

    except Exception as e:
        action = handle_openai_error(e)

        if action == "retry":
            pass

        if action == "check_network":
            now = str(datetime.now())
            await store_message(session, "system", None, MessageRole.system, MessageStatus.sent, "Failed to connect when generating response in OpenAI API due to network error, TIME: " + now)
            print("Issue connecting to OpenAI servers, check network configuration")

        if action == "fail_user":
            now = str(datetime.now())
            await store_message(session, "system", None, MessageRole.system, MessageStatus.sent, "Bad request to OpenAI API when generating response, TIME: " +  now)
            print("Bad written request, try again.")

        if action == "fail_fast":
            now = str(datetime.now())
            await store_message(session, "system", None, MessageRole.system, MessageStatus.sent, "Invalid credentials error when generating response, TIME: " + now)
            print("Api key invalid, try configuring enviroment variables")

        if action == "fallback":
            await ai_check_escalation_fallback(session, user_id)
            pass
