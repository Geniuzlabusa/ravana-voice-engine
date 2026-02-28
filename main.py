import os
import re
import json
import httpx
import requests
import urllib.parse
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

# --- Config ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
POCKETBASE_URL = os.getenv("POCKETBASE_URL", "http://18.207.204.66:8090")
POCKETBASE_EMAIL = os.getenv("POCKETBASE_EMAIL", "admin@geniuzlab.com")
POCKETBASE_PASSWORD = os.getenv("POCKETBASE_PASSWORD", "changeme")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")

app = FastAPI(title="Geniuzlab Singularity V14")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
groq_client = Groq(api_key=GROQ_API_KEY)

class InteractionRequest(BaseModel):
    input_text: str
    session_id: str
    business_id: str = "default"
    mode: str = "voice"

class ProposalRequest(BaseModel):
    name: str
    email: str
    company: str
    missed_calls: int
    avg_value: int
    business_id: str
    session_id: str

async def pb_auth():
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{POCKETBASE_URL}/api/collections/_superusers/auth-with-password",
                             json={"identity": POCKETBASE_EMAIL, "password": POCKETBASE_PASSWORD})
        return r.json().get("token")

@app.post("/interact")
async def interact(req: InteractionRequest):
    token = await pb_auth()
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{POCKETBASE_URL}/api/collections/business_configs/records?filter=(business_id='{req.business_id}')", headers={"Authorization": token})
        biz = resp.json().get("items", [{}])[0]

    biz_name = biz.get("business_name", "Geniuzlab")
    kb = biz.get("knowledge_base", "World-class AI Forging.")

    system_prompt = (
        f"You are Zara Vane, the elite closer for {biz_name}. "
        f"CONTEXT: {kb}. "
        "STYLE: High-status, rugged, concise. Max 35 words. "
        "Use 'Um' or 'Well' to sound human. End with a sharp question."
    )

    try:
        chat_completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": req.input_text}],
            temperature=0.8
        )
        reply = chat_completion.choices[0].message.content.strip()
    except: raise HTTPException(status_code=500, detail="Brain Lag")

    clean_reply = re.sub(r'\[\[.*?\]\]', '', reply).strip()

    if req.mode == "voice" and DEEPGRAM_API_KEY:
        audio_path = f"audio_{req.session_id}.mp3"
        res = requests.post(
            "https://api.deepgram.com/v1/speak?model=aura-stella-en",
            headers={"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": "application/json"},
            json={"text": clean_reply}
        )
        with open(audio_path, "wb") as f: f.write(res.content)

    return {"reply": clean_reply, "captured": False}

@app.post("/generate-proposal")
async def generate_proposal(req: ProposalRequest):
    token = await pb_auth()
    
    # 1. Calculate the Pain
    lost_yearly = req.missed_calls * req.avg_value * 52
    
    # 2. Store in PocketBase
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{POCKETBASE_URL}/api/collections/leads/records", 
                json={
                    "name": req.name,
                    "email": req.email,
                    "business_niche": req.company,
                    "session_id": req.session_id,
                    "status": "Proposal Generated"
                },
                headers={"Authorization": token}
            )
    except Exception as e:
        print(f"DB Error: {e}")

    # 3. Dynamic Stripe Link Generation (Injecting their email for zero friction)
    base_stripe_link = "https://buy.stripe.com/test_geniuzlab"
    encoded_email = urllib.parse.quote(req.email)
    custom_stripe_link = f"{base_stripe_link}?prefilled_email={encoded_email}"

    return {
        "status": "success",
        "lost_revenue": lost_yearly,
        "stripe_url": custom_stripe_link
    }

@app.get("/audio/{session_id}")
async def get_audio(session_id: str):
    return FileResponse(f"audio_{session_id}.mp3")
