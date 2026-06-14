import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr

from app.config import settings
from app.database import audit_col, tokens_col, users_col
from app.dependencies import get_current_user, validate_api_key
from app.limiter import limiter
from app.models.user import UserResponse

router = APIRouter()
_bearer = HTTPBearer()

# Dummy hash — used when user not found so response time is identical
# to the case where the user exists but password is wrong (prevents timing attack)
_DUMMY_HASH = bcrypt.hashpw(b"dummy", bcrypt.gensalt()).decode()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def _write_audit(event_type: str, user_id: str | None, ip: str, details: dict = {}):
    import asyncio
    async def _insert():
        await audit_col().insert_one({
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": ip,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
        })
    asyncio.create_task(_insert())


def _issue_token(user_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expiry_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ── POST /api/auth/login ──────────────────────────────────────────────────────

@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    _: None = Depends(validate_api_key),
):
    ip = request.client.host
    invalid_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
    )

    user = await users_col().find_one({"email": body.email})

    # Always run bcrypt to prevent timing-based user enumeration
    candidate_hash = user["hashed_password"] if user else _DUMMY_HASH
    password_ok = bcrypt.checkpw(body.password.encode(), candidate_hash.encode())

    if not user or not password_ok:
        if user:
            # Increment failed attempts and lock if threshold reached
            attempts = user.get("failed_login_attempts", 0) + 1
            update: dict = {"$set": {"failed_login_attempts": attempts}}
            if attempts >= 3:
                locked_until = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
                update["$set"]["locked_until"] = locked_until
            await users_col().update_one({"email": body.email}, update)
            _write_audit("login_failure", user["id"], ip, {"reason": "wrong_password"})
        else:
            _write_audit("login_failure", None, ip, {"reason": "unknown_email"})
        raise invalid_error

    # Check account lock (after password check — same error either way)
    locked_until = user.get("locked_until")
    if locked_until:
        lock_dt = datetime.fromisoformat(locked_until)
        if datetime.now(timezone.utc) < lock_dt:
            _write_audit("login_failure", user["id"], ip, {"reason": "account_locked"})
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Account temporarily locked. Try again later.",
            )

    # Check disabled status
    if user["status"] == "disabled":
        _write_audit("login_failure", user["id"], ip, {"reason": "account_disabled"})
        raise invalid_error

    # Success — reset lockout, issue token
    await users_col().update_one(
        {"email": body.email},
        {"$set": {"failed_login_attempts": 0, "locked_until": None}},
    )

    token = _issue_token(user["id"], user["role"])
    _write_audit("login_success", user["id"], ip)

    return {
        "token": token,
        "user": {"id": user["id"], "email": user["email"], "role": user["role"]},
    }


# ── POST /api/auth/logout ─────────────────────────────────────────────────────

@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    current_user: UserResponse = Depends(get_current_user),
):
    token = credentials.credentials
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    jti = payload["jti"]
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

    await tokens_col().insert_one({
        "jti": jti,
        "invalidated_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": exp,
    })
    _write_audit("logout", current_user.id, "server")
    return {"message": "Logged out"}


# ── GET /api/auth/me ──────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def me(current_user: UserResponse = Depends(get_current_user)):
    return current_user
