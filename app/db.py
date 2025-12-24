import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


def _build_engine(url: str | None = None) -> Engine:
    load_dotenv()  # Load .env locally so DATABASE_URL is available when not exported
    database_url = url or os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL no está definido. Ej: postgres://user:pass@host:port/dbname"
        )

    # If user provides plain postgres URL, default to psycopg3 driver.
    if database_url.startswith("postgresql://") and "+psycopg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    engine = create_engine(database_url, future=True, connect_args=connect_args)

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
