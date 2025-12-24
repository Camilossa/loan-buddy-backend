import os
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


logger = logging.getLogger(__name__)


def _normalize_postgres_driver(database_url: str) -> str:
    """Force psycopg (v3) driver when URL omits a driver."""
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg")
    return str(url)


def _mask_url(database_url: str) -> str:
    """Render URL hiding password to log safely."""
    try:
        return make_url(database_url).render_as_string(hide_password=True)
    except Exception:
        return "<invalid DATABASE_URL>"


def _build_engine(url: str | None = None) -> Engine:
    database_url = url or os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL no está definido. Ej: postgres://user:pass@host:port/dbname"
        )

    database_url = _normalize_postgres_driver(database_url)

    masked = _mask_url(database_url)
    logger.info("Usando DATABASE_URL=%s", masked)

    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    try:
        engine = create_engine(database_url, future=True, connect_args=connect_args)
    except Exception as exc:
        logger.error("Error creando engine con DATABASE_URL=%s", masked)
        raise exc

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, _):  # type: ignore
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

    return engine


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_engine(url: str) -> Engine:
    """Recreate the engine/sessionmaker for a given URL (used in tests)."""
    global engine, SessionLocal
    engine = _build_engine(url)
    SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    return engine


def get_session():
    """Yield a session for dependency injection (not used directly in routes today)."""
    with SessionLocal() as session:
        yield session
