from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "apps" / "backend"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from database_production import SessionLocal
from models.monetization import Transaction, Wallet
from models.user import User
from security import get_password_hash
from services.wallet_service import (
    InsufficientBalanceError,
    debit_wallet,
    get_or_create_wallet,
    normalize_amount,
    serialize_amount,
)


@dataclass
class AttemptResult:
    worker_id: int
    status_code: int
    success: bool
    duration_ms: float
    reference_id: str
    transaction_id: int | None = None
    balance_after: float | None = None
    error: str | None = None


def ensure_test_user(email: str, password: str) -> int:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                hashed_password=get_password_hash(password),
                role="user",
                is_active="true",
                is_email_verified="true",
                subscription_status="active",
                subscription_tier="enterprise",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            user.is_active = "true"
            user.is_email_verified = "true"
            user.subscription_status = "active"
            user.subscription_tier = "enterprise"
            db.commit()
        return user.id
    finally:
        db.close()


def reset_wallet(user_id: int, balance: Decimal) -> dict[str, Any]:
    db = SessionLocal()
    try:
        wallet = get_or_create_wallet(db, user_id=user_id, for_update=True)
        wallet.balance = normalize_amount(balance)
        wallet.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(wallet)
        return {
            "wallet_id": wallet.id,
            "balance": serialize_amount(wallet.balance),
            "currency": wallet.currency,
        }
    finally:
        db.close()


def fetch_wallet_state(user_id: int) -> dict[str, Any]:
    db = SessionLocal()
    try:
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
        return {
            "wallet_id": wallet.id if wallet else None,
            "balance": serialize_amount(wallet.balance) if wallet else 0.0,
            "currency": wallet.currency if wallet else "USD",
        }
    finally:
        db.close()


def count_test_transactions(reference_prefix: str) -> int:
    db = SessionLocal()
    try:
        return (
            db.query(Transaction)
            .filter(Transaction.reference_id.like(f"{reference_prefix}%"))
            .count()
        )
    finally:
        db.close()


def make_worker(
    *,
    barrier: threading.Barrier,
    user_id: int,
    debit_amount: Decimal,
    reference_prefix: str,
) -> callable:
    def worker(worker_id: int) -> AttemptResult:
        reference_id = f"{reference_prefix}-{worker_id}"
        db = SessionLocal()
        try:
            barrier.wait(timeout=15)
        except threading.BrokenBarrierError:
            pass

        started_at = time.perf_counter()
        try:
            wallet, transaction = debit_wallet(
                db=db,
                user_id=user_id,
                amount=debit_amount,
                transaction_type="wallet_concurrency_test",
                description=f"Concurrent debit test worker {worker_id}",
                reference_id=reference_id,
            )
            db.commit()
            db.refresh(wallet)
            db.refresh(transaction)
            return AttemptResult(
                worker_id=worker_id,
                status_code=200,
                success=True,
                duration_ms=(time.perf_counter() - started_at) * 1000,
                reference_id=reference_id,
                transaction_id=transaction.id,
                balance_after=serialize_amount(wallet.balance),
            )
        except InsufficientBalanceError as exc:
            db.rollback()
            return AttemptResult(
                worker_id=worker_id,
                status_code=402,
                success=False,
                duration_ms=(time.perf_counter() - started_at) * 1000,
                reference_id=reference_id,
                error=str(exc),
            )
        except Exception as exc:
            db.rollback()
            return AttemptResult(
                worker_id=worker_id,
                status_code=500,
                success=False,
                duration_ms=(time.perf_counter() - started_at) * 1000,
                reference_id=reference_id,
                error=f"{type(exc).__name__}: {exc}",
            )
        finally:
            db.close()

    return worker


