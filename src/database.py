from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

import ssl

from src.models import Base
from src.config import DATABASE_URL

# PostgreSQL jit is disabled due to asyncpg driver problems with enum types, see: https://docs.sqlalchemy.org/en/14/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.asyncpg
# set an additional argument echo=True to print everything for debugging purposes
# both comments are relative to create_async_engine

ssl_context = ssl.create_default_context()

engine = create_async_engine(DATABASE_URL, connect_args={"server_settings": {"jit": "off"}, "ssl": ssl_context}) #type:ignore
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all) #type:ignore

async def get_session(): #type:ignore
    async with async_session() as session:
        yield session #type:ignore