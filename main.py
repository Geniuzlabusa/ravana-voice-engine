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

app = FastAPI(title="Geniuzlab Singularity V4 - Stabilized")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
groq_client = Groq(api_key=GROQ_API_KEY)

class VoiceRequest(BaseModel):
    transcript: str
    session_id: str
    business_id: str = "default"

async def pb_authenticate():
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{POCKETBASE_URL}/api/collections/_superusers/auth-with-password",
                             json={"identity": POCKETBASE_EMAIL, "password": POCKETBASE_PASSWORD})
        return r.json().get("token")

async def get_business_context(token: str, biz_id: str):
    async with httpx.AsyncClient() as client:
        # Fixed query logic to handle missing records safely
        resp = await client.get(
            f"{POCKETBASE_URL}/api/collections/business_configs/records?filter=(business_id='{biz_id}')",
            headers={"Authorization": token}
        )
        data = resp.json().get("items", [])
        return data[0] if data else {} # Return empty dict instead of None to prevent 'get' errors

@app.post("/process-voice")
async def process_voice(req: VoiceRequest):
    token = await pb_authenticate()
    biz = await get_business_context(token, req.business_id)
    
    # SAFE DEFAULTS TO PREVENT ATTRIBUTEERRORS
    name = biz.get("business_name", "Geniuzlab")
    knowledge = biz.get("knowledge_base", "AI Sales Executive")
    location = biz.get("target_location", "Matara Command")

    system_prompt = (
        f"You are Zara Vane, the elite Executive AI Director at Geniuzlab LLC. "
        f"You represent {name} in {location}. KNOWLEDGE: {knowledge}. "
        "Sound human using 'Um' or 'Well'. Max 2 short sentences. End with a sharp question to control the frame."
    )

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": req.transcript}]
        )
        reply = completion.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    if DEEPGRAM_API_KEY:
        audio_path = f"audio_{req.session_id}.mp3"
        res = requests.post(
            "https://api.deepgram.com/v1/speak?model=aura-stella-en",
            headers={"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": "application/json"},
            json={"text": reply}
        )
        if res.status_code == 200:
            with open(audio_path, "wb") as f: f.write(res.content)

    return {"reply": reply}

@app.get("/audio/{session_id}")
async def get_audio(session_id: str):
    return FileResponse(f"audio_{session_id}.mp3")
