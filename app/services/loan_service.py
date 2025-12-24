from __future__ import annotations

from datetime import date, datetime
from typing import Iterable, List, Optional
from uuid import uuid4

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..db import SessionLocal
from ..models import LoanModel, PaymentModel
from ..schemas import Loan, LoanCreate, LoanSummary, LoanUpdate, Payment, PaymentCreate


class LoanService:
    """Domain logic for loans, payments and dashboard summaries backed by SQLAlchemy."""

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession] = SessionLocal
    ) -> None:
        self.session_factory = session_factory

    # ---- Public API -----------------------------------------------------
    async def list_loans(self) -> List[Loan]:
        async with self.session_factory() as session:
            result = await session.execute(select(LoanModel))
            loans = result.scalars().all()
            changed = False
            for loan in loans:
                changed |= self._refresh_status(loan)
            if changed:
                await session.commit()
            return [self._to_loan_schema(loan) for loan in loans]

    async def get_loan(self, loan_id: str) -> Optional[Loan]:
        async with self.session_factory() as session:
            loan = await session.get(LoanModel, loan_id)
            if not loan:
                return None
            if self._refresh_status(loan):
                await session.commit()
            return self._to_loan_schema(loan)

    async def create_loan(self, payload: LoanCreate) -> Loan:
        now = datetime.utcnow()
        monthly_payment = self._calculate_monthly_payment(
            payload.principalAmount, payload.interestRate, payload.totalInstallments
        )

        loan = LoanModel(
            id=str(uuid4()),
            debtorName=payload.debtorName,
            debtorEmail=payload.debtorEmail,
            debtorPhone=payload.debtorPhone,
            principalAmount=payload.principalAmount,
            interestRate=payload.interestRate,
            totalInstallments=payload.totalInstallments,
            monthlyPayment=monthly_payment,
            remainingBalance=payload.principalAmount,
            paidInstallments=0,
            startDate=payload.startDate,
            nextPaymentDate=payload.nextPaymentDate,
            status="active",
            createdAt=now,
            updatedAt=now,
        )

        async with self.session_factory() as session:
            session.add(loan)
            await session.commit()
            await session.refresh(loan)
            return self._to_loan_schema(loan)

    async def update_loan(self, loan_id: str, payload: LoanUpdate) -> Optional[Loan]:
        async with self.session_factory() as session:
            loan = await session.get(LoanModel, loan_id)
            if not loan:
                return None

            data = payload.model_dump(exclude_none=True)
            for field, value in data.items():
                setattr(loan, field, value)

            if any(
                key in data
                for key in ("principalAmount", "interestRate", "totalInstallments")
            ):
                loan.monthlyPayment = self._calculate_monthly_payment(
                    loan.principalAmount, loan.interestRate, loan.totalInstallments
                )
                if loan.remainingBalance > loan.principalAmount:
                    loan.remainingBalance = loan.principalAmount

            loan.updatedAt = datetime.utcnow()
            self._refresh_status(loan)
            await session.commit()
            await session.refresh(loan)
            return self._to_loan_schema(loan)

    async def delete_loan(self, loan_id: str) -> bool:
        async with self.session_factory() as session:
            loan = await session.get(LoanModel, loan_id)
            if not loan:
                return False
            await session.delete(loan)
            await session.commit()
            return True

    async def list_payments(self, limit: Optional[int] = None) -> List[Payment]:
        async with self.session_factory() as session:
            stmt = select(PaymentModel).order_by(PaymentModel.paymentDate.desc())
            if limit:
                stmt = stmt.limit(limit)
            payments = (await session.execute(stmt)).scalars().all()
            return [self._to_payment_schema(p) for p in payments]

    async def get_payments_by_loan(self, loan_id: str) -> List[Payment]:
        async with self.session_factory() as session:
            payments = (
                await session.execute(
                    select(PaymentModel)
                    .where(PaymentModel.loanId == loan_id)
                    .order_by(PaymentModel.paymentDate.desc())
                )
            ).scalars().all()
            return [self._to_payment_schema(p) for p in payments]

    async def add_payment(self, payload: PaymentCreate) -> Optional[Payment]:
        async with self.session_factory() as session:
            loan = await session.get(LoanModel, payload.loanId)
            if not loan:
                return None

            monthly_rate = loan.interestRate / 100 / 12
            interest_paid = loan.remainingBalance * monthly_rate
            principal_paid = max(0.0, payload.amount - interest_paid)
            new_remaining = max(0.0, loan.remainingBalance - principal_paid)
            installment_number = loan.paidInstallments + 1

            now = datetime.utcnow()
            payment = PaymentModel(
                id=str(uuid4()),
                loanId=loan.id,
                amount=payload.amount,
                principalPaid=principal_paid,
                interestPaid=interest_paid,
                remainingBalance=new_remaining,
                paymentDate=payload.paymentDate,
                installmentNumber=installment_number,
                status="completed",
                notes=payload.notes,
                createdAt=now,
            )

            session.add(payment)

            loan.paidInstallments = installment_number
            loan.remainingBalance = new_remaining
            loan.status = "paid" if new_remaining <= 0 else loan.status
            if new_remaining > 0:
                loan.nextPaymentDate = loan.nextPaymentDate + relativedelta(months=1)
                if loan.status == "paid":
                    loan.status = "active"
            loan.updatedAt = now
            self._refresh_status(loan)

            await session.commit()
            await session.refresh(payment)
            await session.refresh(loan)
            return self._to_payment_schema(payment)

    async def compute_summary(self) -> LoanSummary:
        async with self.session_factory() as session:
            loans = (await session.execute(select(LoanModel))).scalars().all()
            payments = (await session.execute(select(PaymentModel))).scalars().all()

            changed = False
            for loan in loans:
                changed |= self._refresh_status(loan)
            if changed:
                await session.commit()

            total_lent = sum(loan.principalAmount for loan in loans)
            total_received = sum(p.amount for p in payments if p.status == "completed")
            pending_amount = sum(
                loan.remainingBalance for loan in loans if loan.status != "paid"
            )
            overdue_loans = len([loan for loan in loans if loan.status == "overdue"])
            upcoming_payments = len(self._compute_upcoming(loans))

            return LoanSummary(
                totalLoans=len(loans),
                activeLoans=len([loan for loan in loans if loan.status == "active"]),
                totalLent=total_lent,
                totalReceived=total_received,
                pendingAmount=pending_amount,
                overdueLoans=overdue_loans,
                upcomingPayments=upcoming_payments,
            )

    async def get_upcoming_payments(self) -> List[dict]:
        async with self.session_factory() as session:
            loans = (await session.execute(select(LoanModel))).scalars().all()
            for loan in loans:
                self._refresh_status(loan)
            await session.commit()
            return self._compute_upcoming(loans)

    async def get_overdue_loans(self) -> List[Loan]:
        async with self.session_factory() as session:
            loans = (await session.execute(select(LoanModel))).scalars().all()
            changed = False
            for loan in loans:
                changed |= self._refresh_status(loan)
            if changed:
                await session.commit()
            return [self._to_loan_schema(l) for l in loans if l.status == "overdue"]

    # ---- Helpers --------------------------------------------------------
    def _calculate_monthly_payment(
        self, principal: float, annual_rate: float, months: int
    ) -> float:
        if months <= 0:
            return 0.0
        if annual_rate == 0:
            return principal / months
        monthly_rate = annual_rate / 100 / 12
        return (
            principal
            * monthly_rate
            * (1 + monthly_rate) ** months
            / ((1 + monthly_rate) ** months - 1)
        )

    def _refresh_status(self, loan: LoanModel) -> bool:
        """Update loan status based on dates/balance. Returns True if changed."""
        previous = loan.status
        if loan.remainingBalance <= 0:
            loan.status = "paid"
        else:
            today = date.today()
            if loan.nextPaymentDate < today:
                loan.status = "overdue"
            else:
                loan.status = "active"
        return previous != loan.status

    def _compute_upcoming(self, loans: Iterable[LoanModel]) -> List[dict]:
        today = date.today()
        in_seven_days = today + relativedelta(days=7)
        results = []
        for loan in loans:
            if loan.status == "paid":
                continue
            if today <= loan.nextPaymentDate <= in_seven_days:
                days_until = (loan.nextPaymentDate - today).days
                results.append(
                    {"loan": self._to_loan_schema(loan), "daysUntil": days_until}
                )
        results.sort(key=lambda item: item["daysUntil"])
        return results

    def _to_loan_schema(self, loan: LoanModel) -> Loan:
        return Loan.model_validate(loan, from_attributes=True)

    def _to_payment_schema(self, payment: PaymentModel) -> Payment:
        return Payment.model_validate(payment, from_attributes=True)
