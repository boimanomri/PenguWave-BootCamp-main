from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, TEXT
from pymongo import IndexModel

from app.config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_uri)
    return _client


def get_db():
    return get_client()["penguwave"]


# ── Collection accessors ──────────────────────────────────────────────────────

def users_col():
    return get_db()["users"]


def events_col():
    return get_db()["events"]


def tokens_col():
    return get_db()["invalidated_tokens"]


def audit_col():
    return get_db()["audit_logs"]


# ── Index definitions ─────────────────────────────────────────────────────────

async def create_indexes() -> None:
    # users ───────────────────────────────────────────────────────────────────
    await users_col().create_indexes([
        IndexModel([("email", ASCENDING)], unique=True),
        IndexModel([("id", ASCENDING)], unique=True),
        IndexModel([("role", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
    ])

    # events ──────────────────────────────────────────────────────────────────
    await events_col().create_indexes([
        # Unique lookup by event ID
        IndexModel([("id", ASCENDING)], unique=True),

        # Default sort: newest first
        IndexModel([("timestamp", DESCENDING)]),

        # Severity filter + time sort — the most common combined query
        IndexModel([("severity", ASCENDING), ("timestamp", DESCENDING)]),

        # Tag filter (array field — MongoDB indexes each element automatically)
        IndexModel([("tags", ASCENDING)]),

        # Full-text search across the most useful fields.
        # Weights control relevance ranking:
        #   title × 10 → exact title hit ranks highest
        #   tags  × 5  → tag match outranks body text
        #   assetHostname × 3 → hostname search (e.g. "prod-web-03")
        #   description × 1  → broad body-text catch-all
        # sourceIp / assetIp are kept as exact-match indexes below
        # because IPs don't benefit from stemming/tokenisation.
        IndexModel(
            [
                ("title", TEXT),
                ("description", TEXT),
                ("tags", TEXT),
                ("assetHostname", TEXT),
            ],
            weights={"title": 10, "tags": 5, "assetHostname": 3, "description": 1},
            name="events_text_search",
        ),

        # Exact IP lookups (future: "show all events from this IP")
        IndexModel([("sourceIp", ASCENDING)]),
        IndexModel([("assetIp", ASCENDING)]),

        # Future: per-user event filtering with time sort
        IndexModel([("userId", ASCENDING), ("timestamp", DESCENDING)]),
    ])

    # invalidated_tokens ──────────────────────────────────────────────────────
    await tokens_col().create_indexes([
        IndexModel([("jti", ASCENDING)], unique=True),
        # TTL index — MongoDB auto-deletes documents after expires_at passes
        IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
    ])

    # audit_logs ──────────────────────────────────────────────────────────────
    await audit_col().create_indexes([
        IndexModel([("timestamp", DESCENDING)]),
        IndexModel([("user_id", ASCENDING), ("timestamp", DESCENDING)]),
        IndexModel([("event_type", ASCENDING), ("timestamp", DESCENDING)]),
    ])


async def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
