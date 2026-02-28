import os
import re
import json
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

app = FastAPI(title="Geniuzlab Voice AI Router - Singularity Edition", version="2.0.0")

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
    user_id: str | None = None
    system_prompt: str | None = None

class VoiceResponse(BaseModel):
    reply: str
    session_id: str
    pb_record_id: str | None = None
    lead_captured: bool = False

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
        return None

async def pb_save_lead(token: str, payload: dict) -> str | None:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{POCKETBASE_URL}/api/collections/leads/records",
            json=payload,
            headers={"Authorization": token},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("id")
        print(f"[WARN] Lead save failed: {resp.text}")
        return None

# --- Routes ---
@app.get("/health")
async def health():
    return {"status": "ok", "service": "Geni
