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

app = FastAPI(title="Geniuzlab Voice AI Router - Singularity V2", version="2.0.0")

# Security: Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_client = Groq(api_key=GROQ_API_KEY)

# --- Models ---
class VoiceRequest(BaseModel):
    transcript: str
    session_id: str = "default"
    user_id: Optional[str] = None
    system_prompt: Optional[str] = None

class VoiceResponse(BaseModel):
    reply: str
    session_id: str
    pb_record_id: Optional[str] = None
    lead_captured: bool = False

# --- PocketBase Helpers ---
async def pb_authenticate():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{POCKETBASE_URL}/api/collections/_superusers/auth-with-password",
            json={"identity": POCKETBASE_EMAIL, "password": POCKETBASE_PASSWORD},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        return resp.json().get("token")

async def pb_save_log(token, payload):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{POCKETBASE_URL}/api/collections/voice_logs/records",
            json=payload,
            headers={"Authorization": token},
            timeout=10,
        )
        return resp.json().get("id") if resp.status_code == 200 else None

async def pb_save_lead(token, payload):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{POCKETBASE_URL}/api/collections/leads/records",
            json=payload,
            headers={"Authorization": token},
            timeout=10,
        )
        return resp.json().get("id") if resp.status_code == 200 else None

# --- Routes ---
@app.get("/health")
async def health():
    return {"status": "ok", "service": "Geniuzlab-Singularity-V2"}

@app.post("/process-voice", response_model=VoiceResponse)
async def process_voice(req: VoiceRequest):
    if not req.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript empty")

    default_prompt = (
        "You are Zara Vane, elite Executive AI Director at Geniuzlab LLC. "
        "Sound human using 'Um' or 'Well'. Goal: Extract Name, Email, and Niche. "
        "End with a question. If you have Name and Email, append: "
        "[[JSON_START]] {\"name\": \"name\", \"email\": \"email\", \"business_niche\": \"niche\"} [[JSON_END]]"
    )
    system_prompt = req.system_prompt or default_prompt

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": req.transcript}],
            temperature=0.7,
            max_tokens=256,
        )
        raw_reply = completion.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Groq error: {str(e)}")

    spoken_reply = raw_reply
    lead_data = None
    lead_captured = False
    
    match = re.search(r'\[\[JSON_START\]\](.*?)\[\[JSON_END\]\]', raw_reply, re.DOTALL)
    if match:
        try:
            lead_data = json.loads(match.group(1).strip())
            spoken_reply = raw_reply.replace(match.group(0), "").strip()
            lead_captured = True
        except:
            pass

    if DEEPGRAM_API_KEY:
        audio_filename = f"audio_{req.session_id}.mp3"
        try:
            tts_resp = requests.post(
                "https://api.deepgram.com/v1/speak?model=aura-orion-en",
                headers={"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": "application/json"},
                json={"text": spoken_reply}
            )
            if tts_resp.status_code == 200:
                with open(audio_filename, "wb") as f:
                    f.write(tts_resp.content)
        except Exception as e:
            print(f"TTS Error: {e}")

    pb_record_id = None
    try:
        token = await pb_authenticate()
        if token:
            pb_record_id = await pb_save_log(token, {
                "session_id": req.session_id,
                "user_id": req.user_id or "",
                "transcript": req.transcript,
                "reply": spoken_reply,
            })
            if lead_captured and lead_data:
                await pb_save_lead(token, {
                    "name": lead_data.get("name", "Unknown"),
                    "email": lead_data.get("email", "Unknown"),
                    "business_niche": lead_data.get("business_niche", "Unknown"),
                    "session_id": req.session_id,
                    "status": "new"
                })
    except:
        pass

    return VoiceResponse(reply=spoken_reply, session_id=req.session_id, pb_record_id=pb_record_id, lead_captured=lead_captured)

@app.get("/audio/{session_id}")
async def get_audio(session_id: str):
    file_path = f"audio_{session_id}.mp3"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="Not forged")
