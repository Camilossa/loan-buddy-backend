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
default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]
origins = (
    [o.strip() for o in cors_env.split(",") if o.strip()]
    if cors_env
    else default_origins
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
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
