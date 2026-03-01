import os
import urllib.parse
import stripe
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- ENTERPRISE CONFIG ---
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_placeholder")
stripe.api_key = STRIPE_SECRET_KEY
POCKETBASE_URL = os.getenv("POCKETBASE_URL", "http://18.207.204.66:8090")

app = FastAPI(title="Geniuzlab Enterprise API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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

@app.post("/generate-enterprise-proposal")
async def generate_enterprise_proposal(req: EnterpriseProposalRequest):
    # 1. CALCULATE FINANCIAL THREAT 
    lost_yearly = req.missed_calls * req.avg_value * 52

    # 2. DYNAMIC PRICING ALGORITHM
    base_price = 497
    if req.employees == "5-20": base_price += 250
    elif req.employees == "50+": base_price += 1000  
    if req.current_crm != "None": base_price += 250   

    # 3. STRIPE SECURE CHECKOUT GENERATION
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            customer_email=req.email,
            line_items=[{
                'price_data': {
                    'currency': 'gbp',
                    'product_data': {
                        'name': f"Geniuzlab {req.product_name} Deployment",
                        'description': f"Custom AI Architecture for {req.company} ({req.niche} Sector).",
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
