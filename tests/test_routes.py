from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.models import CustomerBillingDate, CustomerStop
from app.services import customer_invoice as customer_service

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


def test_readiness_reports_database_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.health.open_connection",
        lambda: (_ for _ in ()).throw(RuntimeError("missing database settings")),
    )

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database": "unavailable",
    }


def test_date_range_validation_happens_before_database_call() -> None:
    response = client.get(
        "/api/reports/lane-profitability",
        params={"start_date": "2026-08-20", "end_date": "2026-08-01"},
    )
    assert response.status_code == 400


def test_customer_preview_uses_one_exact_bill_date(monkeypatch) -> None:
    captured = {}

    def fake_fetch(start_date, end_date):
        captured["dates"] = (start_date, end_date)
        return [
            CustomerStop(
                order_id="100",
                ordered_date=date(2026, 8, 1),
                delivery_date=date(2026, 8, 3),
                bill_date=date(2026, 8, 4),
                origin_city="Salt Lake City",
                origin_state="UT",
                origin_zip="84339",
                destination_city="Boise",
                destination_state="ID",
                destination_zip="83702",
                consignee="Demo Distribution",
                miles=350,
                bol_number="BOL-100",
                commodity="Sporting goods",
                weight=12000,
                movement_sequence=1,
                total_pallets=20,
                pallets_dropped=10,
                pallets_picked_up=10,
                freight_charge=1000,
                fuel_surcharge=250,
                extra_drops=25,
                extra_pickups=0,
                other_charges=10,
                other_charge_total=285,
                total_charge=1285,
                allocated_fuel=125,
                allocated_freight=500,
                trailer_number="TR-42",
            )
        ]

    monkeypatch.setattr(customer_service, "fetch_customer_stops", fake_fetch)
    response = client.get(
        "/api/reports/customer-invoice/preview",
        params={"bill_date": "2026-08-04"},
    )
    assert response.status_code == 200
    assert captured["dates"] == (date(2026, 8, 4), date(2026, 8, 4))
    assert response.json()["summary"]["calculated_total"] == 1285


def test_customer_preview_accepts_optional_end_date(monkeypatch) -> None:
    captured = {}

    def fake_fetch(start_date, end_date):
        captured["dates"] = (start_date, end_date)
        return []

    monkeypatch.setattr(customer_service, "fetch_customer_stops", fake_fetch)
    response = client.get(
        "/api/reports/customer-invoice/preview",
        params={"bill_date": "2026-08-04", "end_date": "2026-08-08"},
    )
    assert response.status_code == 404
    assert captured["dates"] == (date(2026, 8, 4), date(2026, 8, 8))
    assert "through 2026-08-08" in response.json()["detail"]


def test_recent_billing_dates_uses_two_mondays_through_friday(monkeypatch) -> None:
    captured = {}

    def fake_fetch(start_date, end_date):
        captured["dates"] = (start_date, end_date)
        return [CustomerBillingDate(date(2026, 8, 24), 4, 12000)]

    monkeypatch.setattr(
        customer_service,
        "fetch_customer_billing_dates",
        fake_fetch,
    )
    response = client.get("/api/reports/customer-invoice/billing-dates")
    assert response.status_code == 200
    assert (captured["dates"][1] - captured["dates"][0]).days == 18
    assert response.json()["dates"][0]["order_count"] == 4


def test_default_billing_window_starts_two_mondays_back() -> None:
    assert customer_service.default_billing_window(date(2026, 8, 25)) == (
        date(2026, 8, 10),
        date(2026, 8, 28),
    )


def test_public_report_routes_are_preserved() -> None:
    paths = app.openapi()["paths"]
    assert "/api/reports/lane-profitability" in paths
    assert "/api/reports/customer-invoice" in paths
    assert "/api/reports/customer-invoice/preview" in paths
    assert "/api/reports/customer-invoice/billing-dates" in paths
    assert "/api/reports/fleet-cost-revenue/preview" in paths
    assert "/api/reports/fleet-cost-revenue.csv" in paths
    assert "/api/reports/fleet-cost-revenue.png" in paths
    assert "/api/overview" in paths


def test_fleet_view_rejects_unknown_granularity() -> None:
    response = client.get(
        "/api/reports/fleet-cost-revenue/preview",
        params={
            "start_date": "2026-07-01",
            "end_date": "2026-07-31",
            "granularity": "quarter",
        },
    )
    assert response.status_code == 422
