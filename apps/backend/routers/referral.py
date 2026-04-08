from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from database_production import get_db
from security import get_current_user
import models
from services.wallet_service import credit_wallet, serialize_amount

router = APIRouter(prefix="/referral", tags=["referral"])


class RedeemRequest(BaseModel):
    referral_id: Optional[int] = None
    code: Optional[str] = None


@router.post("/redeem")
def redeem_referral(
    payload: RedeemRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not payload.referral_id and not payload.code:
        raise HTTPException(status_code=400, detail="referral_id or code required")

    query = db.query(models.Referral)
    if payload.referral_id:
        query = query.filter(models.Referral.id == payload.referral_id)
    if payload.code:
        query = query.filter(models.Referral.code == payload.code)
    referral = query.first()

    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")

    if referral.reward_claimed:
        raise HTTPException(status_code=400, detail="Reward already claimed")

    reward_points = int(referral.reward_points or 0)
    if reward_points <= 0:
        reward_points = 10

    referral.reward_claimed = True
    referral.status = "completed"
    if referral.referred_user_id is None and referral.referee_id is None:
        referral.referred_user_id = current_user.id

    wallet, _ = credit_wallet(
        db=db,
        user_id=referral.referrer_id,
        amount=reward_points,
        transaction_type="referral_reward",
        description="Referral reward redeemed",
        reference_id=str(referral.id),
    )
    db.commit()

    return {
        "status": "redeemed",
        "reward_points": serialize_amount(reward_points),
        "wallet_balance": serialize_amount(wallet.balance),
    }
