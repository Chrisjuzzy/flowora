from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database_production import get_db
from models.monetization import Wallet, Transaction, WalletCharge
from models.user import User
from security import get_current_user
from datetime import datetime
import logging
from services.wallet_service import (
    credit_wallet,
    get_or_create_wallet,
    lock_wallet_charge,
    serialize_amount,
)

router = APIRouter(prefix="/wallet", tags=["wallet"])
logger = logging.getLogger(__name__)

@router.get("/balance")
def get_balance(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    wallet = get_or_create_wallet(db, current_user.id)
    return {"balance": serialize_amount(wallet.balance), "currency": wallet.currency}

@router.post("/recharge")
def recharge_wallet(amount: float, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    wallet = get_or_create_wallet(db, current_user.id)
    reference = f"charge_mock_{int(datetime.utcnow().timestamp())}"
    charge = WalletCharge(
        wallet_id=wallet.id,
        amount=amount,
        currency=wallet.currency,
        status="pending",
        provider="mock",
        provider_reference=reference,
    )
    db.add(charge)
    db.commit()
    db.refresh(charge)

    logger.info("Wallet recharge initiated", extra={"wallet_id": wallet.id, "charge_id": charge.id, "amount": amount})

    return {
        "status": charge.status,
        "charge_id": charge.id,
        "amount": serialize_amount(charge.amount),
        "currency": charge.currency,
        "message": "Recharge created. Confirm to complete payment.",
        "next_action": "confirm"
    }


@router.post("/recharge/{charge_id}/confirm")
def confirm_recharge(charge_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    wallet = get_or_create_wallet(db, current_user.id)
    charge = lock_wallet_charge(db, charge_id=charge_id, wallet_id=wallet.id)
    if not charge:
        raise HTTPException(status_code=404, detail="Charge not found")
    if charge.status != "pending":
        raise HTTPException(status_code=409, detail=f"Charge already {charge.status}")

    charge.status = "succeeded"
    charge.updated_at = datetime.utcnow()
    wallet, _ = credit_wallet(
        db=db,
        user_id=current_user.id,
        amount=charge.amount,
        transaction_type="recharge",
        description=f"Recharge of {serialize_amount(charge.amount)} {wallet.currency}",
        reference_id=charge.provider_reference,
        currency=wallet.currency,
    )
    db.commit()

    logger.info(
        "Wallet recharge succeeded",
        extra={"wallet_id": wallet.id, "charge_id": charge.id, "amount": serialize_amount(charge.amount)}
    )

    return {
        "status": charge.status,
        "charge_id": charge.id,
        "new_balance": serialize_amount(wallet.balance)
    }


@router.post("/recharge/{charge_id}/fail")
def fail_recharge(charge_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    wallet = get_or_create_wallet(db, current_user.id)
    charge = lock_wallet_charge(db, charge_id=charge_id, wallet_id=wallet.id)
    if not charge:
        raise HTTPException(status_code=404, detail="Charge not found")
    if charge.status != "pending":
        raise HTTPException(status_code=409, detail=f"Charge already {charge.status}")

    charge.status = "failed"
    charge.updated_at = datetime.utcnow()
    db.commit()

    logger.info("Wallet recharge failed", extra={"wallet_id": wallet.id, "charge_id": charge.id})

    return {"status": charge.status, "charge_id": charge.id}

@router.get("/transactions")
def get_transactions(limit: int = 20, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    wallet = get_or_create_wallet(db, current_user.id)
    transactions = db.query(Transaction).filter(Transaction.wallet_id == wallet.id).order_by(Transaction.created_at.desc()).limit(limit).all()
    return transactions


@router.get("/charges")
def get_charges(limit: int = 20, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    wallet = get_or_create_wallet(db, current_user.id)
    charges = db.query(WalletCharge).filter(WalletCharge.wallet_id == wallet.id).order_by(WalletCharge.created_at.desc()).limit(limit).all()
    return charges
