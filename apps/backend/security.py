from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from database_production import get_db
from models import User, APIAccessKey
from tenancy import set_current_tenant

from config_production import settings
import secrets
from datetime import datetime

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# pbkdf2_sha256 avoids bcrypt backend issues in slim images
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if "type" not in to_encode:
        to_encode["type"] = "access"
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def generate_api_key() -> str:
    return f"aab_{secrets.token_urlsafe(32)}"


def hash_api_key(key: str) -> str:
    return pwd_context.hash(key)


def verify_api_key(key: str, hashed_key: str) -> bool:
    return pwd_context.verify(key, hashed_key)


def _normalize_role(role: Optional[str]) -> str:
    return (role or "").strip().lower().replace("-", "_").replace(" ", "_")


def _is_truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return False


def _resolve_user_from_api_key(api_key: str, db: Session) -> Optional[User]:
    if not api_key:
        return None
    prefix = api_key[:8]
    candidates = db.query(APIAccessKey).filter(
        APIAccessKey.key_prefix == prefix,
        APIAccessKey.is_active == True
    ).all()
    for key in candidates:
        try:
            if verify_api_key(api_key, key.hashed_key):
                key.last_used = datetime.utcnow()
                db.commit()
                db.refresh(key)
                return db.query(User).filter(User.id == key.user_id).first()
        except Exception:
            continue
    return None

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if api_key:
        user = _resolve_user_from_api_key(api_key, db)
        if not user:
            raise credentials_exception
        try:
            set_current_tenant(user.organization_id)
        except Exception:
            pass
        return user

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type", "access")
        if email is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    try:
        set_current_tenant(user.organization_id)
    except Exception:
        pass
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not _is_truthy(current_user.is_active):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_active_user)):
        allowed = {_normalize_role(role) for role in self.allowed_roles}
        user_role = _normalize_role(user.role)
        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted"
            )
        return user
