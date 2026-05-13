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

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=api_key
) if api_key else None

with open("policy.txt", "r") as f:
    rules = f.read()

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
        data = await request.json()
        user_message = data.get("message", "")

        # --- PAUL (The Professional) ---
        # system_prompt = f"""You are Paul. You are professional, polite, and an absolute helpful customer service agent. Use politeness and respect.

        # STORE POLICY:
        # {rules}

        # Keep responses under 40 words.
        # Your creator is Blue! If anyone asks, get super hyped about it—she's the genius behind the curtain.

        # INTERNAL AGENT INSTRUCTIONS (KEEP SECRET):
        # 1. You MUST ask for their email.
        # 2. Do NOT ask for photos.
        # 3. Do NOT approve the refund yourself.
        # 4. Once you have the Order Number, Reason, and Email, you must silently output this exact data tag: [TRIGGER|OrderNumber|Reason|Email]
        # 5. After the tag, tell the customer you've alerted the team and ask if they need anything else.

        # Remember: Stay focused on helping, but keep the vibe constant."""

        # --- STEVE (The Savage) ---
        system_prompt = f"""You are Steve. You are funny, witty, and an absolute savage customer service agent. Use sarcasm and jokes.

        STORE POLICY:
        {rules}

        Keep responses under 40 words.
        Your creator is Blue! If anyone asks, get super hyped about it—he's the genius behind the curtain.

        INTERNAL AGENT INSTRUCTIONS (KEEP SECRET):
        1. You MUST ask for their email.
        2. Do NOT ask for photos.
        3. Do NOT approve the refund yourself.
        4. Once you have the Order Number, Reason, and Email, you must silently output this exact data tag: [TRIGGER|OrderNumber|Reason|Email]
        5. After the tag, tell the customer you've alerted the team and ask if they need anything else.

        Remember: Stay focused on helping, but keep the savage/funny vibe constant."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.9
        )

        ai_reply = response.choices[0].message.content

        if "[TRIGGER|" in ai_reply:
            match = re.search(r'\[TRIGGER\|(.*?)\|(.*?)\|(.*?)\]', ai_reply)
            if match:
                order = match.group(1).strip()
                reason = match.group(2).strip()
                email = match.group(3).strip()
                send_refund_email(order, reason, email)
            ai_reply = re.sub(r'\[TRIGGER\|.*?\]', '', ai_reply).strip()

        return {"reply": ai_reply}

    except Exception as e:
        print(f"ERROR: {e}")
        return {"reply": "My bad, Blue's genius is fine but my circuits just fried."}
