import os
import re
import json
import httpx
import requests
import urllib.parse
import stripe
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

# ==========================================
# ENTERPRISE CONFIGURATION & SECRETS
# ==========================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_placeholder")
POCKETBASE_URL = os.getenv("POCKETBASE_URL", "http://18.207.204.66:8090")
POCKETBASE_EMAIL = os.getenv("POCKETBASE_EMAIL", "admin@geniuzlab.com")
POCKETBASE_PASSWORD = os.getenv("POCKETBASE_PASSWORD", "changeme")

# Initialize Stripe & APIs
stripe.api_key = STRIPE_SECRET_KEY
groq_client = Groq(api_key=GROQ_API_KEY)

# Initialize FastAPI Server
app = FastAPI(title="Geniuzlab Enterprise API V1.0")
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# ==========================================
# DATA MODELS
# ==========================================
class InteractionRequest(BaseModel):
    input_text: str
    session_id: str
    business_id: str = "default"
    mode: str = "voice"

class EnterpriseProposalRequest(BaseModel):
    name: str
    email: str
    phone: str
    company: str
    employees: str       
    current_crm: str     
    missed_calls: int
    avg_value: int
    product_name: str    
    niche: str

# ==========================================
# HELPER: POCKETBASE AUTHENTICATION
# ==========================================
async def pb_auth():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{POCKETBASE_URL}/api/collections/_superusers/auth-with-password",
                json={"identity": POCKETBASE_EMAIL, "password": POCKETBASE_PASSWORD}
            )
            return r.json().get("token")
    except:
        return None

# ==========================================
# ENDPOINT 1: AI VOICE & CHAT ENGINE
# ==========================================
@app.post("/interact")
async def interact(req: InteractionRequest):
    token = await pb_auth()
    biz_name = "Geniuzlab"
    kb = "World-class AI Forging."
    
    if token:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{POCKETBASE_URL}/api/collections/business_configs/records?filter=(business_id='{req.business_id}')", 
                    headers={"Authorization": token}
                )
                biz = resp.json().get("items", [{}])[0]
                biz_name = biz.get("business_name", biz_name)
                kb = biz.get("knowledge_base", kb)
        except:
            pass

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
    except Exception as e:
        raise HTTPException(status_code=500, detail="LLM Brain Lag")

    clean_reply = re.sub(r'\[\[.*?\]\]', '', reply).strip()

    # Deepgram Voice Generation
    if req.mode == "voice" and DEEPGRAM_API_KEY:
        audio_path = f"audio_{req.session_id}.mp3"
        try:
            res = requests.post(
                "https://api.deepgram.com/v1/speak?model=aura-stella-en",
                headers={"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": "application/json"},
                json={"text": clean_reply}
            )
            with open(audio_path, "wb") as f: 
                f.write(res.content)
        except Exception as e:
            print(f"Voice generation failed: {e}")

    return {"reply": clean_reply, "captured": False}

# ==========================================
# ENDPOINT 2: ENTERPRISE STRIPE CALCULATOR
# ==========================================
@app.post("/generate-enterprise-proposal")
async def generate_enterprise_proposal(req: EnterpriseProposalRequest):
    # 1. CALCULATE FINANCIAL THREAT 
    lost_yearly = req.missed_calls * req.avg_value * 52

    # 2. DYNAMIC PRICING ALGORITHM
    base_price = 497
    if req.employees == "5-20": base_price += 250
    elif req.employees == "50+": base_price += 1000  
    if req.current_crm != "None": base_price += 250   

    # 3. POCKETBASE CRM LOGGING (Silent execution)
    token = await pb_auth()
    if token:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{POCKETBASE_URL}/api/collections/leads/records", 
                    json={
                        "name": req.name,
                        "email": req.email,
                        "business_niche": f"{req.company} - {req.niche}",
                        "status": "Enterprise Proposal Generated",
                    },
                    headers={"Authorization": token}
                )
        except Exception as e:
            print(f"CRM Log Error: {e}")

    # 4. STRIPE SECURE CHECKOUT GENERATION
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            customer_email=req.email,
            line_items=[{
                'price_data': {
                    'currency': 'gbp',
                    'product_data': {
                        'name': f"Geniuzlab {req.product_name} Deployment",
                        'description': f"Enterprise-Grade AI Architecture for {req.company}. Includes 24/7 autonomous lead capture, sub-800ms latency, and {req.current_crm} CRM sync for the {req.niche} sector.",
                        'images': ["https://raw.githubusercontent.com/github/explore/main/topics/ai/ai.png"], # Static, highly reliable premium tech image
                    },
                    'unit_amount': base_price * 100, 
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url="https://geniuzlab.com/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://geniuzlab.com/",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe Gateway Error: {str(e)}")

    return {
        "status": "success",
        "lost_revenue": lost_yearly,
        "calculated_price": base_price,
        "stripe_checkout_url": checkout_session.url
    }

# ==========================================
# ENDPOINT 3: AUDIO SERVING
# ==========================================
@app.get("/audio/{session_id}")
async def get_audio(session_id: str):
    file_path = f"audio_{session_id}.mp3"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Audio file not found")
