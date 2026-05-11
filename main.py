import os
import re
import resend
import requests
from fastapi import FastAPI, Request
from openai import OpenAI

app = FastAPI()

api_key = os.getenv("GROQ_API_KEY") or ""
resend.api_key = os.getenv("RESEND_API_KEY") or ""
GMAIL_USER = os.getenv("GMAIL_USER") or ""
CRISP_WEBSITE_ID = os.getenv("CRISP_WEBSITE_ID") or ""
CRISP_TOKEN = os.getenv("CRISP_TOKEN") or ""

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=api_key
) if api_key else None

with open("policy.txt", "r") as f:
    rules = f.read()

def send_crisp_reply(session_id, message):
    url = f"https://api.crisp.chat/v1/website/{CRISP_WEBSITE_ID}/conversation/{session_id}/message"
    headers = {
        "Content-Type": "application/json",
        "X-Crisp-Tier": "plugin",
        "Authorization": f"Basic {CRISP_TOKEN}"
    }
    payload = {
        "type": "text",
        "from": "operator",
        "origin": "chat",
        "content": message
    }
    response = requests.post(url, json=payload, headers=headers)
    print("CRISP REPLY STATUS:", response.status_code, response.text)

def send_refund_email(order_id, reason, customer_email):
    try:
        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": [GMAIL_USER, customer_email],
            "subject": f"New Refund Request - Order {order_id}",
            "html": f"<p><b>Order #:</b> {order_id}<br><b>Reason:</b> {reason}<br><b>Customer Email:</b> {customer_email}</p>"
        })
    except Exception as e:
        print(f"Email error: {e}")

@app.get("/")
def root():
    return {"status": "Agent is running"}

@app.post("/webhook")
async def crisp_webhook(request: Request):
    data = await request.json()

    event = data.get("event", "")
    if event != "message:send":
        return {"status": "ignored"}

    message_data = data.get("data", {})
    if message_data.get("from") != "user":
        return {"status": "ignored"}

    user_message = message_data.get("content", "")
    session_id = message_data.get("session_id", "")

    if not user_message or not session_id:
        return {"status": "ignored"}

    system_prompt = f"""You are a helpful customer service agent. Use these rules: {rules}. Keep responses under 40 words. If customer wants a refund, ask for Order #, Reason, and Email one by one. Once you have all 3, output exactly: [TRIGGER|OrderNumber|Reason|Email]"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    if not client:
        send_crisp_reply(session_id, "Sorry, I am unavailable right now.")
        return {"status": "no client"}

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.7
    )

    response_text = response.choices[0].message.content

    if "[TRIGGER|" in response_text:
        match = re.search(r'\[TRIGGER\|(.*?)\|(.*?)\|(.*?)\]', response_text)
        if match:
            order = match.group(1).strip()
            reason = match.group(2).strip()
            email = match.group(3).strip()
            send_refund_email(order, reason, email)
        response_text = re.sub(r'\[TRIGGER\|.*?\]', '', response_text).strip()

    send_crisp_reply(session_id, response_text)
    return {"status": "ok"}
