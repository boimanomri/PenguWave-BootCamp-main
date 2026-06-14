from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import close_client
from app.limiter import limiter
from app.middleware import SecurityHeadersMiddleware
from seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    await seed()
    yield
    await close_client()


app = FastAPI(
    title="PenguWave API",
    docs_url=None,   # disable Swagger UI in prod
    redoc_url=None,
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# CORS — allow only the frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Api-Key"],
)

from app.routers import auth
app.include_router(auth.router, prefix="/api/auth")
# app.include_router(events.router, prefix="/api/events")
# app.include_router(users.router, prefix="/api/users")


@app.get("/health")
async def health():
    return {"status": "ok"}
