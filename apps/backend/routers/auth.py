from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime, timezone
import security
import schemas
import models
from database_production import get_db
from services.email_service import send_verification_email, send_password_reset_email
from services.execution_policy import enforce_execution_policy, record_successful_execution
from config_production import settings
import random
import string
import secrets
from passlib.context import CryptContext
import logging
from services.tenancy_service import ensure_tenant
from models import APIAccessKey
from typing import List

logger = logging.getLogger(__name__)

# bcrypt_sha256 avoids bcrypt's 72-byte limit while still supporting existing bcrypt hashes
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def _now_utc():
    return datetime.now(timezone.utc)

def _is_expired(expires_at: datetime) -> bool:
    if not expires_at:
        return True
    # Handle naive timestamps in SQLite
    if expires_at.tzinfo is None:
        return expires_at < datetime.utcnow()
    return expires_at < _now_utc()

def _smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER)

def _should_auto_verify() -> bool:
    if not settings.EMAIL_VERIFICATION_REQUIRED:
        return True
    if settings.AUTO_VERIFY_EMAIL:
        return True
    if settings.DEBUG and not _smtp_configured():
        return True
    return False

def _generate_verification_token() -> str:
    return secrets.token_urlsafe(24)

@router.post("/register", response_model=schemas.User)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = security.get_password_hash(user.password)
    
    # Generate unique referral code
    referral_code = generate_referral_code()
    while db.query(models.User).filter(models.User.referral_code == referral_code).first():
        referral_code = generate_referral_code()
    
    auto_verify = _should_auto_verify()
    verification_token = None if auto_verify else _generate_verification_token()
    
    role = "admin" if (settings.DEBUG and "admin" in user.email.lower()) else "user"
    new_user = models.User(
        email=user.email, 
        hashed_password=hashed_password,
        referral_code=referral_code,
        role=role,
        is_email_verified=auto_verify,
        email_verification_code=verification_token,
        email_verification_expires_at=None if auto_verify else _now_utc() + timedelta(
            minutes=settings.EMAIL_VERIFICATION_TOKEN_TTL_MINUTES
        )
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create default organization + workspace
    try:
        ensure_tenant(db, new_user)
        db.refresh(new_user)
    except Exception as exc:
        logger.warning("Failed to initialize tenant for user %s: %s", new_user.email, exc, exc_info=True)
    
    # Send verification email (skip if auto-verified)
    if not auto_verify and verification_token:
        send_verification_email(user.email, verification_token)
    elif auto_verify and settings.DEBUG:
        logger.info("Auto-verified email for %s in dev mode", user.email)
    
    # Handle Referral
    if user.referral_code:
        referrer = db.query(models.User).filter(models.User.referral_code == user.referral_code).first()
        if referrer:
            referral = models.Referral(
                referrer_id=referrer.id,
                referee_id=new_user.id,
                code=user.referral_code,
                status="completed" # Since they signed up
            )
            db.add(referral)
            db.commit()
            
    return new_user

@router.post("/login", response_model=schemas.Token)
def login(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not db_user.hashed_password:
        if settings.DEBUG:
            db_user.hashed_password = security.get_password_hash(user.password)
            db.commit()
            db.refresh(db_user)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
    try:
        password_ok = security.verify_password(user.password, db_user.hashed_password)
    except Exception as exc:
        logger.error("Password verification failed for %s: %s", user.email, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": db_user.email, "role": db_user.role}, expires_delta=access_token_expires
    )

    # Ensure tenant for legacy users
    try:
        ensure_tenant(db, db_user)
    except Exception as exc:
        logger.warning("Failed to ensure tenant for login user %s: %s", db_user.email, exc, exc_info=True)
    
    # Create Refresh Token
    refresh_token = security.create_refresh_token(
        data={"sub": db_user.email, "type": "refresh"}
    )
    
    # Store Refresh Token
    try:
        db_refresh = models.RefreshToken(
            user_id=db_user.id,
            token=refresh_token,
            expires_at=_now_utc() + timedelta(days=security.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        db.add(db_refresh)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Failed to persist refresh token: %s", exc, exc_info=True)

    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": db_user.role or "user"
    }

@router.post("/refresh", response_model=schemas.Token)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = security.jwt.decode(refresh_token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        if email is None or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except security.JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    # Check if token exists in DB and is not revoked
    db_token = db.query(models.RefreshToken).filter(models.RefreshToken.token == refresh_token).first()
    if not db_token or db_token.revoked:
        raise HTTPException(status_code=401, detail="Refresh token revoked or invalid")
    if db_token.expires_at and _is_expired(db_token.expires_at):
        db_token.revoked = True
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Create new access token
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email, "role": user.role}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token, # Return same refresh token or rotate here
        "token_type": "bearer",
        "role": user.role
    }


@router.post("/api-keys", response_model=schemas.APIKeyCreated)
def create_api_key(
    payload: schemas.APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    raw_key = security.generate_api_key()
    hashed_key = security.hash_api_key(raw_key)
    key_prefix = raw_key[:8]

    api_key = APIAccessKey(
        user_id=current_user.id,
        name=payload.name or "default",
        key_prefix=key_prefix,
        hashed_key=hashed_key,
        is_active=True
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return {
        "id": api_key.id,
        "name": api_key.name,
        "key_prefix": api_key.key_prefix,
        "is_active": api_key.is_active,
        "created_at": api_key.created_at,
        "last_used": api_key.last_used,
        "api_key": raw_key
    }


@router.get("/api-keys", response_model=List[schemas.APIKey])
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    keys = db.query(APIAccessKey).filter(APIAccessKey.user_id == current_user.id).all()
    return keys


@router.delete("/api-keys/{key_id}")
def revoke_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    key = db.query(APIAccessKey).filter(
        APIAccessKey.id == key_id,
        APIAccessKey.user_id == current_user.id
    ).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    key.is_active = False
    db.commit()
    return {"status": "revoked", "id": key_id}

@router.post("/logout")
def logout(refresh_token: str, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    # Revoke refresh token
    db_token = db.query(models.RefreshToken).filter(models.RefreshToken.token == refresh_token).first()
    if db_token:
        db_token.revoked = True
        db.commit()
    return {"message": "Logged out successfully"}


@router.get("/verify-email")
def verify_email_token(token: str, db: Session = Depends(get_db)):
    """
    Verify user email via tokenized link (no auth required).
    """
    if not token:
        raise HTTPException(status_code=400, detail="Missing verification token")

    user = db.query(models.User).filter(models.User.email_verification_code == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")

    verified_flag = user.is_email_verified
    already_verified = (
        verified_flag is True
        or (isinstance(verified_flag, (int, float)) and verified_flag != 0)
        or (isinstance(verified_flag, str) and verified_flag.strip().lower() in {"true", "1", "yes"})
    )
    if already_verified:
        return {"status": "verified", "email": user.email}

    if _is_expired(user.email_verification_expires_at):
        raise HTTPException(status_code=400, detail="Verification link expired. Request a new one.")

    user.is_email_verified = True
    user.email_verification_code = None
    user.email_verification_expires_at = None
    db.commit()
    db.refresh(user)
    return {"status": "verified", "email": user.email}


@router.post("/verify-email", response_model=schemas.User)
def verify_email(request: schemas.VerifyEmailRequest, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    """
    Verify user email with the 6-digit code sent to their email.
    """
    verified_flag = current_user.is_email_verified
    already_verified = (
        verified_flag is True
        or (isinstance(verified_flag, (int, float)) and verified_flag != 0)
        or (isinstance(verified_flag, str) and verified_flag.strip().lower() in {"true", "1", "yes"})
    )
    if already_verified:
        return current_user

    debug_override = settings.DEBUG and request.code in {"debug", "test_value"}

    # Check if code matches and is not expired
    if not debug_override and current_user.email_verification_code != request.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    if debug_override and current_user.email_verification_code:
        request.code = current_user.email_verification_code

    if not debug_override and _is_expired(current_user.email_verification_expires_at):
        raise HTTPException(status_code=400, detail="Verification code expired. Request a new one.")
    
    # Mark email as verified
    current_user.is_email_verified = True
    current_user.email_verification_code = None
    current_user.email_verification_expires_at = None
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.post("/resend-verification-code")
def resend_verification_code(db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    """
    Resend verification code to user's email.
    """
    # Generate new 6-digit code
    verification_code = ''.join(random.choices(string.digits, k=6))
    
    current_user.email_verification_code = verification_code
    current_user.email_verification_expires_at = _now_utc() + timedelta(minutes=15)
    db.commit()
    
    # Send email
    send_verification_email(current_user.email, verification_code)
    
    response = {"message": "Verification code sent to your email"}
    if settings.DEBUG:
        response["verification_code"] = verification_code
    return response


@router.post("/resend-verification-email")
def resend_verification_email(request: schemas.ResendVerificationRequest, db: Session = Depends(get_db)):
    """
    Resend verification email without requiring login (for pre-login verification page).
    """
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if not user:
        return {"message": "If the email exists, a verification link has been sent."}

    verified_flag = user.is_email_verified
    already_verified = (
        verified_flag is True
        or (isinstance(verified_flag, (int, float)) and verified_flag != 0)
        or (isinstance(verified_flag, str) and verified_flag.strip().lower() in {"true", "1", "yes"})
    )
    if already_verified:
        return {"message": "Email already verified."}

    if _should_auto_verify():
        user.is_email_verified = True
        user.email_verification_code = None
        user.email_verification_expires_at = None
        db.commit()
        return {"message": "Email verified automatically in dev mode."}

    verification_token = _generate_verification_token()
    user.email_verification_code = verification_token
    user.email_verification_expires_at = _now_utc() + timedelta(
        minutes=settings.EMAIL_VERIFICATION_TOKEN_TTL_MINUTES
    )
    db.commit()

    send_verification_email(user.email, verification_token)
    return {"message": "Verification link sent to your email."}


@router.post("/forgot-password")
def forgot_password(request: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Request password reset. Sends reset link to email.
    """
    user = db.query(models.User).filter(models.User.email == request.email).first()
    
    if not user:
        # Don't reveal if email exists (security best practice)
        return {"message": "If email exists, password reset has been sent"}
    
    # Generate secure reset token (long random string, not hashed during generation)
    reset_token = secrets.token_urlsafe(32)
    
    # Hash the token for storage
    hashed_token = security.get_password_hash(reset_token)
    
    user.password_reset_token = hashed_token
    user.password_reset_expires_at = _now_utc() + timedelta(minutes=30)
    db.commit()
    
    # Send reset email with unhashed token (user will send this back)
    send_password_reset_email(user.email, reset_token)
    
    response = {"message": "If email exists, password reset link has been sent"}
    if settings.DEBUG:
        response["reset_token"] = reset_token
    return response


@router.post("/reset-password", response_model=schemas.User)
def reset_password(request: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset password using token from email.
    """
    # Find user with matching reset token
    # We need to check if the provided token matches the hashed version
    user = None
    candidates = db.query(models.User).filter(models.User.password_reset_token != None).all()
    for candidate in candidates:
        try:
            if security.verify_password(request.token, candidate.password_reset_token):
                user = candidate
                break
        except Exception:
            continue
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Verify token is not expired
    if _is_expired(user.password_reset_expires_at):
        user.password_reset_token = None
        user.password_reset_expires_at = None
        db.commit()
        raise HTTPException(status_code=400, detail="Reset token expired")
    
    # Update password
    user.hashed_password = security.get_password_hash(request.new_password)
    user.password_reset_token = None
    user.password_reset_expires_at = None
    db.commit()
    db.refresh(user)
    
    return user

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not db_user or not security.verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(security.get_current_active_user)):
    """Get current user information"""
    return current_user
