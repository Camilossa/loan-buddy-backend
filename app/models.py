from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4
from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .db import Base


class LoanModel(Base):
    __tablename__ = "loans"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    debtorName = Column(String(100), nullable=False)
    debtorEmail = Column(String(255), nullable=True)
    debtorPhone = Column(String(50), nullable=True)
    principalAmount = Column(Float, nullable=False)
    interestRate = Column(Float, nullable=False)
    totalInstallments = Column(Integer, nullable=False)
    monthlyPayment = Column(Float, nullable=False)
    remainingBalance = Column(Float, nullable=False)
    paidInstallments = Column(Integer, nullable=False, default=0)
    startDate = Column(Date, nullable=False)
    nextPaymentDate = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="active")
    createdAt = Column(DateTime, nullable=False, default=datetime.utcnow)
    updatedAt = Column(DateTime, nullable=False, default=datetime.utcnow)

    payments = relationship(
        "PaymentModel",
        back_populates="loan",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PaymentModel(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    loanId = Column(
        String, ForeignKey("loans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    amount = Column(Float, nullable=False)
    principalPaid = Column(Float, nullable=False)
    interestPaid = Column(Float, nullable=False)
    remainingBalance = Column(Float, nullable=False)
    paymentDate = Column(Date, nullable=False)
    installmentNumber = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="completed")
    notes = Column(String(500), nullable=True)
    createdAt = Column(DateTime, nullable=False, default=datetime.utcnow)

    loan = relationship("LoanModel", back_populates="payments")
