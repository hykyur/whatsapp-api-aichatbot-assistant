from fastapi import FastAPI, Request, Response, HTTPException
import source.crud.messages
from db import init_db, get_session

init_db()

session = get_session()
app = FastAPI()

@app.post("/whatsapp/message")
async def read_message(request: Request) -> Response:
    json = request.json()
    name = json.get("name")
    phone = json.get("wa_id")
    body = json.get("body")

    await store_message(session, name, phone, MessageRole.user, MessageStatus.pending)

    return Response("200 OK, MESSAGE LOADED INTO DATABASE", media_type = 'text/plain')
