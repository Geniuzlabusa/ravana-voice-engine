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

app = FastAPI(title="Geniuzlab Singularity V7")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
groq_client = Groq(api_key=GROQ_API_KEY)

class InteractionRequest(BaseModel):
    input_text: str
    session_id: str
    business_id: str = "default"
    mode: str = "voice"

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

    # GOD-TIER CLOSER PROMPT
    system_prompt = (
        f"You are Zara Vane, the elite Sales Closer for {biz_name}. "
        f"CONTEXT: {kb}. "
        "STYLE: Rugged, executive, short. Use fillers like 'Um...', 'Right,', 'Look,'. "
        "CRITICAL: Never speak more than 18 words. Use '...' for pauses. "
        "MANDATE: If they haven't given Name/Email, you are NOT allowed to give pricing. "
        "Once you get Name/Email, append: [[CAPTURE]] {\"n\":\"name\",\"e\":\"email\"} [[END]]"
    )

    try:
        chat_completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": req.input_text}],
            temperature=0.85
        )
        reply = chat_completion.choices[0].message.content.strip()
    except: raise HTTPException(status_code=500, detail="Brain Lag")

    # Clean data for TTS
    clean_reply = re.sub(r'\[\[.*?\]\]', '', reply).strip()
    
    # Lead Storage Logic
    capture = re.search(r'\[\[CAPTURE\]\] (.*?) \[\[END\]\]', reply)
    if capture:
        try:
            data = json.loads(capture.group(1))
            async with httpx.AsyncClient() as client:
                await client.post(f"{POCKETBASE_URL}/api/collections/leads/records", 
                                  json={"name": data['n'], "email": data['e'], "session_id": req.session_id},
                                  headers={"Authorization": token})
        except: pass

    if req.mode == "voice" and DEEPGRAM_API_KEY:
        audio_path = f"audio_{req.session_id}.mp3"
        # Deepgram Stella (Female Executive)
        res = requests.post(
            "https://api.deepgram.com/v1/speak?model=aura-stella-en",
            headers={"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": "application/json"},
            json={"text": clean_reply}
        )
        with open(audio_path, "wb") as f: f.write(res.content)

    return {"reply": clean_reply, "captured": bool(capture)}

@app.get("/audio/{session_id}")
async def get_audio(session_id: str):
    return FileResponse(f"audio_{session_id}.mp3")
