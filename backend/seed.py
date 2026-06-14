"""
Seed script — runs automatically on first startup via main.py lifespan.
Inserts events and initial users only when the collections are empty.
Also creates all MongoDB indexes (idempotent — safe to call every boot).
"""
import asyncio
import json
import os
from pathlib import Path

import bcrypt
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from app.database import audit_col, create_indexes, events_col, users_col


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

MOCK_EVENTS_PATH = Path(__file__).parent.parent / "data" / "mock_events.json"

INITIAL_USERS = [
    {
        "id": "usr-001",
        "email": "admin@penguwave.io",
        "password": os.environ["SEED_ADMIN_PASSWORD"],
        "role": "admin",
        "status": "active",
    },
    {
        "id": "usr-002",
        "email": "analyst@penguwave.io",
        "password": os.environ["SEED_ANALYST_PASSWORD"],
        "role": "analyst",
        "status": "active",
    },
    {
        "id": "usr-003",
        "email": "viewer@penguwave.io",
        "password": os.environ["SEED_VIEWER_PASSWORD"],
        "role": "viewer",
        "status": "disabled",
    },
]


async def seed() -> None:
    await create_indexes()

    # ── Events ────────────────────────────────────────────────────────────────
    if await events_col().count_documents({}) == 0:
        raw = json.loads(MOCK_EVENTS_PATH.read_text())
        # Deduplicate on id before inserting
        seen: set[str] = set()
        unique = []
        for evt in raw:
            if evt["id"] not in seen:
                seen.add(evt["id"])
                unique.append(evt)
        await events_col().insert_many(unique)
        print(f"[seed] Inserted {len(unique)} events")
    else:
        print("[seed] Events already present — skipping")

    # ── Users ─────────────────────────────────────────────────────────────────
    if await users_col().count_documents({}) == 0:
        docs = []
        for u in INITIAL_USERS:
            docs.append({
                "id": u["id"],
                "email": u["email"],
                "hashed_password": hash_password(u["password"]),
                "role": u["role"],
                "status": u["status"],
                "failed_login_attempts": 0,
                "locked_until": None,
            })
        await users_col().insert_many(docs)
        print(f"[seed] Inserted {len(docs)} users")
    else:
        print("[seed] Users already present — skipping")

    print("[seed] Done — indexes and data ready")


if __name__ == "__main__":
    asyncio.run(seed())
