from fastapi import FastAPI, Request, Response

from src.posts.router import router as posts_router
from contextlib import asynccontextmanager
from src.database import init_db
from src.config import config

META_VERIFY_TOKEN = config.META_VERIFY_TOKEN

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(posts_router)

@app.get("/")
async def root()-> Response:
    return Response("ok",media_type='text/plain')

@app.get("/whatsapp/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == META_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain", status_code=200)

    return Response(status_code=403)

