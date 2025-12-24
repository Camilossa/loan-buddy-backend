from typing import List, Optional
from fastapi import APIRouter, HTTPException, status

from ..schemas import (
    Loan,
    LoanCreate,
    LoanSummary,
    LoanUpdate,
    Payment,
    PaymentCreate,
    UpcomingPayment,
)
from ..services.loan_service import LoanService

service = LoanService()

api_router = APIRouter(prefix="/api")


@api_router.get("/health", tags=["health"])
def healthcheck() -> dict:
    return {"status": "ok"}


# Loans ---------------------------------------------------------------
loans_router = APIRouter(prefix="/loans", tags=["loans"])


@loans_router.get("/", response_model=List[Loan])
def list_loans() -> List[Loan]:
    return service.list_loans()


@loans_router.post("/", response_model=Loan, status_code=status.HTTP_201_CREATED)
def create_loan(payload: LoanCreate) -> Loan:
    return service.create_loan(payload)


@loans_router.get("/{loan_id}", response_model=Loan)
def get_loan(loan_id: str) -> Loan:
    loan = service.get_loan(loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    return loan


@loans_router.patch("/{loan_id}", response_model=Loan)
def update_loan(loan_id: str, payload: LoanUpdate) -> Loan:
    loan = service.update_loan(loan_id, payload)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    return loan


@loans_router.delete("/{loan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_loan(loan_id: str) -> None:
    removed = service.delete_loan(loan_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Loan not found")


@loans_router.get("/{loan_id}/payments", response_model=List[Payment])
def get_payments_by_loan(loan_id: str) -> List[Payment]:
    return service.get_payments_by_loan(loan_id)


# Payments ------------------------------------------------------------
payments_router = APIRouter(prefix="/payments", tags=["payments"])


@payments_router.get("/", response_model=List[Payment])
def list_payments(limit: Optional[int] = None) -> List[Payment]:
    return service.list_payments(limit)


@payments_router.post("/", response_model=Payment, status_code=status.HTTP_201_CREATED)
def create_payment(payload: PaymentCreate) -> Payment:
    payment = service.add_payment(payload)
    if not payment:
        raise HTTPException(status_code=404, detail="Loan not found")
    return payment


# Stats ---------------------------------------------------------------
stats_router = APIRouter(prefix="/stats", tags=["stats"])


@stats_router.get("/summary", response_model=LoanSummary)
def summary() -> LoanSummary:
    return service.compute_summary()


@stats_router.get("/upcoming-payments", response_model=List[UpcomingPayment])
def upcoming_payments() -> List[UpcomingPayment]:
    items = service.get_upcoming_payments()
    return [
        UpcomingPayment(loan=item["loan"], daysUntil=item["daysUntil"])
        for item in items
    ]


@stats_router.get("/overdue", response_model=List[Loan])
def overdue_loans() -> List[Loan]:
    return service.get_overdue_loans()


api_router.include_router(loans_router)
api_router.include_router(payments_router)
api_router.include_router(stats_router)
