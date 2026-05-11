import os
import re
import resend
from fastapi import FastAPI, Request
from openai import OpenAI

app = FastAPI()

api_key = os.getenv("GROQ_API_KEY") or ""
resend.api_key = os.getenv("RESEND_API_KEY") or ""
GMAIL_USER = os.getenv("GMAIL_USER") or ""

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=api_key
) if api_key else None

with open("policy.txt", "r") as f:
    rules = f.read()

@app.get("/")
def root():
    return {"status": "Agent is running"}

@app.post("/webhook")
async def crisp_webhook(request: Request):
    data = await request.json()
    print("CRISP DATA:", data)
    return {"status": "ok"}
