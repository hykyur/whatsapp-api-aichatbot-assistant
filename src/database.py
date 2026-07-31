from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import MetaData

import ssl

from src.models import Base
from src.config import config


POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}
metadata = MetaData(naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION)

DATABASE_URL = str(config.DATABASE_URL)

# PostgreSQL jit is disabled due to asyncpg driver problems with enum types, see: https://docs.sqlalchemy.org/en/14/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.asyncpg
# set an additional argument echo=True to print everything for debugging purposes
# both comments are relative to create_async_engine

ssl_context = ssl.create_default_context()
# https://docs.sqlalchemy.org/en/20/core/pooling.html#disconnect-handling-pessimistic
engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"server_settings": {"jit": "off"}, "ssl": ssl_context}) #type:ignore
async_session = async_sessionmaker(engine, expire_on_commit=False) #autoflush is false by default in sqlalchemy 2.0

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all) #type:ignore

async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        yield session