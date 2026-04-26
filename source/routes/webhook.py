from fastapi import FastAPI, Request, Response, HTTPException
app = FastAPI()

@app.post("/whatsapp/message")
async def read_message(request: Request):
    return