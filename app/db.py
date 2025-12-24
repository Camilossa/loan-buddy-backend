import os
import re
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

load_dotenv()


class Base(DeclarativeBase):
    """Declarative base for ORM models."""
    pass


def _get_database_url() -> str:
    """Get and normalize DATABASE_URL for async driver."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL no está definido. Ej: postgresql://user:pass@host:port/dbname"
        )
    # Convert postgresql:// to postgresql+asyncpg://
    return re.sub(r"^postgresql:", "postgresql+asyncpg:", database_url)


def _build_engine() -> AsyncEngine:
    """Create async engine with SSL support for Neon."""
    database_url = _get_database_url()
    
    # Remove channel_binding param not supported by asyncpg
    database_url = re.sub(r"[&?]channel_binding=require", "", database_url)
    
    # Check if SSL is required
    ssl_required = "sslmode=require" in database_url
    
    # Remove sslmode param (we'll handle it via connect_args)
    database_url = re.sub(r"[&?]sslmode=require", "", database_url)
    
    connect_args = {"ssl": True} if ssl_required else {}
    
    return create_async_engine(
        database_url,
        echo=False,
        future=True,
        connect_args=connect_args,
    )


engine: AsyncEngine = _build_engine()

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session():
    """Async session dependency for FastAPI routes."""
    async with SessionLocal() as session:
        yield session
