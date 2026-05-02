from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from dotenv import load_dotenv
import os

from openai import OpenAI

import source.crud.messages
from source.models.message import MessageRole, Message
from db import init_db, get_session

load_dotenv()

openai_token = os.environ("OPEN_AI_KEY")
business = os.environ("BUSINESS")
client = OpenAI()
init_db()

# async def ai_check_escalation():

# async def ai_reformulates():

async def ai_response(session:AsyncSession, conversation:list[Message]):
    parsed = []
    for message in conversation:
        parsed.append({"role":message.role, "content":message.body})

    parsed.insert(0, {"role":"developer", "content":"You are answering a client on a {business} business, here is the current history (could be the customer first message):"})
    response = client.responses.create(
        model = "gpt-5.4-nano-2026-03-17",
        reasoning = {"effort":"low"},
        input = parsed
    )

#TODO: response is a json that needs to be parsed into the meta api json format to send back a response to the user through the api get route (also to be done)

