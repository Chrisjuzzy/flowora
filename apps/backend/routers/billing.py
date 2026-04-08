from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from database_production import get_db
from models import Subscription, Execution, User, Wallet, Invoice
from security import get_current_user
from pydantic import BaseModel
from datetime import datetime, timedelta
import logging
from services.wallet_service import serialize_amount

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])

# --- Constants ---
TIER_LIMITS = {
    "free": {"agents": 5, "runs_per_month": 100},
    "pro": {"agents": 50, "runs_per_month": 10000},
    "enterprise": {"agents": 999999, "runs_per_month": 999999}
}

TIER_PRICES = {
    "pro": "price_pro_monthly", # Stripe Price ID
    "enterprise": "price_ent_monthly"
}

# --- Schemas ---
class SubscriptionSchema(BaseModel):
    tier: str
    status: str
    start_date: datetime
    end_date: Optional[datetime]
    limits: Dict[str, int]
    
    class Config:
        from_attributes = True

class UsageStats(BaseModel):
    total_executions: int
    total_tokens: int
    estimated_cost: float
    remaining_credits: float
    monthly_executions: int

class InvoiceSchema(BaseModel):
    id: int
    amount: float
    status: str
    stripe_invoice_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Helper ---
def check_subscription_limit(db: Session, user_id: int, resource: str, current_count: int):
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    tier = sub.tier if sub and sub.status == "active" else "free"
    
    limit = TIER_LIMITS.get(tier, TIER_LIMITS["free"]).get(resource, 0)
    if current_count >= limit:
        raise HTTPException(
            status_code=403, 
            detail=f"Limit reached for {resource} ({limit}) on {tier} tier. Upgrade to increase limits."
        )

# --- Endpoints ---

@router.get("/invoices", response_model=List[InvoiceSchema])
def get_invoices(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Invoice).filter(Invoice.user_id == current_user.id).order_by(Invoice.created_at.desc()).all()

@router.get("/subscription", response_model=SubscriptionSchema)
def get_subscription(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if not sub:
        # Create default free tier
        sub = Subscription(user_id=current_user.id, tier="free", status="active")
        db.add(sub)
        db.commit()
        db.refresh(sub)
        
    limits = TIER_LIMITS.get(sub.tier, TIER_LIMITS["free"])
    
    # Return schema manually since limits is extra field
    return SubscriptionSchema(
        tier=sub.tier,
        status=sub.status,
        start_date=sub.start_date,
        end_date=sub.end_date,
        limits=limits
    )

@router.post("/checkout-session")
def create_checkout_session(tier: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create Stripe Checkout Session"""
    if tier not in TIER_PRICES:
        raise HTTPException(status_code=400, detail="Invalid tier")
        
    # Mock Stripe Session URL
    # In real implementation:
    # session = stripe.checkout.Session.create(...)
    # return {"url": session.url}
    
    return {"url": f"https://checkout.stripe.com/pay/{TIER_PRICES[tier]}?client_reference_id={current_user.id}"}

@router.post("/upgrade")
def upgrade_tier(
    tier: str,
    confirm: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manual upgrade with explicit confirmation step.
    """
    if tier not in ["pro", "enterprise"]:
        raise HTTPException(status_code=400, detail="Invalid tier")

    if not confirm:
        return {
            "status": "pending",
            "message": "Upgrade requires confirmation. Re-submit with confirm=true after payment."
        }

    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if not sub:
        sub = Subscription(user_id=current_user.id)

    sub.tier = tier
    sub.status = "active"
    sub.end_date = datetime.utcnow() + timedelta(days=30)
    db.add(sub)
    db.commit()

    logger.info("Subscription upgraded", extra={"user_id": current_user.id, "tier": tier})

    return {"status": "success", "message": f"Upgraded to {tier} tier"}

@router.get("/usage", response_model=UsageStats)
def get_usage(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Calculate usage from executions
    executions = db.query(Execution).filter(Execution.user_id == current_user.id).all()
    
    total_execs = len(executions)
    
    # Monthly executions (simple filter for now)
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_execs = len([e for e in executions if e.timestamp >= month_start])
    
    total_tokens = sum([e.token_usage for e in executions if e.token_usage])
    total_cost = sum([float(e.cost_estimate) for e in executions if e.cost_estimate])
    
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    remaining = serialize_amount(wallet.balance) if wallet else 0.0
    
    return {
        "total_executions": total_execs,
        "total_tokens": total_tokens,
        "estimated_cost": total_cost,
        "remaining_credits": remaining,
        "monthly_executions": monthly_execs
    }

@router.post("/webhook")
async def stripe_webhook(payload: dict, db: Session = Depends(get_db)):
    """Handle Stripe Webhooks"""
    event_type = payload.get("type")
    data = payload.get("data", {}).get("object", {})
    
    logger.info(f"Received webhook: {event_type}")
    
    if event_type == "checkout.session.completed":
        # Handle successful subscription
        client_reference_id = data.get("client_reference_id")
        customer_id = data.get("customer")
        
        if client_reference_id:
            user_id = int(client_reference_id)
            sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
            if sub:
                sub.status = "active"
                if customer_id:
                    sub.stripe_customer_id = customer_id
                # Update tier based on price/product ID if needed
                # sub.tier = "pro" 
                db.commit()
                logger.info(f"Updated subscription for user {user_id}")
                
    elif event_type == "invoice.payment_failed":
        # Handle failed payment
        customer_id = data.get("customer")
        sub = db.query(Subscription).filter(Subscription.stripe_customer_id == customer_id).first()
        if sub:
            sub.status = "past_due"
            db.commit()
            
    elif event_type == "invoice.payment_succeeded":
        # Handle successful payment and create invoice record
        customer_id = data.get("customer")
        amount_paid = data.get("amount_paid", 0) / 100.0
        invoice_id = data.get("id")
        
        # Try to find user via subscription
        sub = db.query(Subscription).filter(Subscription.stripe_customer_id == customer_id).first()
        if sub:
            # Create Invoice Record
            new_invoice = Invoice(
                user_id=sub.user_id,
                amount=amount_paid,
                status="paid",
                stripe_invoice_id=invoice_id
            )
            db.add(new_invoice)
            db.commit()
            logger.info(f"Created invoice for user {sub.user_id}")
            
    return {"status": "received"}
