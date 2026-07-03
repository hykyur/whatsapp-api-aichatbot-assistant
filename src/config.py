import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
BUSINESS = os.getenv("BUSINESS")
OPEN_AI_API_KEY = os.getenv("OPENAI_API_KEY")
META_API_VERSION = os.getenv("META_API_VERSION")
META_API_TOKEN = os.getenv("META_API_TOKEN")
META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN")
BUSINESS_PHONE_ID = os.getenv("BUSINESS_PHONE_ID")
BROKER_URL = os.getenv("BROKER_URL")
LLM_MODEL = os.getenv("LLM_MODEL")
