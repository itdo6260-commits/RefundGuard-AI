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
async def botpress_webhook(request: Request):
    try:
        # 1. Pull the data from Botpress
        data = await request.json()
        user_message = data.get("message", "")

        # 2. CHOOSE YOUR PERSONA HERE (Just comment/uncomment the one you want)
        
        # --- PAUL (The Professional) ---
        # system_prompt = "You are Paul, a professional customer servive agent. You are helpful, formal, and polite."
        
        # --- STEVE (The Savage) ---
        system_prompt = "You are Steve. You are funny, witty, and an absolute savage customer service agent. Use sarcasm and roasts."
        
        # 3. Build the AI message
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        # 4. Call the Groq Brain (using the model from your image_6423d9.png)
        # We use a try/except here to catch any API errors so the bot doesn't crash
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.9 if "Steve" in system_prompt else 0.7, # Steve gets more creative
            max_tokens=150
        )
        
        ai_reply = response.choices[0].message.content

        # 5. Send the REAL answer back (No more echoing!)
        return {"reply": ai_reply}

    except Exception as e:
        print(f"ERROR: {e}")
        return {"reply": "My bad, something went wrong in my brain. Try again?"}

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
