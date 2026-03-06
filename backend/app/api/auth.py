"""Authentication API — first-run setup, login, token verification, password reset."""

import os
import secrets
import smtplib
import logging
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
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
RESET_TOKEN_EXPIRE_MINUTES = 60  # 1 hour


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
# Email helper
# ---------------------------------------------------------------------------

def _send_email(db: Database, to: str, subject: str, body: str) -> None:
    """Send an email using the stored SMTP settings. Raises on failure."""
    s = db.get_smtp_settings()
    if not s.get("host") or not s.get("from_address"):
        raise RuntimeError("SMTP not configured — set host and From address in Administration → SMTP")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = f"{s.get('from_name', 'Netboot Orchestrator')} <{s['from_address']}>"
    msg["To"] = to

    port = int(s.get("port", 587))
    if s.get("use_ssl"):
        smtp = smtplib.SMTP_SSL(s["host"], port, timeout=15)
    else:
        smtp = smtplib.SMTP(s["host"], port, timeout=15)
        if s.get("use_tls"):
            smtp.starttls()
    if s.get("username") and s.get("password"):
        smtp.login(s["username"], s["password"])
    smtp.sendmail(s["from_address"], [to], msg.as_string())
    smtp.quit()


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
    if current_user.get("role") not in ("admin", "super_user"):
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


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "admin"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserResponse(BaseModel):
    username: str
    role: str


class UserListItem(BaseModel):
    username: str
    role: str
    created_at: str


class SetEmailRequest(BaseModel):
    email: str


class ForgotPasswordRequest(BaseModel):
    identifier: str   # username or email address
    base_url: str     # frontend origin so we can build the reset link


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


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
    db.log_audit("system", "user.created", user["username"], "First-run setup")

    token = _create_access_token({"sub": user["username"], "role": user["role"]})
    return TokenResponse(access_token=token, role=user["role"])


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Database = Depends(get_db),
):
    """Authenticate and return a JWT. Reports 'Username not found' vs 'Wrong password'."""
    user = db.get_user(form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not _verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = _create_access_token({"sub": user["username"], "role": user["role"]})
    return TokenResponse(access_token=token, role=user["role"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(require_admin)):
    """Return calling user's profile (requires valid token)."""
    return UserResponse(username=current_user["username"], role=current_user["role"])


@router.get("/users", response_model=list)
async def list_users(
    _: dict = Depends(require_admin),
    db: Database = Depends(get_db),
):
    """List all users (admin only)."""
    return db.list_users()


@router.post("/users")
async def create_user(
    body: CreateUserRequest,
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_db),
):
    """Create an additional user account (admin only)."""
    uname = body.username.strip()
    if len(uname) < 3:
        raise HTTPException(status_code=422, detail="Username must be at least 3 characters")
    if len(body.password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")
    if body.role not in ("admin", "super_user"):
        raise HTTPException(status_code=422, detail="Invalid role; must be 'admin' or 'super_user'")
    if db.get_user(uname):
        raise HTTPException(status_code=409, detail="Username already exists")
    hashed = _hash_password(body.password)
    user = db.create_user(uname, hashed, role=body.role)
    db.log_audit(current_user["username"], "user.created", uname, f"role={body.role}")
    return {k: v for k, v in user.items() if k != "hashed_password"}


@router.put("/users/{username}/email")
async def set_user_email(
    username: str,
    body: SetEmailRequest,
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_db),
):
    """Set or update the email address for a user (admin only)."""
    result = db.update_user_email(username, body.email)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.log_audit(current_user["username"], "user.email_updated", username, body.email)
    return result


@router.delete("/users/{username}")
async def delete_user(
    username: str,
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_db),
):
    """Delete a user account (admin only). Allows deleting last admin to trigger re-setup."""
    if not db.get_user(username):
        raise HTTPException(status_code=404, detail="User not found")
    db.delete_user(username)
    db.log_audit(current_user["username"], "user.deleted", username)
    logger.info("User '%s' deleted by '%s'", username, current_user["username"])
    return {"deleted": username}


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: Database = Depends(get_db),
):
    """
    Request a password reset link.
    - identifier is a username → 404 if not found (explicit, so user knows typo)
    - identifier looks like an email → always return 200 (privacy: don't reveal if registered)
    """
    identifier = body.identifier.strip()
    is_email = "@" in identifier

    if is_email:
        user = db.get_user_by_email(identifier)
        if not user or not user.get("email"):
            # Security: don't reveal whether this email is registered
            return {"ok": True, "message": "If that address is registered, a reset link has been sent."}
    else:
        user = db.get_user(identifier)
        if not user:
            raise HTTPException(status_code=404, detail="Username not found")
        if not user.get("email"):
            raise HTTPException(
                status_code=422,
                detail="No email address is set for this account. Ask an administrator to add one."
            )

    # Generate reset token
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)).isoformat()
    db.set_reset_token(user["username"], token, expires)

    reset_url = f"{body.base_url.rstrip('/')}?token={token}"
    email_body = (
        f"Hello {user['username']},\n\n"
        f"A password reset was requested for your Netboot Orchestrator account.\n\n"
        f"Click the link below to set a new password (valid for {RESET_TOKEN_EXPIRE_MINUTES} minutes):\n\n"
        f"  {reset_url}\n\n"
        f"If you did not request this, you can safely ignore this email.\n\n"
        f"— Netboot Orchestrator"
    )

    try:
        _send_email(db, user["email"], "Netboot Orchestrator — Password Reset", email_body)
        db.log_audit("system", "password.reset_requested", user["username"], f"sent to {user['email']}")
    except Exception as exc:
        logger.error("Failed to send reset email: %s", exc)
        raise HTTPException(status_code=502, detail=f"Could not send email: {exc}")

    return {"ok": True, "message": "Password reset link sent."}


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: Database = Depends(get_db),
):
    """Apply a password reset using a valid token."""
    if len(body.password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")

    user = db.get_user_by_reset_token(body.token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    # Check expiry
    expires_str = user.get("reset_token_expires", "")
    try:
        expires_dt = datetime.fromisoformat(expires_str)
        if datetime.now(timezone.utc) > expires_dt:
            db.clear_reset_token(user["username"])
            raise HTTPException(status_code=400, detail="Reset token has expired")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid reset token")

    hashed = _hash_password(body.password)
    db.reset_password(user["username"], hashed)
    db.log_audit("system", "password.reset", user["username"])
    return {"ok": True, "username": user["username"]}

