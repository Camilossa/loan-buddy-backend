import logging
import os

from dotenv import load_dotenv
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)

load_dotenv()


def _normalize_driver(database_url: str) -> tuple[str, bool]:
    """Force async drivers and drop unsupported query params.

    Returns: (normalized_url, ssl_required)
    """
    url = make_url(database_url)

    # Drop Neon pool param not supported by asyncpg.
    query = dict(url.query)
    query.pop("channel_binding", None)

    ssl_required = False
    sslmode = query.pop("sslmode", None)
    if sslmode == "require":
        ssl_required = True

    if url.drivername.startswith("postgresql") and "asyncpg" not in url.drivername:
        url = url.set(drivername="postgresql+asyncpg")
    elif url.drivername.startswith("sqlite") and "aiosqlite" not in url.drivername:
        url = url.set(drivername="sqlite+aiosqlite")

    if query != url.query:
        url = url.set(query=query)

    return str(url), ssl_required


def _mask_url(database_url: str) -> str:
    """Render URL hiding password to log safely."""
    try:
        return make_url(database_url).render_as_string(hide_password=True)
    except Exception:
        return "<invalid DATABASE_URL>"


def _build_engine(url: str | None = None) -> AsyncEngine:
    database_url = url or os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL no está definido. Ej: postgres://user:pass@host:port/dbname"
        )

    # Neon requiere driver async (asyncpg) para conexiones eficientes.
    database_url, ssl_required = _normalize_driver(database_url)

    masked = _mask_url(database_url)
    logger.info("Usando DATABASE_URL=%s", masked)

    connect_args = {"ssl": True} if ssl_required else None

    try:
        engine = create_async_engine(
            database_url, echo=False, future=True, connect_args=connect_args
        )
    except Exception as exc:
        logger.error("Error creando engine con DATABASE_URL=%s", masked)
        raise exc

    if database_url.startswith("sqlite"):

        @event.listens_for(engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, _):  # type: ignore
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

    return engine


engine: AsyncEngine = _build_engine()
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine, expire_on_commit=False, autoflush=False, autocommit=False
)


def init_engine(url: str) -> AsyncEngine:
    """Recreate the engine/sessionmaker for a given URL (used in tests)."""
    global engine, SessionLocal
    engine = _build_engine(url)
    SessionLocal = async_sessionmaker(
        bind=engine, expire_on_commit=False, autoflush=False, autocommit=False
    )
    return engine


async def get_session():
    """Async session dependency for FastAPI routes."""
    async with SessionLocal() as session:
        yield session
