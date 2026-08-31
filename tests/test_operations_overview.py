from dataclasses import replace
from datetime import date

from app.services import operations_overview as service


def performance_row(manager_id: str, miles: float, empty: float) -> dict:
    return {
        "manager_id": manager_id,
        "working_trucks": 10,
        "movement_count": 20,
        "total_miles": miles,
        "loaded_miles": miles - empty,
        "empty_miles": empty,
        "allocated_revenue": 50_000,
        "stop_appointments": 100,
        "on_time_stops": 90,
        "order_appointments": 50,
        "on_time_orders": 45,
    }


def test_operations_overview_builds_weighted_otr_summary(monkeypatch) -> None:
    rows = [
        performance_row("carter", 1_000, 100),
        performance_row("blake", 1_000, 100),
        performance_row("reed", 1_000, 100),
    ]
    calls = []

    def fake_performance(start_date, end_date):
        calls.append((start_date, end_date))
        return rows

    monkeypatch.setattr(service, "fetch_operations_performance", fake_performance)
    monkeypatch.setattr(
        service,
        "fetch_operations_tractors",
        lambda: [
            {"manager_id": manager_id, "manager_name": manager_id, "assigned_trucks": 12, "seated_trucks": 9}
            for manager_id in ("carter", "blake", "reed")
        ],
    )
    monkeypatch.setattr(
        service,
        "fetch_operations_fleet_status",
        lambda: {
            "active_fleet": 40,
            "seated_tractors": 36,
            "dispatch_ready": 34,
            "ready_to_seat": 4,
            "out_of_service": 2,
            "special_hold": 1,
        },
    )

    overview = service.build_operations_overview(date(2026, 8, 28))

    assert calls[0] == (date(2026, 8, 23), date(2026, 8, 29))
    assert calls[1] == (date(2026, 8, 1), date(2026, 8, 28))
    assert overview["week_start"] == "2026-08-23"
    assert overview["week_end"] == "2026-08-29"
    assert overview["summary"]["otr_assigned_trucks"] == 36
    assert overview["summary"]["otr_working_trucks"] == 30
    assert overview["summary"]["otr_miles_per_truck"] == 100
    assert overview["managers"][0]["week"]["miles_per_truck"] == 100
    assert overview["summary"]["otr_deadhead_pct"] == 10
    assert overview["summary"]["otr_stop_otp"] == 90
    assert overview["summary"]["seating_pct"] == 90
    assert overview["business_days_elapsed"] == 20
    assert overview["business_days_total"] == 21


def test_alerts_use_centralized_thresholds(monkeypatch) -> None:
    monkeypatch.setattr(
        service,
        "OVERVIEW_CONFIG",
        replace(service.OVERVIEW_CONFIG, alert_stop_otp_pct=95, max_alerts=1),
    )

    alerts = service._build_alerts(
        {
            "otr_stop_otp": 94,
            "active_fleet": 10,
            "seated_tractors": 10,
            "seating_pct": 100,
            "out_of_service": 0,
            "otr_deadhead_pct": 5,
        }
    )

    assert len(alerts) == 1
    assert "95%" in alerts[0]["detail"]
