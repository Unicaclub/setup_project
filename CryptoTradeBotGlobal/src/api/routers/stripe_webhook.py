from fastapi import APIRouter, Request, HTTPException
import stripe
import os
from ..models import Assinatura
from ..database import get_session
from sqlmodel import Session, select

router = APIRouter(prefix="/stripe", tags=["stripe"])

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Exemplo: atualizar status da assinatura
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        # Atualize a assinatura no banco (exemplo simplificado)
        # ...
    return {"ok": True}
