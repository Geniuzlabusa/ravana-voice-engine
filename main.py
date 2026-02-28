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

app = FastAPI(title="Geniuzlab Singularity V4")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
groq_client = Groq(api_key=GROQ_API_KEY)

class VoiceRequest(BaseModel):
    transcript: str
    session_id: str
    business_id: str = "default" # The pSEO page will send this

async def get_business_context(token: str, biz_id: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{POCKETBASE_URL}/api/collections/business_configs/records?filter=(business_id='{biz_id}')",
            headers={"Authorization": token}
        )
        data = resp.json().get("items", [])
        return data[0] if data else None

@app.post("/process-voice")
async def process_voice(req: VoiceRequest):
    # 1. AUTH & RETRIEVE KNOWLEDGE
    token = await pb_authenticate()
    biz = await get_business_context(token, req.business_id)
    
    knowledge = biz.get("knowledge_base", "General Geniuzlab Executive") if biz else "AI Sales Specialist"
    location = biz.get("target_location", "Global") if biz else "Matara Command"

    # 2. THE HUMAN SALES PROMPT
    system_prompt = (
        f"You are Zara Vane. You represent {biz.get('business_name', 'Geniuzlab')} in {location}. "
        f"KNOWLEDGE: {knowledge}. "
        "DIRECTIVE: Sound human. Use 'Um', 'Well', and '...'. "
        "STRICT LIMIT: Maximum 25 words. Ask ONE sharp question to close the deal. "
        "If they give contact info, append: [[JSON_START]] {\"name\": \"name\"} [[JSON_END]]"
    )

    # 3. BRAIN
    completion = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": req.transcript}],
        temperature=0.9
    )
    raw_reply = completion.choices[0].message.content.strip()
    spoken_reply = re.sub(r'\[\[.*?\]\]', '', raw_reply).strip()

    # 4. VOICE (Stella - Human Cadence)
    if DEEPGRAM_API_KEY:
        audio_path = f"audio_{req.session_id}.mp3"
        res = requests.post(
            "https://api.deepgram.com/v1/speak?model=aura-stella-en",
            headers={"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": "application/json"},
            json={"text": spoken_reply}
        )
        with open(audio_path, "wb") as f: f.write(res.content)

    return {"reply": spoken_reply}

async def pb_authenticate():
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{POCKETBASE_URL}/api/collections/_superusers/auth-with-password",
                             json={"identity": POCKETBASE_EMAIL, "password": POCKETBASE_PASSWORD})
        return r.json().get("token")

@app.get("/audio/{session_id}")
async def get_audio(session_id: str):
    return FileResponse(f"audio_{session_id}.mp3")
