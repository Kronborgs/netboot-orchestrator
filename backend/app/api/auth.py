"""Authentication API — first-run setup, login, token verification."""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

from ..database import Database

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get("AUTH_SECRET_KEY", "CHANGE_ME_in_production_use_a_long_random_string")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("AUTH_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 h


# ---------------------------------------------------------------------------
# Password / JWT helpers
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _create_access_token(data: dict, expires_in: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + (expires_in or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload["exp"] = expire
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# FastAPI dependencies — re-exported so v1.py can import them
# ---------------------------------------------------------------------------

def get_db() -> Database:
    return Database()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Database = Depends(get_db),
) -> Optional[dict]:
    """Return the user dict for a valid JWT, or None for no / invalid token."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            return None
        user = db.get_user(username)
        return user
    except JWTError:
        return None


async def require_admin(
    current_user: Optional[dict] = Depends(get_current_user),
):
    """Dependency that raises 401/403 unless the caller is an authenticated admin."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class SetupRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserResponse(BaseModel):
    username: str
    role: str


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/setup-status")
async def setup_status(db: Database = Depends(get_db)):
    """Return whether an admin user has been created yet."""
    return {"has_admin": db.has_admin()}


@router.post("/setup", response_model=TokenResponse)
async def first_run_setup(body: SetupRequest, db: Database = Depends(get_db)):
    """Create the first admin account (only works when no admin exists yet)."""
    if db.has_admin():
        raise HTTPException(status_code=409, detail="Admin account already exists")
    if len(body.username.strip()) < 3:
        raise HTTPException(status_code=422, detail="Username must be at least 3 characters")
    if len(body.password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")

    hashed = _hash_password(body.password)
    user = db.create_user(body.username.strip(), hashed, role="admin")

    token = _create_access_token({"sub": user["username"], "role": user["role"]})
    return TokenResponse(access_token=token, role=user["role"])


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Database = Depends(get_db),
):
    """Authenticate and return a JWT."""
    user = db.get_user(form_data.username)
    if not user or not _verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = _create_access_token({"sub": user["username"], "role": user["role"]})
    return TokenResponse(access_token=token, role=user["role"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(require_admin)):
    """Return calling user's profile (requires valid token)."""
    return UserResponse(username=current_user["username"], role=current_user["role"])
