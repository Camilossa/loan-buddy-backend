from datetime import date, timedelta

from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"


def test_list_loans_returns_seed_data(client: TestClient) -> None:
    resp = client.get("/api/loans")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    required_fields = {"id", "debtorName", "principalAmount", "status"}
    assert required_fields.issubset(data[0].keys())


def test_create_loan_success(client: TestClient) -> None:
    payload = {
        "debtorName": "Test User",
        "debtorEmail": "test@example.com",
        "debtorPhone": "+52 555 000 0000",
        "principalAmount": 12000,
        "interestRate": 12,
        "totalInstallments": 12,
        "startDate": "2025-01-01",
        "nextPaymentDate": "2025-02-01",
    }
    resp = client.post("/api/loans", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["debtorName"] == payload["debtorName"]
    assert body["monthlyPayment"] > 0
    assert body["remainingBalance"] == payload["principalAmount"]
    assert body["status"] == "active"


def test_create_loan_validation_error(client: TestClient) -> None:
    payload = {
        "debtorName": "",
        "principalAmount": -10,
        "interestRate": 200,
        "totalInstallments": 0,
        "startDate": "2025-01-01",
        "nextPaymentDate": "2025-02-01",
    }
    resp = client.post("/api/loans", json=payload)
    assert resp.status_code == 422


def test_update_loan_recalculates_monthly_payment(client: TestClient) -> None:
    create = {
        "debtorName": "Rate Test",
        "principalAmount": 10000,
        "interestRate": 10,
        "totalInstallments": 10,
        "startDate": "2025-01-01",
        "nextPaymentDate": "2025-02-01",
    }
    created = client.post("/api/loans", json=create).json()
    loan_id = created["id"]
    old_payment = created["monthlyPayment"]

    resp = client.patch(f"/api/loans/{loan_id}", json={"interestRate": 5})
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["monthlyPayment"] != old_payment
    assert updated["interestRate"] == 5


def test_delete_loan_removes_resource(client: TestClient) -> None:
    payload = {
        "debtorName": "Delete Me",
        "principalAmount": 5000,
        "interestRate": 8,
        "totalInstallments": 6,
        "startDate": "2025-01-01",
        "nextPaymentDate": "2025-02-01",
    }
    created = client.post("/api/loans", json=payload).json()
    loan_id = created["id"]

    resp = client.delete(f"/api/loans/{loan_id}")
    assert resp.status_code == 204

    resp = client.get(f"/api/loans/{loan_id}")
    assert resp.status_code == 404


def test_add_payment_updates_balance_and_installments(client: TestClient) -> None:
    loan = client.post(
        "/api/loans",
        json={
            "debtorName": "Pay Me",
            "principalAmount": 1000,
            "interestRate": 12,
            "totalInstallments": 4,
            "startDate": "2025-01-01",
            "nextPaymentDate": "2025-02-01",
        },
    ).json()
    loan_id = loan["id"]
    before_balance = loan["remainingBalance"]

    resp = client.post(
        "/api/payments",
        json={
            "loanId": loan_id,
            "amount": 300,
            "paymentDate": "2025-02-01",
            "notes": "first",
        },
    )
    assert resp.status_code == 201
    payment = resp.json()
    assert payment["remainingBalance"] < before_balance
    assert payment["installmentNumber"] == 1

    loan_after = client.get(f"/api/loans/{loan_id}").json()
    assert loan_after["paidInstallments"] == 1
    assert loan_after["remainingBalance"] == payment["remainingBalance"]


def test_payments_list_respects_limit(client: TestClient) -> None:
    resp_all = client.get("/api/payments")
    assert resp_all.status_code == 200
    total = len(resp_all.json())

    resp_one = client.get("/api/payments", params={"limit": 1})
    assert resp_one.status_code == 200
    assert len(resp_one.json()) == 1
    assert total >= 1


def test_upcoming_and_overdue_endpoints(client: TestClient) -> None:
    soon_date = (date.today() + timedelta(days=3)).isoformat()
    client.post(
        "/api/loans",
        json={
            "debtorName": "Upcoming",
            "principalAmount": 2000,
            "interestRate": 10,
            "totalInstallments": 4,
            "startDate": date.today().isoformat(),
            "nextPaymentDate": soon_date,
        },
    )

    resp_upcoming = client.get("/api/stats/upcoming-payments")
    assert resp_upcoming.status_code == 200
    assert any(item["daysUntil"] <= 7 for item in resp_upcoming.json())

    resp_overdue = client.get("/api/stats/overdue")
    assert resp_overdue.status_code == 200
    assert isinstance(resp_overdue.json(), list)


def test_summary_endpoint_ok(client: TestClient) -> None:
    resp = client.get("/api/stats/summary")
    assert resp.status_code == 200
    payload = resp.json()
    for key in [
        "totalLoans",
        "activeLoans",
        "totalLent",
        "totalReceived",
        "pendingAmount",
        "overdueLoans",
        "upcomingPayments",
    ]:
        assert key in payload
