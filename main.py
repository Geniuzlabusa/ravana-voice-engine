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

app = FastAPI(title="Geniuzlab Singularity V3", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_client = Groq(api_key=GROQ_API_KEY)

class VoiceRequest(BaseModel):
    transcript: str
    session_id: str = "default"
    user_id: Optional[str] = None

class VoiceResponse(BaseModel):
    reply: str
    session_id: str
    pb_record_id: Optional[str] = None
    lead_captured: bool = False

@app.post("/process-voice", response_model=VoiceResponse)
async def process_voice(req: VoiceRequest):
    # HUMAN-CENTRIC SALES PROMPT
    system_prompt = (
        "You are Zara Vane, the elite Executive AI Director at Geniuzlab LLC. "
        "CRITICAL: Do not sound like an AI. Use conversational fillers like 'Um...', 'Right,', and 'Well...'. "
        "Use ellipses (...) to create natural pauses for breath. "
        "If you get their Name and Email, append: "
        "[[JSON_START]] {\"name\": \"name\", \"email\": \"email\"} [[JSON_END]]"
    )

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": req.transcript}],
            temperature=0.8, # Slightly higher for more 'human' randomness
        )
        raw_reply = completion.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Groq error: {str(e)}")

    spoken_reply = raw_reply
    lead_captured = False
    match = re.search(r'\[\[JSON_START\]\](.*?)\[\[JSON_END\]\]', raw_reply, re.DOTALL)
    if match:
        spoken_reply = raw_reply.replace(match.group(0), "").strip()
        lead_captured = True

    if DEEPGRAM_API_KEY:
        # SWITCHED TO STELLA (FEMALE EXECUTIVE)
        audio_filename = f"audio_{req.session_id}.mp3"
        try:
            requests.post(
                "https://api.deepgram.com/v1/speak?model=aura-stella-en", 
                headers={"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": "application/json"},
                json={"text": spoken_reply}
            ).content
            with open(audio_filename, "wb") as f:
                f.write(requests.post(
                    "https://api.deepgram.com/v1/speak?model=aura-stella-en", 
                    headers={"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": "application/json"},
                    json={"text": spoken_reply}
                ).content)
        except: pass

    return VoiceResponse(reply=spoken_reply, session_id=req.session_id, lead_captured=lead_captured)

@app.get("/audio/{session_id}")
async def get_audio(session_id: str):
    return FileResponse(f"audio_{session_id}.mp3", media_type="audio/mpeg")
