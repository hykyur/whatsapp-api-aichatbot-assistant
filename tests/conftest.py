import os

from _pytest import monkeypatch

os.environ["ENVIRONMENT"] = "pytest"

from collections.abc import AsyncGenerator
import pytest
from httpx import  ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
import taskiq_fastapi

from src.queues.broker import broker
from src.models import Base
from src.database import init_db
import src.posts.openai_client as services
import src.posts.router as router
import src.posts.utils as utils
from main import app
import time

pytest_plugins = ["anyio"]

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(autouse=True)
def mock_openai(monkeypatch):

    async def mock_call_responses(**kwargs):
        instructions = kwargs.get("instructions", "").lower()

        if "needs escalation" in instructions:
            return "no escalation"

        if "rewrite the following message" in instructions:
            return "This is the rewritten message."

        return "This is a mock AI response."

    async def mock_create_conversation_token():
        return "mock-conversation-token"

    monkeypatch.setattr(
        services,
        "_call_responses",
        mock_call_responses,
    )

    monkeypatch.setattr(
        services,
        "create_conversation_token",
        mock_create_conversation_token,
    )

    monkeypatch.setattr(
        utils,
        "create_conversation_token",
        mock_create_conversation_token,
    )

@pytest.fixture(autouse=True)
def mock_verify_webhook(monkeypatch):
    def mock_verify_signature(*args, **kwargs):
        return True

    monkeypatch.setattr(
        router,
        "verify_signature",
        mock_verify_signature,
    )

@pytest.fixture(scope="session")
def test_engine():
    engine = create_async_engine(
        os.environ["DATABASE_URL"],
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args={"server_settings": {"jit": "off"}, "statement_cache_size": 0, "ssl":"disable"},
    )
    return engine

@pytest.fixture(scope="session")
async def setup_database(test_engine):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()

@pytest.fixture
async def db_session(test_engine, setup_database) -> AsyncGenerator[AsyncSession]:
    conn = await test_engine.connect()
    trans = await conn.begin()
    test_async_session = async_sessionmaker(
        bind=conn, class_=AsyncSession,
        expire_on_commit=False, join_transaction_mode="create_savepoint",
    )
    async with test_async_session() as session:
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
            await conn.close()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    async def override_init_db():
        yield db_session

    app.dependency_overrides[init_db] = override_init_db

    taskiq_fastapi.init(broker, "main:app")
    taskiq_fastapi.populate_dependency_context(broker, app)

    for k, v in app.dependency_overrides.items():
        broker.dependency_overrides[k] = v

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()

def make_text_message(from_="16315551234", message_id=None, timestamp=None, body="Hello, world!"):
    return {
        "from": from_,
        "id": message_id or "wamid.HBgLMTYzMTU1NTEyMzQVAgASGBQzQTdCNzc2",
        "timestamp": timestamp or str(int(time.time())),
        "type": "text",
        "text": {"body": body},
    }


def make_contact(wa_id="16315551234", bsuid="TT-3U90KFISDKAVIOJDO", name="Test User"):
    return {
        "profile": {"name": name},
        "wa_id": wa_id,
        "user_id": bsuid,
    }


def make_webhook_payload(
    field="messages",
    phone_number_id="123456789012345",
    display_phone_number="16315551234",
    messages=None,
    contacts=None,
    entry_id="0",
    messaging_product="whatsapp",
    object_type="whatsapp_business_account",
):
    value = {
        "messaging_product": messaging_product,
        "metadata": {
            "display_phone_number": display_phone_number,
            "phone_number_id": phone_number_id,
        },
    }
    if contacts is not None:
        value["contacts"] = contacts
    if messages is not None:
        value["messages"] = messages
    return {
        "object": object_type,
        "entry": [{"id": entry_id, "changes": [{"value": value, "field": field}]}],
    }


@pytest.fixture
def webhook_payload_factory():
    return make_webhook_payload


@pytest.fixture
def text_message_factory():
    return make_text_message


@pytest.fixture
def contact_factory():
    return make_contact