import uuid

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.database import audit_col, users_col
from app.dependencies import require_admin
from app.models.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def _write_audit(event_type: str, admin_id: str, target_id: str, details: dict = {}):
    import asyncio
    from datetime import datetime, timezone
    async def _insert():
        await audit_col().insert_one({
            "event_type": event_type,
            "user_id": admin_id,
            "target_id": target_id,
            "ip_address": "server",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
        })
    asyncio.create_task(_insert())


# ── GET /api/users ────────────────────────────────────────────────────────────

@router.get("", response_model=list[UserResponse])
async def get_users(admin=Depends(require_admin)):
    cursor = users_col().find({}, {"_id": 0, "hashed_password": 0})
    return await cursor.to_list(length=None)


# ── POST /api/users ───────────────────────────────────────────────────────────

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, admin=Depends(require_admin)):
    new_id = f"usr-{uuid.uuid4().hex[:6]}"
    doc = {
        "id": new_id,
        "email": body.email.lower(),
        "hashed_password": _hash(body.password),
        "role": body.role,
        "status": "active",
        "failed_login_attempts": 0,
        "locked_until": None,
    }
    try:
        await users_col().insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    _write_audit("user_created", admin.id, new_id, {"email": body.email, "role": body.role})
    return UserResponse(id=new_id, email=doc["email"], role=body.role, status="active")


# ── PATCH /api/users/:id ──────────────────────────────────────────────────────

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, body: UserUpdate, admin=Depends(require_admin)):
    if not body.role and not body.status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to update")

    user = await users_col().find_one({"id": user_id}, {"_id": 0, "hashed_password": 0})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent removing the last admin
    if body.role and body.role != "admin" and user["role"] == "admin":
        admin_count = await users_col().count_documents({"role": "admin"})
        if admin_count <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove last admin")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    await users_col().update_one({"id": user_id}, {"$set": updates})
    _write_audit("user_updated", admin.id, user_id, updates)

    updated = {**user, **updates}
    return UserResponse(**updated)


# ── DELETE /api/users/:id ─────────────────────────────────────────────────────

@router.delete("/{user_id}")
async def delete_user(user_id: str, admin=Depends(require_admin)):
    # Cannot delete yourself
    if user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete your own account")

    user = await users_col().find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Cannot delete the last admin
    if user["role"] == "admin":
        admin_count = await users_col().count_documents({"role": "admin"})
        if admin_count <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete last admin")

    await users_col().delete_one({"id": user_id})
    _write_audit("user_deleted", admin.id, user_id, {"email": user["email"]})
    return {"message": "User deleted"}
