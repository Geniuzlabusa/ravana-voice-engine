import os
import httpx
import requests
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

app = FastAPI(title="Geniuzlab Voice AI Router", version="1.0.0")

# --- Security: Enable CORS for the pSEO Web Widgets ---
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
    session_id: str = "default"             # Enforces a strict session_id
    user_id: str | None = None
    system_prompt: str | None = None

class VoiceResponse(BaseModel):
    reply: str
    session_id: str
    pb_record_id: str | None = None

# --- PocketBase helpers ---
async def pb_authenticate() -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{POCKETBASE_URL}/api/collections/_superusers/auth-with-password",
            json={"identity": POCKETBASE_EMAIL, "password": POCKETBASE_PASSWORD},
            timeout=10,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="PocketBase auth failed")
        return resp.json()["token"]

async def pb_save_log(token: str, payload: dict) -> str | None:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{POCKETBASE_URL}/api/collections/voice_logs/records",
            json=payload,
            headers={"Authorization": token},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("id")
        print(f"[WARN] PocketBase save failed: {resp.status_code} {resp.text}")
        return None

# --- Routes ---
@app.get("/health")
async def health():
    return {"status": "ok", "service": "Geniuzlab Voice AI Router"}

@app.post("/process-voice", response_model=VoiceResponse)
async def process_voice(req: VoiceRequest):
    if not req.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty")

    # The Singularity Closer Prompt
    system_prompt = req.system_prompt or (
        "You are Zara Vane, the elite Executive AI Director at Geniuzlab LLC. "
        "Speak with absolute certainty and a rugged, professional edge. Keep your response to 2 short sentences."
    )

    # 1. Brain: Get Llama 3 response via Groq
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.transcript},
            ],
            temperature=0.7,
            max_tokens=256,
        )
        reply = completion.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Groq error: {str(e)}")

    # 2. Voice: DEEPGRAM TTS FORGE
    if DEEPGRAM_API_KEY:
        audio_filename = f"audio_{req.session_id}.mp3"
        deepgram_url = "https://api.deepgram.com/v1/speak?model=aura-orion-en"
        
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "application/json"
        }
        tts_payload = {"text": reply}
        
        print(f"[INFO] Forging Boyka audio payload for session: {req.session_id}...")
        try:
            tts_response = requests.post(deepgram_url, headers=headers, json=tts_payload)
            if tts_response.status_code == 200:
                with open(audio_filename, "wb") as f:
                    f.write(tts_response.content)
                print(f"[SUCCESS] Cinematic audio forged: {audio_filename}")
            else:
                print(f"[WARN] Deepgram API failed: {tts_response.text}")
        except Exception as e:
            print(f"[WARN] Deepgram Request Error: {str(e)}")
    else:
        print("[WARN] DEEPGRAM_API_KEY not found in environment variables. Skipping audio forge.")

    # 3. Memory: Log interaction to PocketBase
    pb_record_id = None
    try:
        token = await pb_authenticate()
        pb_record_id = await pb_save_log(token, {
            "session_id": req.session_id,
            "user_id": req.user_id or "",
            "transcript": req.transcript,
            "reply": reply,
        })
    except Exception as e:
        print(f"[WARN] PocketBase logging skipped: {e}")

    return VoiceResponse(
        reply=reply,
        session_id=req.session_id,
        pb_record_id=pb_record_id,
    )

@app.get("/audio/{session_id}")
async def get_audio(session_id: str):
    file_path = f"audio_{session_id}.mp3"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="Audio file not found or not yet forged")
