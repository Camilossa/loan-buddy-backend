from datetime import date
from pathlib import Path
from typing import AsyncGenerator
import sys

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

# Ensure project root is on sys.path so `app` package imports work when running pytest from repo root.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app
from app.services.loan_service import LoanService
from app.schemas import LoanCreate
from app import db
from app.models import Base
import app.api.routes as routes


@pytest_asyncio.fixture()
async def temp_service(tmp_path: Path) -> AsyncGenerator[LoanService, None]:
    """Create an isolated LoanService backed by a temp SQLite DB so tests don't touch real data."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"

    db.init_engine(db_url)
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    service = LoanService(session_factory=db.SessionLocal)

    # Seed a sample loan so list endpoint has data
    await service.create_loan(
        LoanCreate(
            debtorName="Fixture User",
            debtorEmail="fixture@example.com",
            debtorPhone="+52 555 111 1111",
            principalAmount=10000,
            interestRate=10,
            totalInstallments=12,
            startDate=date.today(),
            nextPaymentDate=date.today(),
        )
    )

    # Swap the global service used by routes so API calls hit the isolated DB.
    routes.service = service

    try:
        yield service
    finally:
        await db.engine.dispose()


@pytest.fixture()
def client(temp_service: LoanService) -> TestClient:  # noqa: D401
    """HTTP client bound to the app using the isolated service."""
    return TestClient(app)
