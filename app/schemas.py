from datetime import date, datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, EmailStr, Field

LoanStatus = Literal["active", "paid", "overdue", "defaulted"]
PaymentStatus = Literal["completed", "pending", "failed"]


class LoanBase(BaseModel):
    debtorName: str = Field(..., min_length=2, max_length=100)
    debtorEmail: Optional[EmailStr] = None
    debtorPhone: Optional[str] = Field(default=None, max_length=50)
    principalAmount: float = Field(..., ge=0)
    interestRate: float = Field(..., ge=0, le=100)
    totalInstallments: int = Field(..., ge=1, le=360)
    startDate: date
    nextPaymentDate: date


class LoanCreate(LoanBase):
    pass


class LoanUpdate(BaseModel):
    debtorName: Optional[str] = Field(default=None, min_length=2, max_length=100)
    debtorEmail: Optional[EmailStr] = None
    debtorPhone: Optional[str] = Field(default=None, max_length=50)
    principalAmount: Optional[float] = Field(default=None, ge=0)
    interestRate: Optional[float] = Field(default=None, ge=0, le=100)
    totalInstallments: Optional[int] = Field(default=None, ge=1, le=360)
    startDate: Optional[date] = None
    nextPaymentDate: Optional[date] = None
    status: Optional[LoanStatus] = None


class Loan(LoanBase):
    id: str
    monthlyPayment: float
    remainingBalance: float
    paidInstallments: int
    status: LoanStatus
    createdAt: datetime
    updatedAt: datetime


class PaymentBase(BaseModel):
    loanId: str
    amount: float = Field(..., gt=0)
    paymentDate: date
    notes: Optional[str] = Field(default=None, max_length=500)


class PaymentCreate(PaymentBase):
    pass


class Payment(PaymentBase):
    id: str
    principalPaid: float
    interestPaid: float
    remainingBalance: float
    installmentNumber: int
    status: PaymentStatus
    createdAt: datetime


class LoanSummary(BaseModel):
    totalLoans: int
    activeLoans: int
    totalLent: float
    totalReceived: float
    pendingAmount: float
    overdueLoans: int
    upcomingPayments: int


class UpcomingPayment(BaseModel):
    loan: Loan
    daysUntil: int


class OverdueLoans(BaseModel):
    loans: List[Loan]
