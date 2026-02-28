import os
import re
import json
import httpx
import requests
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

app = FastAPI(title="Geniuzlab Singularity V5.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
groq_client = Groq(api_key=GROQ_API_KEY)

class InteractionRequest(BaseModel):
    input_text: str
    session_id: str
    business_id: str = "default"
    mode: str = "voice"

async def pb_authenticate():
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{POCKETBASE_URL}/api/collections/_superusers/auth-with-password",
                             json={"identity": POCKETBASE_EMAIL, "password": POCKETBASE_PASSWORD})
        return r.json().get("token")

@app.post("/interact")
async def interact(req: InteractionRequest):
    token = await pb_authenticate()
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{POCKETBASE_URL}/api/collections/business_configs/records?filter=(business_id='{req.business_id}')", headers={"Authorization": token})
        biz = resp.json().get("items", [{}])[0]

    name = biz.get("business_name", "Geniuzlab")
    knowledge = biz.get("knowledge_base", "AI Solutions")
    
    # ENFORCING BREVITY TO PREVENT "ROBOTIC READING"
    system_prompt = (
        f"You are Zara Vane, Executive Director at {name}. Knowledge: {knowledge}. "
        "CRITICAL: Speak in short, punchy sentences. Max 20 words total. "
        "Use 'Um' or 'Listen' occasionally. Never lecture. End with one sharp question. "
        "If they are ready to buy, append: [[PAYMENT_LINK]]"
    )

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": req.input_text}],
            temperature=0.8
        )
        reply = completion.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=502, detail="Brain Lag")
    
    payment_triggered = "[[PAYMENT_LINK]]" in reply
    clean_reply = reply.replace("[[PAYMENT_LINK]]", "").strip()

    if req.mode == "voice" and DEEPGRAM_API_KEY:
        audio_path = f"audio_{req.session_id}.mp3"
        # Force Stella for the highest fidelity female executive voice
        res = requests.post(
            "https://api.deepgram.com/v1/speak?model=aura-stella-en",
            headers={"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": "application/json"},
            json={"text": clean_reply}
        )
        with open(audio_path, "wb") as f: f.write(res.content)

    return {"reply": clean_reply, "payment_triggered": payment_triggered}

@app.get("/audio/{session_id}")
async def get_audio(session_id: str):
    return FileResponse(f"audio_{session_id}.mp3")