def build_report(
    *,
    results: list[AttemptResult],
    initial_balance: Decimal,
    debit_amount: Decimal,
    final_balance: float,
    transaction_count: int,
) -> dict[str, Any]:
    successes = [result for result in results if result.status_code == 200]
    insufficient = [result for result in results if result.status_code == 402]
    unexpected = [result for result in results if result.status_code not in {200, 402}]

    theoretical_successes = int(initial_balance // debit_amount)
    expected_final_balance = serialize_amount(
        normalize_amount(initial_balance - (debit_amount * len(successes)))
    )

    race_conditions: list[str] = []
    if len(successes) > theoretical_successes:
        race_conditions.append(
            "More debits succeeded than the wallet balance should allow."
        )
    if final_balance < 0:
        race_conditions.append("Final wallet balance dropped below zero.")
    if abs(final_balance - expected_final_balance) > 1e-6:
        race_conditions.append(
            "Final wallet balance does not match the committed debit transaction count."
        )
    if transaction_count != len(successes):
        race_conditions.append(
            "Ledger transaction count does not match successful debit attempts."
        )
    if unexpected:
        race_conditions.append("Unexpected non-402 failures occurred during the test.")

    return {
        "summary": {
            "attempted_requests": len(results),
            "successful_transactions": len(successes),
            "failed_transactions_402": len(insufficient),
            "unexpected_failures": len(unexpected),
            "theoretical_success_limit": theoretical_successes,
            "initial_balance": serialize_amount(initial_balance),
            "debit_amount": serialize_amount(debit_amount),
            "expected_final_balance": expected_final_balance,
            "final_wallet_balance": final_balance,
            "ledger_transaction_count": transaction_count,
        },
        "race_conditions": race_conditions,
        "sample_successes": [asdict(item) for item in successes[:5]],
        "sample_failures": [asdict(item) for item in (insufficient + unexpected)[:5]],
        "all_status_codes": sorted({result.status_code for result in results}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Concurrent wallet debit stress test for Flowora.")
    parser.add_argument("--email", default="wallet-load-test@flowora.local")
    parser.add_argument("--password", default="FloworaWallet123!")
    parser.add_argument("--requests", type=int, default=50, help="Concurrent debit attempts to run.")
    parser.add_argument("--initial-balance", type=Decimal, default=Decimal("10.0"))
    parser.add_argument("--debit-amount", type=Decimal, default=Decimal("1.0"))
    parser.add_argument("--output-json", default="", help="Optional path to write the report JSON.")
    args = parser.parse_args()

    if args.requests < 1:
        raise SystemExit("--requests must be at least 1")
    if args.debit_amount <= 0:
        raise SystemExit("--debit-amount must be positive")
    if args.initial_balance < 0:
        raise SystemExit("--initial-balance cannot be negative")

    user_id = ensure_test_user(args.email, args.password)
    wallet_state = reset_wallet(user_id, normalize_amount(args.initial_balance))
    reference_prefix = f"wallet-load-{uuid.uuid4().hex}"
    barrier = threading.Barrier(args.requests)
    worker = make_worker(
        barrier=barrier,
        user_id=user_id,
        debit_amount=normalize_amount(args.debit_amount),
        reference_prefix=reference_prefix,
    )

    started_at = time.perf_counter()
    results: list[AttemptResult] = []
    with ThreadPoolExecutor(max_workers=args.requests) as executor:
        futures = [executor.submit(worker, worker_id) for worker_id in range(1, args.requests + 1)]
        for future in as_completed(futures):
            results.append(future.result())
    elapsed_ms = (time.perf_counter() - started_at) * 1000

    final_wallet = fetch_wallet_state(user_id)
    transaction_count = count_test_transactions(reference_prefix)
    report = build_report(
        results=sorted(results, key=lambda item: item.worker_id),
        initial_balance=normalize_amount(args.initial_balance),
        debit_amount=normalize_amount(args.debit_amount),
        final_balance=final_wallet["balance"],
        transaction_count=transaction_count,
    )
    report["metadata"] = {
        "user_id": user_id,
        "wallet_id": wallet_state["wallet_id"],
        "currency": wallet_state["currency"],
        "reference_prefix": reference_prefix,
        "elapsed_ms": round(elapsed_ms, 2),
    }

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0 if not report["race_conditions"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
