import pytest
from sqlalchemy import select

from src.models import User, Message, MessageRole, MessageStatus
@pytest.mark.anyio
async def test_store_webhook(client, db_session, webhook_payload_factory, text_message_factory, contact_factory, mock_openai, mock_verify_webhook):
    payload = webhook_payload_factory(
        messages=[text_message_factory(from_="+999999999", body="test_body")],
        contacts=[contact_factory(wa_id="+999999999", bsuid="TT-3U90KFISDKAVIOJDO", name="test_name")],
    )
    response = await client.post("/whatsapp/webhook", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert "task_id" in data
    assert "enqueued_at" in data

    msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    contact = payload["entry"][0]["changes"][0]["value"]["contacts"][0]

    assert data["content"] == msg["text"]["body"]
    assert data["user_phone"] == msg["from"]
    assert data["user_bsuid"] == contact["user_id"]

    result = await db_session.execute(
        select(Message, User).join(User, Message.user_id == User.id).where(User.phone == msg["from"]).where(Message.role == MessageRole.user)
    )
    message, user = result.one()

    assert message is not None, "Expected message row was not found in the test database"
    assert user is not None, "Expected user row was not found in the test database"
    assert message.body == msg["text"]["body"]
    assert message.user_id == user.id
    assert message.role == MessageRole.user
    assert message.status == MessageStatus.pending
    assert user.name == contact["profile"]["name"]
    assert user.phone == (contact["wa_id"] or None)
    assert user.bsuid == (contact["user_id"] or None)
    assert user.openai_token is not None, "Expected openai token was not found in the user row"

# @pytest.mark.anyio
# async def test_bad_request_webhook(client, webhook_payload_factory, text_message_factory, contact_factory):
#     payload = webhook_payload_factory(
#         messages=[text_message_factory(from_=None, body=None)],
#         contacts=[contact_factory(wa_id=None, name="test_name")],
#     )
#     response = await client.post("/whatsapp/webhook", json=payload)
#     assert response.status_code == 400