# PenguWave Backend Architecture

## Table of Contents

1. [Overview](#overview)
2. [Directory Structure](#directory-structure)
3. [Technology Stack & Dependencies](#technology-stack--dependencies)
4. [Configuration & Environment Variables](#configuration--environment-variables)
5. [Application Entry Point & Assembly](#application-entry-point--assembly)
6. [Database Architecture](#database-architecture)
7. [Authentication & Authorization](#authentication--authorization)
8. [Middleware & Request Pipeline](#middleware--request-pipeline)
9. [Rate Limiting](#rate-limiting)
10. [API Endpoints — Complete Reference](#api-endpoints--complete-reference)
11. [Data Models & Schemas](#data-models--schemas)
12. [Dependency Injection](#dependency-injection)
13. [Error Handling](#error-handling)
14. [Audit Logging](#audit-logging)
15. [Seeding & Initialization](#seeding--initialization)
16. [Security Deep Dive](#security-deep-dive)
17. [Key Architectural Decisions](#key-architectural-decisions)

---

## Overview

PenguWave is a security event management platform. Its backend is a **FastAPI** application that exposes a REST API for:

- Authenticating users (JWT-based)
- Managing user accounts (admin-only CRUD)
- Serving security events stored in MongoDB

The server is **fully async** — all I/O goes through async drivers (Motor for MongoDB, async FastAPI route handlers). It targets a single-origin frontend (default: `http://localhost:5173`) and protects every meaningful endpoint with a combination of a static API key and a per-user JWT token.

---

## Directory Structure

```
PenguWave-BootCamp-main/
├── backend/
│   ├── app/
│   │   ├── __init__.py              # empty package marker
│   │   ├── main.py                  # FastAPI app factory, middleware wiring, router registration
│   │   ├── config.py                # Pydantic-settings configuration class
│   │   ├── database.py              # MongoDB client singleton, collection accessors, index creation
│   │   ├── dependencies.py          # FastAPI dependency-injection functions (API key, JWT, admin guard)
│   │   ├── middleware.py            # Custom ASGI middleware for security headers
│   │   ├── limiter.py               # SlowAPI rate-limiter instance
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              # Login, logout, /me
│   │   │   ├── users.py             # Admin user CRUD
│   │   │   └── events.py            # Security event listing and retrieval
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── user.py              # User Pydantic schemas (Create, Update, Response, InDB)
│   │       └── event.py             # Event Pydantic schema (Response)
│   ├── seed.py                      # Startup seeding: indexes, events, initial users
│   ├── requirements.txt             # Pinned Python dependencies
│   ├── .env                         # Local secrets (not committed)
│   ├── .env.example                 # Environment variable template
│   └── docker-compose.yml           # MongoDB 7 service definition
└── data/
    └── mock_events.json             # ~50 realistic security event fixtures
```

---

## Technology Stack & Dependencies

All dependencies are pinned in `requirements.txt`:

| Package | Version | Role |
|---|---|---|
| `fastapi` | 0.115.0 | Web framework (async routing, DI, OpenAPI) |
| `uvicorn[standard]` | 0.32.0 | ASGI server (runs the app) |
| `motor` | 3.6.0 | Async MongoDB driver (wraps PyMongo with asyncio) |
| `pydantic[email]` | 2.10.0 | Data validation, serialization, email type |
| `pydantic-settings` | 2.7.0 | Settings class that reads `.env` files |
| `python-jose[cryptography]` | 3.3.0 | JWT encode/decode |
| `bcrypt` | 4.3.0 | Password hashing |
| `slowapi` | 0.1.9 | Rate limiting for FastAPI |
| `python-multipart` | 0.0.18 | Form data parsing (required by FastAPI) |

**Runtime services:**
- MongoDB 7 (via Docker Compose on `127.0.0.1:27017`)

---

## Configuration & Environment Variables

**File:** `backend/app/config.py`

All configuration lives in a single Pydantic `Settings` class (a `BaseSettings` subclass). It reads values from the `.env` file at startup and validates them.

```
MONGO_USER=penguwave
MONGO_PASSWORD=change_me_strong_password
JWT_SECRET=<64-char hex string>
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=8
API_KEY=<static API key>
CORS_ORIGIN=http://localhost:5173
SEED_ADMIN_PASSWORD=<admin seed password>
SEED_ANALYST_PASSWORD=<analyst seed password>
SEED_VIEWER_PASSWORD=<viewer seed password>
```

**Computed field** (`mongo_uri`): Assembled from `MONGO_USER` and `MONGO_PASSWORD` using `urllib.parse.quote_plus` for URL encoding. The resulting URI points to:

```
mongodb://<user>:<password>@127.0.0.1:27017/penguwave?authSource=admin
```

**Defaults:**
- `JWT_ALGORITHM`: `"HS256"`
- `JWT_EXPIRY_HOURS`: `8`
- `CORS_ORIGIN`: `"http://localhost:5173"`

The settings object is a module-level singleton (`settings = Settings()`) imported wherever configuration values are needed.

---

## Application Entry Point & Assembly

**File:** `backend/app/main.py`

The application is assembled using FastAPI's standard factory pattern with a **lifespan context manager** for startup/shutdown hooks.

### Lifespan

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await seed()        # runs on startup
    yield
    await close_client()  # runs on shutdown
```

- **Startup:** Calls `seed()` which creates MongoDB indexes and inserts initial data if collections are empty.
- **Shutdown:** Calls `close_client()` which gracefully closes the Motor connection.

### App creation

```python
app = FastAPI(
    title="PenguWave API",
    docs_url=None,     # Swagger UI disabled
    redoc_url=None,    # ReDoc disabled
    lifespan=lifespan,
    exception_handlers={RequestValidationError: _clean_validation_error},
)
```

Both interactive API docs (`/docs` and `/redoc`) are disabled, which is intentional for a production-style deployment — no documentation surface is exposed externally.

### Middleware stack (applied bottom-up for requests, top-down for responses)

```python
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Api-Key"],
    allow_credentials=True,
)
```

CORS is configured to allow only the single frontend origin. `allow_credentials=True` is included to support cookie-based auth in the future.

### Rate limiter

```python
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

The limiter instance is attached to app state, which is how SlowAPI resolves it at request time. The exception handler converts `RateLimitExceeded` into a proper JSON 429 response.

### Router registration

```python
app.include_router(auth.router,   prefix="/api/auth")
app.include_router(events.router, prefix="/api/events")
app.include_router(users.router,  prefix="/api/users")
```

### Validation error sanitization

`RequestValidationError` (Pydantic validation failure on incoming request data) is intercepted by a custom handler that:
- Returns HTTP 422
- Strips raw input values from the error response (prevents data leakage)
- Strips internal field paths (prevents internal schema leakage)
- Returns only human-readable messages

---

## Database Architecture

**File:** `backend/app/database.py`

### Client

The Motor async client uses a **singleton pattern**: `get_client()` creates the `AsyncIOMotorClient` on first call and returns the same instance on subsequent calls.

```python
_client: AsyncIOMotorClient | None = None

def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_uri)
    return _client
```

The database is always `penguwave`.

### Collections

Four collection accessor functions return `AsyncIOMotorCollection` objects:

| Function | Collection | Purpose |
|---|---|---|
| `get_users_collection()` | `users` | User accounts, credentials, role, status, lockout |
| `get_events_collection()` | `events` | Security event documents |
| `get_invalidated_tokens_collection()` | `invalidated_tokens` | Revoked JWT JTI values |
| `get_audit_logs_collection()` | `audit_logs` | Action audit trail |

### Indexes

All indexes are created by `create_indexes()`, called on every startup (idempotent — MongoDB ignores existing indexes with the same spec).

#### `users` collection

| Index | Type | Purpose |
|---|---|---|
| `email` | Unique ascending | Enforce email uniqueness; fast lookup on login |
| `id` | Unique ascending | Fast lookup by app-level user ID |
| `role` | Ascending | Admin queries ("list all admins") |
| `status` | Ascending | Filter by active/disabled status |

#### `events` collection

| Index | Type | Purpose |
|---|---|---|
| `id` | Unique ascending | Fast event lookup by app ID |
| `timestamp` | Descending | Default sort (newest first) |
| `(severity, timestamp)` | Compound ascending/descending | Filter by severity + sort by time |
| `tags` | Ascending | Tag-based filtering |
| Full-text on `(title, description, tags, assetHostname)` | Text | Full-text search with weighted relevance |
| `sourceIp` | Ascending | IP-based lookup |
| `assetIp` | Ascending | Asset IP lookup |
| `(userId, timestamp)` | Compound ascending/descending | Per-user event history |

The **full-text index** uses custom weights:
- `title`: weight 10 (most relevant)
- `tags`: weight 5
- `assetHostname`: weight 3
- `description`: weight 1 (least relevant)

#### `invalidated_tokens` collection

| Index | Type | Purpose |
|---|---|---|
| `jti` | Unique ascending | Fast blacklist lookup on every authenticated request |
| `expires_at` | TTL (expireAfterSeconds=0) | Auto-delete documents when their `expires_at` time arrives |

The TTL index means expired token records self-delete — no garbage collection job needed.

#### `audit_logs` collection

| Index | Type | Purpose |
|---|---|---|
| `timestamp` | Descending | Chronological audit queries |
| `(user_id, timestamp)` | Compound ascending/descending | Per-user activity history |
| `(event_type, timestamp)` | Compound ascending/descending | Filter by event type |

---

## Authentication & Authorization

**File:** `backend/app/dependencies.py`

### Dual-layer authentication

Most endpoints require **both** an API key and a JWT token. The two serve different purposes:
- The **API key** (`X-Api-Key` header) identifies the calling application (the frontend). It is a static shared secret.
- The **JWT** (`Authorization: Bearer`) identifies the specific user making the request. It is issued at login and expires after 8 hours.

### API Key Validation

```python
async def validate_api_key(x_api_key: str | None = Header(default=None)):
    if not x_api_key or not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
```

Key detail: `secrets.compare_digest` performs a **constant-time comparison**, preventing timing attacks where an attacker could enumerate the correct key character by character based on response time.

### JWT Token Validation

```python
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
```

Step-by-step flow:

1. Extract the `Authorization: Bearer <token>` header via FastAPI's `HTTPBearer` scheme.
2. Decode the JWT using `python-jose` with `settings.jwt_secret` and `settings.jwt_algorithm`.
3. If the token is expired, malformed, or has an invalid signature → raise `401`.
4. Extract `jti` (JWT ID) from the payload.
5. Query `invalidated_tokens` for a document matching `jti` → if found, the token was revoked (user logged out) → raise `401`.
6. Extract `sub` (user ID) from the payload.
7. Query `users` collection for the user.
8. If user not found → raise `401`.
9. If `user.status == "disabled"` → raise `401`.
10. Return the `UserResponse` object for use in route handlers.

### JWT Token Structure

```json
{
  "sub": "usr-001",
  "role": "admin",
  "jti": "a1b2c3d4-...",
  "iat": 1718000000,
  "exp": 1718028800
}
```

- `sub`: user's app-level ID
- `role`: cached at token issue time (stale if admin changes the user's role before token expires)
- `jti`: UUID, unique per token — used to identify a token for revocation
- `iat`/`exp`: standard JWT issue time and expiration

### Admin Guard

```python
async def require_admin(current_user: UserResponse = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

A thin wrapper around `get_current_user` that enforces the admin role. Used as a dependency on all `/api/users` routes.

### Account Lockout

Brute-force protection is implemented directly in the login handler:
- Failed login attempts are tracked in the `users` document as `failed_login_attempts` (integer).
- After **3 consecutive failures**, `locked_until` is set to `now + 15 minutes` (ISO8601 string).
- On login, if `locked_until` is set and is in the future, the request is rejected with 401 before checking the password.
- On **successful** login, `failed_login_attempts` is reset to 0 and `locked_until` is cleared.

---

## Middleware & Request Pipeline

### Request pipeline (order of execution on inbound request)

```
Client Request
    │
    ▼
CORSMiddleware          (sets Access-Control-* headers; handles OPTIONS preflight)
    │
    ▼
SecurityHeadersMiddleware  (adds X-Content-Type-Options, X-Frame-Options, CSP, etc.)
    │
    ▼
SlowAPI rate limiter    (on decorated endpoints only; checks request count by IP)
    │
    ▼
FastAPI router          (matches path/method, runs endpoint handler)
    │
    ▼
Dependency injection    (validate_api_key, get_current_user, require_admin)
    │
    ▼
Route handler           (business logic, DB queries)
    │
    ▼
Pydantic serialization  (response model validation and JSON encoding)
    │
    ▼
Response (back through middleware layers in reverse)
```

### SecurityHeadersMiddleware

**File:** `backend/app/middleware.py`

A custom Starlette `BaseHTTPMiddleware` that appends security headers to every response:

| Header | Value | Purpose |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | Prevents MIME type sniffing — browser must use the declared content type |
| `X-Frame-Options` | `DENY` | Prevents this page from being embedded in an `<iframe>` (clickjacking protection) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limits referrer information sent with cross-origin requests |
| `Content-Security-Policy` | `default-src 'none'` | Strict CSP — blocks all inline scripts, styles, and external resource loads by default |
| `Cache-Control` | `no-store` | Applied only to `/api/auth/*` endpoints — prevents browsers from caching auth responses |

---

## Rate Limiting

**File:** `backend/app/limiter.py`

SlowAPI is used for rate limiting. The limiter is initialized with:

```python
limiter = Limiter(key_func=get_remote_address)
```

`get_remote_address` extracts the client's IP from `request.client.host`. Rate limits are declared per-endpoint using a decorator:

```python
@limiter.limit("5/minute")
async def login(...):
```

Currently, only the login endpoint is rate-limited (5 requests per minute per IP). When the limit is exceeded, SlowAPI raises `RateLimitExceeded`, which the registered exception handler converts to an HTTP 429 response.

---

## API Endpoints — Complete Reference

### Summary table

| Method | Path | Auth Required | Role | Rate Limit | Status Codes |
|---|---|---|---|---|---|
| `POST` | `/api/auth/login` | API Key | — | 5/min | 200, 401, 429 |
| `POST` | `/api/auth/logout` | Bearer + API Key | Any | — | 200, 401 |
| `GET` | `/api/auth/me` | Bearer | Any | — | 200, 401 |
| `GET` | `/api/users` | Bearer | Admin | — | 200, 401, 403 |
| `POST` | `/api/users` | Bearer | Admin | — | 201, 400, 401, 403 |
| `PATCH` | `/api/users/{user_id}` | Bearer | Admin | — | 200, 400, 401, 403, 404 |
| `DELETE` | `/api/users/{user_id}` | Bearer | Admin | — | 200, 400, 401, 403, 404 |
| `GET` | `/api/events` | Bearer + API Key | Any | — | 200, 401 |
| `GET` | `/api/events/{event_id}` | Bearer + API Key | Any | — | 200, 401, 404 |
| `GET` | `/health` | None | — | — | 200 |

---

### Auth Router (`/api/auth`)

**File:** `backend/app/routers/auth.py`

#### `POST /api/auth/login`

Authenticates a user and returns a JWT.

**Request headers:**
- `X-Api-Key: <api-key>` (required)

**Request body:**
```json
{
  "email": "admin@penguwave.io",
  "password": "AdminPass1"
}
```

**Success response (200):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "usr-001",
    "email": "admin@penguwave.io",
    "role": "admin",
    "status": "active"
  }
}
```

**Failure responses:**
- `401` — Unknown email, wrong password, account locked, or account disabled
- `429` — Rate limit exceeded (5 req/min per IP)

**Internal logic:**
1. Look up user by `email` in the `users` collection.
2. If not found: check password against a dummy hash (timing-attack prevention), log `login_failure` with reason `unknown_email`, return 401.
3. Check `locked_until` — if user is locked, log `login_failure` with reason `account_locked`, return 401.
4. Check `status` — if `"disabled"`, log `login_failure` with reason `account_disabled`, return 401.
5. Verify password with `bcrypt.checkpw`. If wrong: increment `failed_login_attempts`; if count reaches 3, set `locked_until = now + 15min`. Log `login_failure` with reason `wrong_password`. Return 401.
6. On success: reset `failed_login_attempts = 0`, clear `locked_until`. Generate JWT with a unique `jti` (UUID). Log `login_success`. Return token + user.

---

#### `POST /api/auth/logout`

Revokes the current token by adding its `jti` to the blacklist.

**Request headers:**
- `Authorization: Bearer <token>` (required)
- `X-Api-Key: <api-key>` (required)

**Request body:** none

**Success response (200):**
```json
{ "message": "Logged out" }
```

**Internal logic:**
1. Validate API key and JWT via dependencies.
2. Extract `jti` and `exp` from the decoded token payload.
3. Insert `{ jti, expires_at: <token expiry datetime> }` into `invalidated_tokens`.
4. Log `logout` event to audit_logs.

The TTL index on `invalidated_tokens.expires_at` will automatically delete this document once the token would have expired anyway, keeping the collection lean.

---

#### `GET /api/auth/me`

Returns the current authenticated user's profile.

**Request headers:**
- `Authorization: Bearer <token>` (required)

**Success response (200):**
```json
{
  "id": "usr-001",
  "email": "admin@penguwave.io",
  "role": "admin",
  "status": "active"
}
```

---

### Users Router (`/api/users`)

**File:** `backend/app/routers/users.py`

All endpoints require a valid JWT with `role == "admin"`.

#### `GET /api/users`

Returns all users in the system.

**Success response (200):** Array of `UserResponse` objects. The query explicitly excludes `_id` and `hashed_password` from returned documents.

```json
[
  { "id": "usr-001", "email": "admin@penguwave.io", "role": "admin", "status": "active" },
  { "id": "usr-002", "email": "analyst@penguwave.io", "role": "analyst", "status": "active" },
  { "id": "usr-003", "email": "viewer@penguwave.io", "role": "viewer", "status": "disabled" }
]
```

---

#### `POST /api/users`

Creates a new user account.

**Request body:**
```json
{
  "email": "newuser@penguwave.io",
  "password": "NewPass1",
  "role": "analyst"
}
```

**Success response (201):** `UserResponse` of the newly created user.

**Failure responses:**
- `400` — Email already exists in the `users` collection
- `400` — Password fails validation (< 8 chars, no letter, or no digit)

**Internal logic:**
1. Validate password with regex `^(?=.*[A-Za-z])(?=.*\d).{8,}$`.
2. Check if email is already taken — return 400 if so.
3. Generate user ID: `usr-` + 6 random hex characters (`secrets.token_hex(3)`).
4. Hash password with `bcrypt` at cost factor 12.
5. Insert document with `status="active"`, `failed_login_attempts=0`, `locked_until=null`.
6. Log `user_created` to audit_logs (includes creating admin's ID).
7. Return `UserResponse`.

---

#### `PATCH /api/users/{user_id}`

Updates a user's role and/or status. At least one field must be provided.

**Path parameter:** `user_id` — the app-level user ID (e.g., `usr-002`)

**Request body (all fields optional):**
```json
{
  "role": "viewer",
  "status": "disabled"
}
```

**Success response (200):** Updated `UserResponse`.

**Failure responses:**
- `400` — No fields provided in the body
- `400` — Attempting to remove admin role from the last admin account
- `404` — User not found

**Internal logic:**
1. Validate that at least one field is present.
2. Fetch the target user — 404 if not found.
3. If changing role and the target is the last admin, reject with 400.
4. Apply the update to the MongoDB document.
5. Log `user_updated` with the admin's ID and target user ID.

---

#### `DELETE /api/users/{user_id}`

Permanently deletes a user account.

**Path parameter:** `user_id` — the app-level user ID

**Success response (200):**
```json
{ "message": "User deleted" }
```

**Failure responses:**
- `403` — Admin is attempting to delete their own account
- `400` — Attempting to delete the last admin account
- `404` — User not found

**Internal logic:**
1. Check if `user_id == current_user.id` → 403 (cannot self-delete).
2. Fetch the target user → 404 if not found.
3. Check if target is the last admin → 400 if so.
4. Delete the document from `users`.
5. Log `user_deleted` with the deleted user's email.

---

### Events Router (`/api/events`)

**File:** `backend/app/routers/events.py`

Both endpoints require a valid JWT (any role) and a valid API key.

#### `GET /api/events`

Returns all security events sorted by timestamp descending (newest first).

**Success response (200):** Array of `EventResponse` objects. The query excludes the MongoDB `_id` field.

```json
[
  {
    "id": "evt-001",
    "timestamp": "2025-02-18T14:32:01Z",
    "severity": "HIGH",
    "title": "Suspicious process execution detected",
    "description": "Process 'mimikatz.exe' was executed on...",
    "assetHostname": "prod-web-03.penguwave.internal",
    "assetIp": "10.0.3.15",
    "sourceIp": "10.0.5.22",
    "tags": ["credential-theft", "endpoint", "mimikatz"],
    "userId": "usr-002"
  },
  ...
]
```

No filtering, searching, or pagination is currently implemented — the endpoint returns all events. This is a candidate for a future enhancement.

---

#### `GET /api/events/{event_id}`

Returns a single event by its app-level ID.

**Path parameter:** `event_id` — e.g., `evt-001`

**Success response (200):** Single `EventResponse`.

**Failure responses:**
- `404` — No event found with that ID

---

### Health Check

#### `GET /health`

Unauthenticated liveness probe.

**Success response (200):**
```json
{ "status": "ok" }
```

---

## Data Models & Schemas

### User models

**File:** `backend/app/models/user.py`

#### Type aliases

```python
Role   = Literal["admin", "analyst", "viewer"]
Status = Literal["active", "disabled"]
```

#### `UserCreate`

Used as the request body for `POST /api/users`.

| Field | Type | Constraints |
|---|---|---|
| `email` | `EmailStr` | Valid email address |
| `password` | `str` | ≥8 chars, must contain a letter and a digit |
| `role` | `Role` | One of: `admin`, `analyst`, `viewer` |

#### `UserUpdate`

Used as the request body for `PATCH /api/users/{id}`. Both fields are optional.

| Field | Type |
|---|---|
| `role` | `Role \| None` |
| `status` | `Status \| None` |

#### `UserResponse`

The external-facing user schema — returned by list, create, update, and `/me` endpoints. **Never includes the password hash**.

| Field | Type |
|---|---|
| `id` | `str` |
| `email` | `str` |
| `role` | `Role` |
| `status` | `Status` |

#### `UserInDB` (internal only)

The full in-database representation, used by auth logic. Never serialized directly to API responses.

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | — |
| `email` | `str` | — |
| `role` | `Role` | — |
| `status` | `Status` | — |
| `hashed_password` | `str` | bcrypt hash |
| `failed_login_attempts` | `int` | Default: 0 |
| `locked_until` | `str \| None` | ISO8601 datetime string or null |

#### MongoDB document shape (`users` collection)

```json
{
  "_id": ObjectId("..."),
  "id": "usr-001",
  "email": "admin@penguwave.io",
  "hashed_password": "$2b$12$...",
  "role": "admin",
  "status": "active",
  "failed_login_attempts": 0,
  "locked_until": null
}
```

---

### Event models

**File:** `backend/app/models/event.py`

#### Type alias

```python
Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
```

#### `EventResponse`

The only event schema — used for API responses. Configured with `populate_by_name=True` to support both alias and field name access.

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | App-level event ID (e.g., `evt-001`) |
| `timestamp` | `datetime` | Event occurrence time |
| `severity` | `Severity` | One of: LOW, MEDIUM, HIGH, CRITICAL |
| `title` | `str` | Short event title |
| `description` | `str` | Full event description |
| `assetHostname` | `str` | Hostname of the affected asset |
| `assetIp` | `str` | IP address of the affected asset |
| `sourceIp` | `str \| None` | Originating IP, if known |
| `tags` | `list[str]` | Classification tags |
| `userId` | `str \| None` | Associated user ID, if applicable |

#### MongoDB document shape (`events` collection)

```json
{
  "_id": ObjectId("..."),
  "id": "evt-001",
  "timestamp": "2025-02-18T14:32:01Z",
  "severity": "HIGH",
  "title": "Suspicious process execution detected",
  "description": "Process 'mimikatz.exe' was executed on endpoint prod-web-03...",
  "assetHostname": "prod-web-03.penguwave.internal",
  "assetIp": "10.0.3.15",
  "sourceIp": "10.0.5.22",
  "tags": ["credential-theft", "endpoint", "mimikatz"],
  "userId": "usr-002"
}
```

---

## Dependency Injection

**File:** `backend/app/dependencies.py`

FastAPI's dependency injection system is used to compose auth checks cleanly and avoid repetition. There are three public dependencies used across routers:

### `validate_api_key`

```python
async def validate_api_key(x_api_key: str | None = Header(default=None)) -> None
```

Reads the `X-Api-Key` header and compares it against `settings.api_key` using constant-time comparison. Raises `HTTPException(401)` on failure.

Used via: `Depends(validate_api_key)` in route function signatures.

### `get_current_user`

```python
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer)
) -> UserResponse
```

Full JWT validation pipeline (decode → blacklist check → DB lookup → status check). Returns the `UserResponse` of the authenticated user.

Used via: `Depends(get_current_user)`.

### `require_admin`

```python
async def require_admin(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse
```

Chains on `get_current_user` and additionally enforces `role == "admin"`. Raises `HTTPException(403)` otherwise.

Used via: `Depends(require_admin)` on all `/api/users` routes.

### Composition example

```python
@router.get("/")
async def list_users(
    current_user: UserResponse = Depends(require_admin),
):
    # current_user is already validated: JWT valid, not revoked, not disabled, role=admin
    ...
```

---

## Error Handling

### Global request validation handler

When Pydantic fails to validate an incoming request body (HTTP 422), the custom handler:
- Omits `input` and `loc` (field path) from each error entry
- Returns only the `msg` field (the human-readable error message)
- Prevents internal schema details from leaking to the client

### Auth error responses (401)

All authentication failures return a generic `{"detail": "..."}` JSON body. Specific failure reasons are intentionally vague for public-facing messages but are logged in detail to the audit_logs collection:

| Scenario | Public message | Audit reason |
|---|---|---|
| Invalid API key | `"Invalid or missing API key"` | — |
| JWT missing/malformed/expired | `"Invalid or expired token"` | — |
| Token revoked | `"Token has been revoked"` | — |
| User not found | `"Invalid credentials"` | `"unknown_email"` |
| Wrong password | `"Invalid credentials"` | `"wrong_password"` |
| Account locked | `"Account is locked. Try again later."` | `"account_locked"` |
| Account disabled | `"Account is disabled"` | `"account_disabled"` |

The phrasing for unknown email and wrong password is deliberately identical (`"Invalid credentials"`) to prevent user enumeration.

### Business logic errors (400/403/404)

Descriptive error messages are appropriate here since they communicate state (not credentials):

| Scenario | Code | Message |
|---|---|---|
| Email already taken | 400 | `"Email already exists"` |
| Password too weak | 400 | Specific failure description |
| No update fields provided | 400 | `"No fields to update"` |
| Would remove last admin | 400 | `"Cannot remove last admin"` |
| Trying to delete own account | 403 | `"Cannot delete your own account"` |
| User not found | 404 | `"User not found"` |
| Event not found | 404 | `"Event not found"` |
| Non-admin accessing admin route | 403 | `"Admin access required"` |

---

## Audit Logging

**Collection:** `audit_logs`

Every significant action — both successes and failures — is written to the audit log. The audit log is append-only by convention (no document is ever updated or deleted).

### Document structure

```json
{
  "_id": ObjectId("..."),
  "event_type": "login_success",
  "user_id": "usr-001",
  "target_id": "usr-002",
  "ip_address": "127.0.0.1",
  "timestamp": "2025-02-18T14:32:01.123456Z",
  "details": {
    "reason": "wrong_password"
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `event_type` | `str` | One of the values below |
| `user_id` | `str \| null` | The acting user's ID; null for unauthenticated events |
| `target_id` | `str \| null` | The affected user's ID (admin actions only) |
| `ip_address` | `str` | Request IP, or `"server"` for server-initiated events |
| `timestamp` | `str` | ISO8601 datetime string |
| `details` | `object` | Event-specific metadata |

### Event types

| `event_type` | When logged | Key `details` fields |
|---|---|---|
| `login_success` | Successful login | — |
| `login_failure` | Failed login attempt | `reason`: `wrong_password`, `unknown_email`, `account_locked`, `account_disabled` |
| `logout` | Successful logout | — |
| `user_created` | Admin creates a new user | `email`, `role` |
| `user_updated` | Admin updates a user | `target_user_id`, changed fields |
| `user_deleted` | Admin deletes a user | `email` of deleted user |

---

## Seeding & Initialization

**File:** `backend/seed.py`

The `seed()` coroutine is called on every application startup via the lifespan handler. All operations are idempotent — they check current state before inserting.

### Step 1: Create indexes

`await create_indexes()` runs unconditionally on every boot. MongoDB ignores duplicate index creation requests, so this is safe to run repeatedly.

### Step 2: Seed events

If the `events` collection is empty:
1. Read `../data/mock_events.json` relative to the backend directory.
2. Deduplicate events by `id` field (in case the JSON file has duplicates).
3. Insert all events into the `events` collection.

If the collection already has documents, seeding is skipped.

The `mock_events.json` file contains approximately 50 realistic security events covering a range of severities and threat categories (credential theft, lateral movement, data exfiltration, etc.).

### Step 3: Seed users

If the `users` collection is empty:

Three initial users are created from hardcoded templates + environment variable passwords:

| ID | Email | Role | Status | Password env var |
|---|---|---|---|---|
| `usr-001` | `admin@penguwave.io` | `admin` | `active` | `SEED_ADMIN_PASSWORD` |
| `usr-002` | `analyst@penguwave.io` | `analyst` | `active` | `SEED_ANALYST_PASSWORD` |
| `usr-003` | `viewer@penguwave.io` | `viewer` | `disabled` | `SEED_VIEWER_PASSWORD` |

Passwords are read from environment variables and hashed with bcrypt at cost factor 4 (lower than production's 12 — this is acceptable because seed passwords are already known/configured in `.env`; the lower cost reduces startup time).

If the collection already has documents, seeding is skipped entirely.

---

## Security Deep Dive

### Password security

- **Storage:** bcrypt with cost factor 12 (for user-created accounts). Cost factor 4 for seed data (startup speed trade-off; acceptable because seed passwords are admin-controlled).
- **Validation requirements:** Minimum 8 characters; must contain at least one letter and one digit. Enforced via Pydantic field validator.
- **Verification:** `bcrypt.checkpw` — the hash is never decrypted; only compared.
- **Timing attack on unknown email:** When a login fails because the email is not in the database, a dummy password check is still performed before returning 401. This ensures that the response time is similar regardless of whether the email exists.

### JWT security

- **Algorithm:** HS256 (HMAC-SHA256 with a shared secret)
- **Secret:** 64-character hex string from environment variable — 256 bits of entropy
- **Expiry:** 8 hours (configurable via `JWT_EXPIRY_HOURS`)
- **Revocation:** Tokens are stateless by default, but logout is implemented by inserting the token's `jti` into the `invalidated_tokens` blacklist. Every authenticated request checks this blacklist. The TTL index cleans up expired entries automatically.
- **Role in token:** The `role` claim is embedded at issue time. If an admin changes a user's role, the old token's role claim is stale until the token expires. This is an accepted trade-off given the 8-hour expiry.

### API key

- Static shared secret between the frontend and backend.
- Compared with `secrets.compare_digest` (constant-time, immune to timing attacks).
- Transmitted in `X-Api-Key` header (not `Authorization` — keeps it visually distinct from the per-user JWT).
- Required on most endpoints, adding a layer of protection against direct API access from unauthorized clients.

### Input validation

- All request bodies are validated by Pydantic before handlers execute. Invalid data never reaches business logic.
- Validation error details are sanitized before being sent to the client (no raw input, no field paths).
- MongoDB queries use parameterized-style documents (no string interpolation) — not vulnerable to NoSQL injection via Motor's driver API.

### CORS

- Only the configured frontend origin is allowed.
- The allowed header list is explicit: `Authorization`, `Content-Type`, `X-Api-Key`.
- No wildcard origins or methods.

### HTTP security headers (set on all responses)

| Header | Value | Protects against |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | MIME type confusion attacks |
| `X-Frame-Options` | `DENY` | Clickjacking via iframe embedding |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Referrer leakage to third parties |
| `Content-Security-Policy` | `default-src 'none'` | XSS, resource injection, data exfiltration |
| `Cache-Control` | `no-store` (auth routes) | Credentials cached in browser or proxy |

### Account lockout

- 3 failed login attempts triggers a 15-minute account lock.
- Lock state is stored in the database, not in memory — survives server restarts.
- Lockout is per-account (not per-IP), so it cannot be bypassed by changing IPs.
- Lockout expiry is a stored timestamp — the server compares current time against it on each attempt.

### Last-admin protection

- The system refuses to delete or demote the last admin account. This prevents accidental lockout of the entire admin panel.
- Checked in both `PATCH` (role change) and `DELETE` endpoints.

### Self-deletion protection

- An admin cannot delete their own account. This prevents a scenario where an admin accidentally locks themselves out.

---

## Key Architectural Decisions

### Async-first

Every route handler and database call is `async`. Motor provides a fully async MongoDB interface built on `asyncio`. This means the server can handle many concurrent requests without thread blocking — important for I/O-bound workloads like database queries.

### MongoDB as primary store

MongoDB is used for all four collections. Its document model is a natural fit for security events, which have variable schemas. Compound and TTL indexes handle the access patterns efficiently without requiring schema migrations.

### Stateless JWT with a revocation blacklist

Pure stateless JWTs cannot be revoked. The `invalidated_tokens` collection bridges this gap: logout inserts the `jti`, and every request checks the blacklist. The TTL index ensures the blacklist never grows unboundedly. The trade-off is one extra DB read per authenticated request.

### Singleton MongoDB client

The `AsyncIOMotorClient` instance is created once and reused. Motor manages an internal connection pool, so creating a new client per request would be wasteful and incorrect. The singleton ensures the connection pool is shared across all requests.

### Seed-on-startup

Instead of a separate migration script, the `seed()` function runs on every startup. All operations are idempotent (check before insert, `create_index` is a no-op if the index exists). This means a fresh environment (new Docker volume) self-bootstraps without manual intervention.

### Swagger/ReDoc disabled

`docs_url=None` and `redoc_url=None` remove the auto-generated API documentation endpoints. In a production deployment, this reduces the discoverable attack surface. Developers use the source code or this document instead.

### Rate limiting on login only

The login endpoint is the only endpoint with IP-based rate limiting. This is where brute-force attacks would target credentials. Other endpoints require a valid JWT (already authenticated), so IP rate limiting adds less value there.

### No pagination on events

The `GET /api/events` endpoint currently returns all events. This is a deliberate simplicity choice for the bootcamp scope but would need pagination (cursor-based or offset) before deployment with large datasets.

### Audit log as append-only

Audit logs are never updated or deleted by application code. Combined with the TTL index on `invalidated_tokens` (which is separate), the audit trail is preserved indefinitely. A production system would add log rotation or archival policies.
