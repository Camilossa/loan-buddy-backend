## Loan Buddy Backend (FastAPI)

API REST para el frontend Loan Buddy. Expone préstamos, pagos y métricas. Ahora persiste en base de datos con SQLAlchemy (PostgreSQL recomendado vía `DATABASE_URL`).

### Requisitos
- Python 3.11+
- `pip` o `uv`
- SQLAlchemy 2.x y psycopg (incluidos en `requirements.txt`)

### Instalación
```bash
cd loan-buddy-backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# (Opcional) con uv: uv venv .venv && source .venv/bin/activate && uv pip install -r requirements.txt
```

### Ejecutar en desarrollo
```bash
# Ejemplo Postgres local
export DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/loan_buddy"
uvicorn app.main:app --reload --port 8000
```
Docs: http://localhost:8000/docs (prefijo global `/api`).

### Entidades y atributos
- Loan
	- id: string (UUID)
	- debtorName: string (2-100)
	- debtorEmail: email opcional
	- debtorPhone: string opcional
	- principalAmount: number >= 0
	- interestRate: number [0, 100]
	- totalInstallments: int [1, 360]
	- monthlyPayment: number (calculado)
	- remainingBalance: number (actualizado en pagos)
	- paidInstallments: int
	- startDate: date
	- nextPaymentDate: date
	- status: "active" | "paid" | "overdue" | "defaulted"
	- createdAt / updatedAt: datetime

- Payment
	- id: string (UUID)
	- loanId: string
	- amount: number > 0
	- principalPaid: number (calculado)
	- interestPaid: number (calculado)
	- remainingBalance: number (saldo tras pago)
	- installmentNumber: int
	- paymentDate: date
	- notes: string opcional
	- status: "completed" | "pending" | "failed"
	- createdAt: datetime

- LoanSummary
	- totalLoans, activeLoans, totalLent, totalReceived, pendingAmount, overdueLoans, upcomingPayments

- UpcomingPayment
	- loan: Loan
	- daysUntil: int

### Endpoints principales (/api)
- Health
	- GET /health → estado

- Loans
	- GET /loans → lista
	- POST /loans → crea (usa campos de LoanCreate)
	- GET /loans/{id} → detalle
	- PATCH /loans/{id} → actualiza parcial (LoanUpdate)
	- DELETE /loans/{id} → elimina préstamo y pagos ligados
	- GET /loans/{id}/payments → pagos del préstamo

- Payments
	- GET /payments?limit=N → pagos (recientes si se limita)
	- POST /payments → registra pago (loanId, amount, paymentDate, notes?)

- Stats
	- GET /stats/summary → métricas (LoanSummary)
	- GET /stats/upcoming-payments → próximos pagos (<= 7 días)
	- GET /stats/overdue → préstamos vencidos

### Datos de ejemplo
Las tablas se crean automáticamente en el arranque (según `DATABASE_URL`). Los tests generan sus propios datos en una base SQLite temporal; en desarrollo puedes comenzar con una base vacía.

### Notas de implementación
- Cálculo de cuota mensual (amortización) y desglose capital/interés al registrar pagos.
- Estados: `paid` si remainingBalance <= 0; `overdue` si nextPaymentDate < hoy y está activo.
- CORS abierto a http://localhost:5173 y 4173 para el frontend Vite.

### Pruebas rápidas
```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/loans | head
curl -X POST http://localhost:8000/api/loans \
	-H "Content-Type: application/json" \
	-d '{"debtorName":"Demo","principalAmount":10000,"interestRate":12,"totalInstallments":12,"startDate":"2025-01-01","nextPaymentDate":"2025-02-01"}'
```

### Próximos pasos sugeridos
- Añadir migraciones (Alembic) y autenticación.
- Agregar pruebas unitarias para amortización y reglas de estado.
