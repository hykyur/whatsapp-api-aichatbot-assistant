from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
import os

from openai import AsyncOpenAI

from source.crud.messages import store_message, update_user_message_status
from source.models.message import MessageRole, MessageStatus, Message

load_dotenv()
business = os.getenv("BUSINESS")
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_text(response):
    try:
        for item in response.output:
            for content in item.content:
                if hasattr(content, "text"):
                    return content.text
    except Exception:
        pass
    return ""

#TODO: MAKE A HELPER FUNCTION FOR PARSING

async def ai_check_escalation(session: AsyncSession, user_id:int, conversation: list[Message]):
    parsed = []
    for message in conversation:
        parsed.append({"role": message.role, "content": message.body})

    try:
        response = await client.responses.create(
            model="gpt-5.4-nano-2026-03-17",
            instructions="""
            You evaluate whether the conversation needs escalation to a human.

            You must answer ONLY with:
            - needs escalation
            - no escalation

            No punctuation. No explanation.
            """,
            temperature=0,
            input=parsed
        )
        text = get_text(response).strip().lower()
        if text == "needs escalation":
            await update_user_message_status(session, user_id, MessageStatus.escalated)
        else:
            pass
    except Exception:
        pass

async def ai_reformulates(session: AsyncSession, sys_message: Message):
    try:
        response = await client.responses.create(
            model="gpt-5.4-nano-2026-03-17",
            instructions="""
            Rewrite the following message to be more formal and professional.
            Do not change its meaning.
            Only output the rewritten message.
            """,
            input=sys_message.body
        )
        text = get_text(response)
        await store_message(session, "LLM", None, MessageRole.system, MessageStatus.ai_handled, text)
    except Exception:
        pass


async def ai_response(session: AsyncSession, user_id: int, conversation: list[Message]) -> Message:
    parsed = []
    for message in conversation:
        parsed.append({"role": message.role, "content": message.body})

    try:
        response = await client.responses.create(
            model="gpt-5.4-nano-2026-03-17",
            instructions=f"""
            You are a professional customer support assistant for a {business}.
            Answer clearly, politely, and concisely.

            Only output the reply to the client. Do not include explanations.
            """,
            temperature=0.3,
            input=parsed
        )
        text = get_text(response)
        await store_message(session, "LLM", None, MessageRole.assistant, MessageStatus.ai_handled, text)
        return Message(user_id= user_id, role= MessageRole.assistant,status= MessageStatus.ai_handled,body= text)
    except Exception:
        await store_message(session, "LLM", None, MessageRole.developer, MessageStatus.escalated, "Weren't able to full fill the request.")
        return Message(user_id= user_id, role=MessageRole.developer, status=MessageStatus.escalated, body="Weren't able to full fill the request.")
#TODO: maybe handle the phase parameter on the LLM calls (not sure if it's necessary)
