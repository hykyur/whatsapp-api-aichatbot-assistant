from dotenv import load_dotenv
import os
from openai import OpenAI
import source.crud.messages
from db import init_db, get_session

load_dotenv()

openai_token = os.environ("OPEN_AI_KEY")
client = OpenAI()
init_db()

session = get_session()

