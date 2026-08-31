"""Public repository interface.

DATA_MODE in the environment decides which implementation runs:

    demo       -> app.db.demo_repository       (seeded SQLite, fictional data)
    production -> app.db.production_repository (read-only Mcloud SQL Server)

Services and API routers import only from this module and never care which
backend is active.
"""

from datetime import date
from typing import Any

from app.config import get_settings
from app.db import demo_repository, production_repository
from app.models import (
    CustomerBillingDate,
    CustomerStop,
    DailyRevenue,
    FleetCostEntry,
    LaneLoad,
)


def _is_production() -> bool:
    return get_settings().data_mode.strip().lower() == "production"


def fetch_lane_loads(start_date: date, end_date: date) -> list[LaneLoad]:
    if _is_production():
        return production_repository.fetch_lane_loads(start_date, end_date)
    return demo_repository.fetch_lane_loads(start_date, end_date)


def fetch_customer_billing_dates(
    start_date: date, end_date: date
) -> list[CustomerBillingDate]:
    if _is_production():
        return production_repository.fetch_customer_billing_dates(start_date, end_date)
    return demo_repository.fetch_customer_billing_dates(start_date, end_date)


def fetch_customer_stops(start_date: date, end_date: date) -> list[CustomerStop]:
    if _is_production():
        return production_repository.fetch_customer_stops(start_date, end_date)
    return demo_repository.fetch_customer_stops(start_date, end_date)


def fetch_fleet_cost_entries(
    start_date: date, end_date: date, gl_accounts: tuple[str, ...]
) -> list[FleetCostEntry]:
    if _is_production():
        return production_repository.fetch_fleet_cost_entries(
            start_date, end_date, gl_accounts
        )
    return demo_repository.fetch_fleet_cost_entries(start_date, end_date, gl_accounts)


def fetch_daily_revenue(start_date: date, end_date: date) -> list[DailyRevenue]:
    if _is_production():
        return production_repository.fetch_daily_revenue(start_date, end_date)
    return demo_repository.fetch_daily_revenue(start_date, end_date)


def fetch_operations_performance(
    start_date: date, end_date: date
) -> list[dict[str, Any]]:
    if _is_production():
        return production_repository.fetch_operations_performance(start_date, end_date)
    return demo_repository.fetch_operations_performance(start_date, end_date)


def fetch_operations_tractors() -> list[dict[str, Any]]:
    if _is_production():
        return production_repository.fetch_operations_tractors()
    return demo_repository.fetch_operations_tractors()


def fetch_operations_fleet_status() -> dict[str, Any]:
    if _is_production():
        return production_repository.fetch_operations_fleet_status()
    return demo_repository.fetch_operations_fleet_status()
