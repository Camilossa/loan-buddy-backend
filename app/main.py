import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect

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


# Ensure tables exist only if missing
def _ensure_tables() -> None:
    inspector = inspect(engine)
    missing = [name for name in Base.metadata.tables if not inspector.has_table(name)]
    if missing:
        Base.metadata.create_all(bind=engine)


_ensure_tables()


@app.get("/")
def root() -> dict:
    return {"message": "Loan Buddy API", "docs": "/docs"}
