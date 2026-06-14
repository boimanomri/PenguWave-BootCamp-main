# PenguWave: Security Operations Portal

A full-stack security operations portal for monitoring and managing security events across your infrastructure. Built as Track A (Backend) for the Upwind Bootcamp 2026.

## What was built

The original repo was a frontend-only React app wired to mock data. This submission adds a real backend:

- **FastAPI** REST API (Python, fully async)
- **MongoDB** persistence via Motor (async driver)
- JWT authentication with token revocation on logout
- Role-based access control: `admin`, `analyst`, `viewer`
- Account lockout after repeated failed logins
- Audit logging for all significant actions
- Security headers, CORS restriction, rate limiting on login

The frontend is connected to the real backend — it no longer uses mock data.

For a detailed breakdown of every design decision, see [`BACKEND_ARCHITECTURE.md`](./BACKEND_ARCHITECTURE.md).

---

## How to run

### Prerequisites

- Node.js 18+
- Python 3.11+
- Docker (for MongoDB)

### 1. Start MongoDB

```bash
cd backend
docker compose up -d
```

This starts MongoDB 7 on `127.0.0.1:27017` with a persistent volume.

### 2. Configure the backend

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and fill in:

```
MONGO_USER=penguwave
MONGO_PASSWORD=<strong password>
JWT_SECRET=<64-char hex string, e.g. from: openssl rand -hex 32>
API_KEY=<any strong random string>
CORS_ORIGIN=http://localhost:5173
SEED_ADMIN_PASSWORD=<admin seed password>
SEED_ANALYST_PASSWORD=<analyst seed password>
SEED_VIEWER_PASSWORD=<viewer seed password>
```

**Never commit `.env`.** It is already in `.gitignore`.

### 3. Start the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

On first boot the server auto-creates MongoDB indexes and seeds initial users and events. No manual migration step needed.

### 4. Start the frontend

In a separate terminal from the project root:

```bash
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`.

### Default accounts (from seed)

| Email | Password | Role | Status |
|---|---|---|---|
| `admin@penguwave.io` | value of `SEED_ADMIN_PASSWORD` | admin | active |
| `analyst@penguwave.io` | value of `SEED_ANALYST_PASSWORD` | analyst | active |
| `viewer@penguwave.io` | value of `SEED_VIEWER_PASSWORD` | viewer | disabled |

---

## Architecture overview

```
Frontend (React + Vite + TypeScript)
    │  HTTP (JSON)
    ▼
FastAPI backend  ──►  MongoDB 7
    app/
    ├── main.py          app factory, middleware, router wiring
    ├── config.py        environment config (Pydantic Settings)
    ├── database.py      Motor client singleton, collections, indexes
    ├── dependencies.py  API key + JWT validation, admin guard
    ├── middleware.py    security headers (CSP, X-Frame-Options, …)
    ├── limiter.py       SlowAPI rate limiter
    ├── routers/
    │   ├── auth.py      login, logout, /me
    │   ├── users.py     admin user CRUD
    │   └── events.py    event listing and lookup
    └── models/
        ├── user.py      user Pydantic schemas
        └── event.py     event Pydantic schema
```

### Authentication

Every request goes through two layers:

1. **`X-Api-Key` header** — identifies the frontend application (static shared secret)
2. **`Authorization: Bearer <token>`** — identifies the specific user (JWT, HS256, 8h expiry)

Logout blacklists the token's `jti` in MongoDB. A TTL index auto-expires old entries. This means logout is real — the token cannot be reused after the user signs out.

### Authorization

Three roles with increasing privilege:

- `viewer` — read-only access to events (currently disabled in seed)
- `analyst` — read-only access to events
- `admin` — all of the above + full user management (create, update role/status, delete)

Role is checked server-side on every request, not just at login.

### Security decisions

| Decision | Rationale |
|---|---|
| bcrypt cost 12 | Balances security and latency; seed uses cost 4 only for startup speed |
| Constant-time API key comparison (`secrets.compare_digest`) | Prevents timing attacks that could leak the key character by character |
| Dummy password check on unknown email | Response time stays the same whether the email exists or not — prevents user enumeration |
| Account lockout after 3 failures (15 min) | Throttles brute-force without rate-limit-only approaches that can be bypassed per-IP |
| Token blacklist via MongoDB TTL index | Logout is stateful without a separate cache layer; expired entries self-delete |
| Last-admin protection on PATCH and DELETE | Prevents accidentally locking yourself out of the admin panel |
| `Content-Security-Policy: default-src 'none'` | Strict default; no inline scripts or external resources allowed |
| Swagger/ReDoc disabled | Reduces the API discovery surface in production |

### What I would add with more time

- Pagination on `GET /api/events` (currently returns all events)
- Filtering and full-text search on events (indexes are already in place)
- Refresh tokens to avoid re-login every 8 hours
- HTTPS / TLS termination (currently HTTP-only; TLS should be handled at the proxy layer)
- Automated test suite (unit tests for auth logic, integration tests against a test DB)
- Role enforcement in the frontend (currently checked only server-side)
