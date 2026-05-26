import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import api_router
from .db import engine
from .models import Base

app = FastAPI(title="Loan Buddy API", version="0.1.0")

# Allow all origins by default so local/dev frontends (including LAN IPs) work.
# Set CORS_ORIGINS="http://host1:port,http://host2" to restrict if needed.
cors_env = os.getenv("CORS_ORIGINS")
default_origins = ["*"]
origins = (
    [o.strip() for o in cors_env.split(",") if o.strip()]
    if cors_env
    else default_origins
)

# If wildcard, credentials must be disabled to satisfy CORS spec.
allow_credentials = origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


async def _ensure_tables() -> None:
    """Create tables on startup using the async engine."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.on_event("startup")
async def _startup() -> None:
    await _ensure_tables()


@app.get("/")
def root() -> dict:
    return {"message": "Loan Buddy API", "docs": "/docs"}
