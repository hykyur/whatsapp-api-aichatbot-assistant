from sqlmodel import SQLModel, create_async_engine, AsyncEngine
from dotenv import load_dotenv
import os
from .message import MessageRole, MessageStatus, Message
from .user import User

engine = create_async_engine(DATABASE_URL, echo=True)

SQLModel.metadata.create_all(engine)