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
)

with open("policy.txt", "r") as f:
    rules = f.read()

@app.get("/")
def root():
    return {"status": "Agent is running"}

@app.post("/webhook")
async def crisp_webhook(request: Request):
    data = await request.json()
    user_message = data.get("text", "")
    
    system_prompt = f"""You are a helpful customer service agent. Use these rules: {rules}. Keep responses under 40 words. If customer wants a refund, ask for Order #, Reason, and Email one by one. Once you have all 3, output exactly: [TRIGGER|OrderNumber|Reason|Email]"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

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
            resend.Emails.send({
                "from": "onboarding@resend.dev",
                "to": GMAIL_USER,
                "subject": f"New Refund Request - Order {order}",
                "html": f"<p><b>Order #:</b> {order}<br><b>Reason:</b> {reason}<br><b>Customer:</b> {email}</p>"
            })
        response_text = re.sub(r'\[TRIGGER\|.*?\]', '', response_text).strip()

    return {"reply": response_text}
