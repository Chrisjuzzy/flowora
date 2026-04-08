from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Iterable, Tuple

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from models.monetization import Transaction, Wallet, WalletCharge


MONEY_QUANTUM = Decimal("0.000001")
ZERO_DECIMAL = Decimal("0.000000")


class WalletError(Exception):
    """Base error for wallet operations."""


class InsufficientBalanceError(WalletError):
    """Raised when a debit would overdraw the wallet."""


def normalize_amount(value: Decimal | float | int | str | None) -> Decimal:
    if value is None:
        return ZERO_DECIMAL
    if isinstance(value, Decimal):
        amount = value
    else:
        amount = Decimal(str(value))
    return amount.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def serialize_amount(value: Decimal | float | int | str | None) -> float:
    return float(normalize_amount(value))


def _ensure_wallet_row(db: Session, user_id: int, currency: str = "USD") -> None:
    dialect_name = db.bind.dialect.name if db.bind is not None else ""

    if dialect_name == "postgresql":
        stmt = (
            pg_insert(Wallet.__table__)
            .values(user_id=user_id, balance=ZERO_DECIMAL, currency=currency)
            .on_conflict_do_nothing(index_elements=[Wallet.user_id])
        )
        db.execute(stmt)
        db.flush()
        return

    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if wallet:
        return

    nested = db.begin_nested()
    try:
        db.add(Wallet(user_id=user_id, balance=ZERO_DECIMAL, currency=currency))
        db.flush()
        nested.commit()
    except Exception:
        nested.rollback()


def get_or_create_wallet(
    db: Session,
    user_id: int,
    currency: str = "USD",
    for_update: bool = False
) -> Wallet:
    _ensure_wallet_row(db, user_id=user_id, currency=currency)
    query = db.query(Wallet).filter(Wallet.user_id == user_id)
    if for_update:
        query = query.with_for_update()
    wallet = query.one()
    wallet.balance = normalize_amount(wallet.balance)
    return wallet


def get_wallets_for_update(
    db: Session,
    user_ids: Iterable[int],
    currency: str = "USD"
) -> Dict[int, Wallet]:
    ordered_ids = sorted({user_id for user_id in user_ids})
    if not ordered_ids:
        return {}

    for user_id in ordered_ids:
        _ensure_wallet_row(db, user_id=user_id, currency=currency)

    wallets = (
        db.query(Wallet)
        .filter(Wallet.user_id.in_(ordered_ids))
        .order_by(Wallet.user_id.asc())
        .with_for_update()
        .all()
    )
    wallet_map = {wallet.user_id: wallet for wallet in wallets}
    for wallet in wallet_map.values():
        wallet.balance = normalize_amount(wallet.balance)
    return wallet_map


def lock_wallet_charge(
    db: Session,
    charge_id: int,
    wallet_id: int
) -> WalletCharge | None:
    return (
        db.query(WalletCharge)
        .filter(WalletCharge.id == charge_id, WalletCharge.wallet_id == wallet_id)
        .with_for_update()
        .first()
    )


def _create_transaction(
    db: Session,
    wallet_id: int,
    amount: Decimal,
    transaction_type: str,
    description: str,
    reference_id: str | None = None
) -> Transaction:
    transaction = Transaction(
        wallet_id=wallet_id,
        amount=normalize_amount(amount),
        type=transaction_type,
        description=description,
        reference_id=reference_id,
    )
    db.add(transaction)
    return transaction


def credit_wallet(
    db: Session,
    user_id: int,
    amount: Decimal | float | int | str,
    transaction_type: str,
    description: str,
    reference_id: str | None = None,
    currency: str = "USD"
) -> Tuple[Wallet, Transaction]:
    normalized_amount = normalize_amount(amount)
    if normalized_amount <= ZERO_DECIMAL:
        raise ValueError("Credit amount must be positive")

    wallet = get_or_create_wallet(db, user_id=user_id, currency=currency, for_update=True)
    wallet.balance = normalize_amount(wallet.balance) + normalized_amount
    wallet.updated_at = datetime.utcnow()
    transaction = _create_transaction(
        db=db,
        wallet_id=wallet.id,
        amount=normalized_amount,
        transaction_type=transaction_type,
        description=description,
        reference_id=reference_id,
    )
    db.flush()
    return wallet, transaction


def debit_wallet(
    db: Session,
    user_id: int,
    amount: Decimal | float | int | str,
    transaction_type: str,
    description: str,
    reference_id: str | None = None,
    currency: str = "USD"
) -> Tuple[Wallet, Transaction]:
    normalized_amount = normalize_amount(amount)
    if normalized_amount <= ZERO_DECIMAL:
        raise ValueError("Debit amount must be positive")

    wallet = get_or_create_wallet(db, user_id=user_id, currency=currency, for_update=True)
    current_balance = normalize_amount(wallet.balance)
    if current_balance < normalized_amount:
        raise InsufficientBalanceError(
            f"Insufficient wallet balance. Required {normalized_amount}, available {current_balance}."
        )

    wallet.balance = current_balance - normalized_amount
    wallet.updated_at = datetime.utcnow()
    transaction = _create_transaction(
        db=db,
        wallet_id=wallet.id,
        amount=-normalized_amount,
        transaction_type=transaction_type,
        description=description,
        reference_id=reference_id,
    )
    db.flush()
    return wallet, transaction


def transfer_between_wallets(
    db: Session,
    source_user_id: int,
    destination_user_id: int,
    amount: Decimal | float | int | str,
    source_transaction_type: str,
    destination_transaction_type: str,
    source_description: str,
    destination_description: str,
    destination_amount: Decimal | float | int | str | None = None,
    reference_id: str | None = None,
    currency: str = "USD"
) -> tuple[Wallet, Wallet]:
    if source_user_id == destination_user_id:
        raise ValueError("Source and destination wallets must be different")

    normalized_amount = normalize_amount(amount)
    normalized_destination_amount = (
        normalize_amount(destination_amount)
        if destination_amount is not None
        else normalized_amount
    )
    if normalized_amount <= ZERO_DECIMAL:
        raise ValueError("Transfer amount must be positive")
    if normalized_destination_amount < ZERO_DECIMAL:
        raise ValueError("Destination amount cannot be negative")

    wallets = get_wallets_for_update(
        db,
        user_ids=[source_user_id, destination_user_id],
        currency=currency,
    )
    source_wallet = wallets[source_user_id]
    destination_wallet = wallets[destination_user_id]

    source_balance = normalize_amount(source_wallet.balance)
    if source_balance < normalized_amount:
        raise InsufficientBalanceError(
            f"Insufficient wallet balance. Required {normalized_amount}, available {source_balance}."
        )

    now = datetime.utcnow()
    source_wallet.balance = source_balance - normalized_amount
    destination_wallet.balance = (
        normalize_amount(destination_wallet.balance) + normalized_destination_amount
    )
    source_wallet.updated_at = now
    destination_wallet.updated_at = now

    _create_transaction(
        db=db,
        wallet_id=source_wallet.id,
        amount=-normalized_amount,
        transaction_type=source_transaction_type,
        description=source_description,
        reference_id=reference_id,
    )
    _create_transaction(
        db=db,
        wallet_id=destination_wallet.id,
        amount=normalized_destination_amount,
        transaction_type=destination_transaction_type,
        description=destination_description,
        reference_id=reference_id,
    )
    db.flush()
    return source_wallet, destination_wallet
